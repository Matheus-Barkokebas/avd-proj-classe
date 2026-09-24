"""Cliente da API ANA HidroWebService — chuva e nível/vazão (ING-04).

Autentica via OAuth (Identificador/Senha por variável de ambiente), coleta a
série de cada estação configurada em conf/sources/ana_estacoes.yml, persiste
RAW fielmente particionada e materializa a camada Bronze em Parquet validando
contra os contratos (FND-02): ana_chuva e ana_nivel.

Falha em uma estação não interrompe as demais — o erro fica registrado no
bloco daquela estação dentro do próprio payload RAW.

IMPORTANTE — limite desta implementação: a API `hidrowebservice` da ANA não
ficou acessível para verificação ao vivo nesta issue (respostas 503/504 nas
tentativas de consulta). Os caminhos de endpoint, o formato do token de
autenticação e os nomes de campo do payload seguem a documentação pública
do serviço, mas **não foram confirmados contra uma resposta real
autenticada**. Os nomes de campo ficam em `conf/sources/ana_estacoes.yml`
(mapeamento_colunas_chuva / mapeamento_colunas_nivel) exatamente para que o
time ajuste sem tocar neste módulo assim que rodar com credenciais reais.
Não inventamos código de estação nem cota de alerta (ai-rules 5.3) — ver
placeholders em ana_estacoes.yml.
"""

import argparse
from datetime import date, datetime
import io
import json
from pathlib import Path
import os
import time
from typing import Any
import pyarrow as pa
import pyarrow.parquet as pq
import requests
import yaml

from src.ingestao import contratos
from src.ingestao import runner


RAIZ_PROJETO = Path(__file__).resolve().parents[2]
CAMINHO_CONFIG_PADRAO = RAIZ_PROJETO / "conf" / "sources" / "ana_estacoes.yml"

CAMINHO_OAUTH = "/EstacoesTelemetricas/OAUth/v1"
CAMINHO_SERIE_CHUVA = "/EstacoesTelemetricas/HidroSerieChuva/v1"
CAMINHO_SERIE_COTAS = "/EstacoesTelemetricas/HidroSerieCotas/v1"

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF = 0  # segundos; 0 por padrão para não atrasar testes/execuções em lote


def carregar_configuracao_fonte(caminho_config: Path | None = None) -> dict[str, Any]:
    """Carrega o arquivo de configuração conf/sources/ana_estacoes.yml."""
    caminho = caminho_config if caminho_config is not None else CAMINHO_CONFIG_PADRAO
    if not caminho.is_file():
        raise FileNotFoundError(f"Configuração de fonte não encontrada: {caminho}")
    with caminho.open(encoding="utf-8") as arquivo:
        config = yaml.safe_load(arquivo)
    if not isinstance(config, dict):
        raise ValueError(f"Conteúdo inválido na configuração de fonte: {caminho}")
    return config


def _obter_credenciais(config: dict[str, Any]) -> tuple[str, str]:
    """Lê identificador/senha de variáveis de ambiente (nunca do arquivo de config)."""
    auth_cfg = config.get("autenticacao", {})
    nome_id = auth_cfg.get("identificador_env", "ANA_HIDROWEB_IDENTIFICADOR")
    nome_senha = auth_cfg.get("senha_env", "ANA_HIDROWEB_SENHA")
    identificador = os.environ.get(nome_id)
    senha = os.environ.get(nome_senha)
    if not identificador or not senha:
        raise RuntimeError(
            f"Credenciais da ANA não configuradas: defina as variáveis de ambiente "
            f"'{nome_id}' e '{nome_senha}' (cadastro em https://www.ana.gov.br/hidrowebservice/)."
        )
    return identificador, senha


def _extrair_token(resposta_json: Any) -> str:
    """Extrai o token de autenticação do envelope de resposta do OAuth.

    Tenta algumas chaves conhecidas da documentação pública; levanta erro
    claro (em vez de devolver algo incorreto) se nenhuma bater — o formato
    real ainda não foi confirmado nesta issue (ver docstring do módulo).
    """
    candidatos = []
    if isinstance(resposta_json, dict):
        items = resposta_json.get("items")
        if isinstance(items, dict):
            candidatos.append(items.get("tokenautenticacao"))
        candidatos.append(resposta_json.get("token"))
        candidatos.append(resposta_json.get("tokenautenticacao"))
    for candidato in candidatos:
        if candidato:
            return str(candidato)
    raise RuntimeError(
        "Não foi possível extrair o token de autenticação da resposta da ANA "
        "(formato inesperado) — confirmar o envelope real do OAuth contra a API."
    )


def autenticar(config: dict[str, Any], max_retries: int = DEFAULT_MAX_RETRIES) -> str:
    """Autentica no HidroWebService e devolve o token Bearer."""
    identificador, senha = _obter_credenciais(config)
    url = config.get("base_url", "").rstrip("/") + CAMINHO_OAUTH
    tentativa = 0
    while True:
        try:
            resposta = requests.get(url, auth=(identificador, senha), timeout=30)
            resposta.raise_for_status()
            return _extrair_token(resposta.json())
        except requests.exceptions.RequestException as exc:
            tentativa += 1
            if tentativa > max_retries:
                raise RuntimeError(f"Falha ao autenticar na ANA após {max_retries} tentativas: {exc}")


def _requisitar_serie(
    base_url: str,
    caminho: str,
    token: str,
    codigo_estacao: str,
    data_referencia: date,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff: int = DEFAULT_BACKOFF,
) -> list[dict[str, Any]]:
    """GET de uma série (chuva ou cotas) para uma estação, com retry."""
    url = base_url.rstrip("/") + caminho
    params = {
        "Código da Estação": codigo_estacao,
        "Tipo Filtro Data": "DATA_LEITURA",
        "Data de Busca": data_referencia.isoformat(),
        "Range Intervalo de busca": 1,
    }
    cabecalhos = {"Authorization": f"Bearer {token}"}
    tentativa = 0
    while True:
        try:
            resposta = requests.get(url, params=params, headers=cabecalhos, timeout=30)
            resposta.raise_for_status()
            dados = resposta.json()
            if isinstance(dados, dict) and isinstance(dados.get("items"), list):
                return dados["items"]
            if isinstance(dados, list):
                return dados
            return []
        except requests.exceptions.RequestException as exc:
            tentativa += 1
            if tentativa > max_retries:
                raise RuntimeError(f"Falha ao consultar estação {codigo_estacao} após {max_retries} tentativas: {exc}")
            if backoff:
                time.sleep(backoff)


def _coletar_serie(tipo: str, data_coleta: date, caminho_config: Path | None = None) -> dict[str, Any]:
    """Coleta a série (chuva|nivel) de todas as estações configuradas.

    Falha em uma estação NÃO interrompe as demais — o erro fica registrado
    no bloco daquela estação.
    """
    config = carregar_configuracao_fonte(caminho_config)
    estacoes = config.get("estacoes", [])
    if not estacoes:
        raise ValueError("Nenhuma estação configurada em 'estacoes' de ana_estacoes.yml")

    base_url = config.get("base_url", "")
    caminho_endpoint = CAMINHO_SERIE_CHUVA if tipo == "chuva" else CAMINHO_SERIE_COTAS

    token = autenticar(config)

    payload: dict[str, Any] = {}
    for estacao in estacoes:
        codigo = estacao.get("codigo")
        if not codigo:
            continue
        try:
            registros = _requisitar_serie(base_url, caminho_endpoint, token, codigo, data_coleta)
            payload[codigo] = {"records": registros, "total": len(registros)}
        except Exception as erro:
            payload[codigo] = {"erro": f"{type(erro).__name__}: {erro}"}

    return payload


def coletar_dados_chuva(data_coleta: date, caminho_config: Path | None = None) -> bytes:
    """Compatível com runner.Coletor.coletar — só busca e devolve bytes, sem gravar nada."""
    payload = _coletar_serie("chuva", data_coleta, caminho_config)
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def coletar_dados_nivel(data_coleta: date, caminho_config: Path | None = None) -> bytes:
    """Compatível com runner.Coletor.coletar — só busca e devolve bytes, sem gravar nada."""
    payload = _coletar_serie("nivel", data_coleta, caminho_config)
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def contar_registros(conteudo: bytes) -> int:
    """Compatível com runner.Coletor.contar_registros: soma os blocos de todas as estações."""
    dados = json.loads(conteudo)
    total = 0
    if isinstance(dados, dict):
        for bloco in dados.values():
            if isinstance(bloco, dict) and "records" in bloco:
                total += len(bloco["records"])
    return total


def _normalizar_timestamp(valor: Any) -> str | None:
    """Converte valor de data/hora para o formato padrão 'YYYY-MM-DD HH:MM:SS'."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    v = str(valor).strip().replace("T", " ")
    if len(v) == 10:
        return f"{v} 00:00:00"
    return v[:19]


def _transformar_serie(
    registros_raw: list[dict[str, Any]],
    mapeamento: dict[str, str],
    mapa_consistencia: dict[str, str],
    codigo_estacao: str,
) -> list[dict[str, Any]]:
    """Mapeia e tipa os registros brutos de UMA estação, para qualquer série
    (campos de valor variam entre chuva e nível/vazão, tratados genericamente)."""
    destino_para_origem = {destino: origem for origem, destino in mapeamento.items()}
    col_data = destino_para_origem.get("data_hora_medicao", "Data_Hora_Medicao")
    col_status = destino_para_origem.get("status_leitura", "NivelConsistencia")
    campos_valor = [d for d in destino_para_origem if d not in ("data_hora_medicao", "status_leitura")]

    linhas: list[dict[str, Any]] = []
    for reg in registros_raw:
        data_hora = _normalizar_timestamp(reg.get(col_data))

        status_bruto_val = reg.get(col_status)
        status_bruto = str(status_bruto_val).strip() if status_bruto_val is not None else None
        status_leitura = mapa_consistencia.get(status_bruto, status_bruto) if status_bruto else None

        linha: dict[str, Any] = {
            "codigo_estacao": codigo_estacao,
            "data_hora_medicao": data_hora,
            "status_leitura": status_leitura,
        }
        for destino in campos_valor:
            val = reg.get(destino_para_origem[destino])
            try:
                linha[destino] = float(val) if val is not None else None
            except (TypeError, ValueError):
                linha[destino] = None
        linhas.append(linha)

    return linhas


def materializar_bronze(
    tipo: str,
    data_coleta: date,
    diretorio_dados: Path = RAIZ_PROJETO / "data",
    caminho_config: Path | None = None,
) -> Path:
    """Lê a RAW já persistida pelo runner, valida contra o contrato e grava Parquet.

    tipo: 'chuva' ou 'nivel'. Se houver violações de contrato, lança exceção
    e NÃO grava Bronze parcial. Idempotência garantida pela substituição
    atômica da partição da data.
    """
    if tipo not in ("chuva", "nivel"):
        raise ValueError("tipo deve ser 'chuva' ou 'nivel'")

    fonte = f"ana_{tipo}"
    caminho_raw = (
        Path(diretorio_dados) / "raw" / fonte
        / f"{data_coleta.year:04d}" / f"{data_coleta.month:02d}"
        / f"{data_coleta.day:02d}" / "hidroweb.json"
    )
    if not caminho_raw.is_file():
        raise FileNotFoundError(f"Arquivo RAW não encontrado para a data {data_coleta}: {caminho_raw}")

    conteudo_raw = json.loads(caminho_raw.read_text(encoding="utf-8"))
    config = carregar_configuracao_fonte(caminho_config)
    mapeamento = config.get(f"mapeamento_colunas_{tipo}", {})
    mapa_consistencia = config.get("mapa_consistencia", {})

    lote_bronze: list[dict[str, Any]] = []
    for codigo_estacao, bloco in conteudo_raw.items():
        if not isinstance(bloco, dict) or "records" not in bloco:
            continue  # bloco de erro daquela estação — não entra na Bronze
        lote_bronze.extend(
            _transformar_serie(bloco["records"], mapeamento, mapa_consistencia, codigo_estacao)
        )

    contrato = contratos.carregar_contrato(fonte)
    violacoes = contratos.validar(lote_bronze, contrato)
    if violacoes:
        resumo = "; ".join(f"[{v.tipo}] {v.campo}: {v.mensagem}" for v in violacoes[:5])
        raise ValueError(f"Violações do contrato de {fonte} detectadas ({len(violacoes)}): {resumo}")

    tabela_pa = pa.Table.from_pylist(lote_bronze)
    buffer = io.BytesIO()
    pq.write_table(tabela_pa, buffer)

    caminho_bronze = (
        Path(diretorio_dados) / "bronze" / fonte
        / f"{data_coleta.year:04d}" / f"{data_coleta.month:02d}"
        / f"{data_coleta.day:02d}" / f"{fonte}.parquet"
    )
    runner.gravar_atomico(caminho_bronze, buffer.getvalue())
    return caminho_bronze


def coletar_e_materializar(
    tipo: str,
    data_coleta: date | None = None,
    diretorio_dados: Path = RAIZ_PROJETO / "data",
    caminho_config: Path | None = None,
) -> dict[str, Any]:
    """Fluxo completo de ponta a ponta para uma série: coleta RAW via runner e materializa Bronze."""
    fonte = f"ana_{tipo}"
    registro = runner.executar(fonte, data_coleta=data_coleta, diretorio_dados=diretorio_dados)

    if registro.get("status") != "ok":
        return {"execucao": registro, "bronze": None}

    data_particao = date.fromisoformat(registro["data_coleta"])
    try:
        caminho_bronze = materializar_bronze(
            tipo, data_particao, diretorio_dados=diretorio_dados, caminho_config=caminho_config
        )
        return {"execucao": registro, "bronze": str(caminho_bronze)}
    except Exception as erro:
        registro["status"] = "erro"
        registro["mensagem"] = f"Erro ao materializar Bronze ({fonte}): {type(erro).__name__}: {erro}"
        return {"execucao": registro, "bronze": None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serie", choices=["chuva", "nivel", "todas"], default="todas")
    parser.add_argument("--data", type=runner.interpretar_data, dest="data_coleta")
    parser.add_argument(
        "--diretorio-dados", type=Path, default=RAIZ_PROJETO / "data",
        help="Diretório raiz de dados; padrão: data/ do projeto",
    )
    opcoes = parser.parse_args()

    tipos = ["chuva", "nivel"] if opcoes.serie == "todas" else [opcoes.serie]
    resultados = {}
    codigo_saida = 0
    for tipo in tipos:
        resultado = coletar_e_materializar(
            tipo, data_coleta=opcoes.data_coleta, diretorio_dados=opcoes.diretorio_dados
        )
        resultados[tipo] = resultado
        if not (resultado["execucao"].get("status") == "ok" and resultado.get("bronze")):
            codigo_saida = 1

    print(json.dumps(resultados, ensure_ascii=False, indent=2))
    return codigo_saida


if __name__ == "__main__":
    raise SystemExit(main())
