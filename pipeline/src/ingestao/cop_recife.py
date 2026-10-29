"""Coleta do Centro de Operações do Recife — COP (chuva, rios, previsão e alagamento).

Cada camada configurada em conf/sources/cop_recife.yml é uma fonte própria:
RAW (resposta original do ArcGIS, via runner) -> validação pelo contrato
conf/contracts/<fonte>.yml -> camada padronizada (Neon ou Parquet local).

As tabelas "atuais" do COP (indicadores e rios) guardam só ~24h; rodando de
hora em hora, a camada padronizada acumula o histórico (upsert pela chave de
negócio). A RAW do dia é substituída a cada coleta — e cada coleta já traz a
janela das últimas ~24h.

Uso:
    python src/ingestao/cop_recife.py                 # todas as camadas
    python src/ingestao/cop_recife.py --fonte cop_rios --armazenamento mongo --padronizada neon
"""

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from typing import Any

import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestao import arcgis
from src.ingestao import armazenamento as armaz
from src.ingestao import bronze
from src.ingestao import padronizada
from src.ingestao import runner

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
CAMINHO_CONFIG_PADRAO = RAIZ_PROJETO / "conf" / "sources" / "cop_recife.yml"
ARQUIVO_RAW = "arcgis.json"
FUSO_RECIFE = timezone(timedelta(hours=-3), name="America/Recife")
MESES = {"JANEIRO": 1, "FEVEREIRO": 2, "MARCO": 3, "MARÇO": 3, "ABRIL": 4, "MAIO": 5, "JUNHO": 6,
         "JULHO": 7, "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12}


def carregar_configuracao_fonte(caminho_config: Path | None = None) -> dict[str, Any]:
    caminho = caminho_config if caminho_config is not None else CAMINHO_CONFIG_PADRAO
    if not caminho.is_file():
        raise FileNotFoundError(f"Configuração de fonte não encontrada: {caminho}")
    with caminho.open(encoding="utf-8") as arquivo:
        config = yaml.safe_load(arquivo)
    if not isinstance(config, dict) or not isinstance(config.get("camadas"), dict):
        raise ValueError(f"Conteúdo inválido na configuração de fonte: {caminho}")
    return config


def camadas(caminho_config: Path | None = None) -> list[str]:
    return list(carregar_configuracao_fonte(caminho_config)["camadas"])


def _camada(fonte: str, config: dict[str, Any]) -> dict[str, Any]:
    if fonte not in config["camadas"]:
        raise ValueError(f"Camada do COP não configurada: {fonte}")
    return config["camadas"][fonte]


# ------------------------------------------------------------------ coleta (RAW)
def coletar_dados(fonte: str, data_coleta: date, caminho_config: Path | None = None) -> bytes:
    """Compatível com runner.Coletor.coletar: consulta o ArcGIS e devolve bytes, sem gravar."""
    config = carregar_configuracao_fonte(caminho_config)
    camada = _camada(fonte, config)
    url = f"{config['base_url'].rstrip('/')}/{camada['servico']}/MapServer/{camada['camada']}"
    feicoes = arcgis.consultar(url, formato=camada.get("formato", "json"),
                               ordenar_por=camada.get("ordenar_por", "OBJECTID"))
    payload = {
        "fonte": fonte, "url": url, "formato": camada.get("formato", "json"),
        "consultado_em": datetime.now(FUSO_RECIFE).strftime("%Y-%m-%d %H:%M:%S"),
        "features": feicoes,
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def contar_registros(conteudo: bytes) -> int:
    return len(json.loads(conteudo).get("features", []))


# ------------------------------------------------------------------ conversões
def _vazio(valor: Any) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def _epoch(valor: Any, fuso: timezone, so_data: bool = False) -> str | None:
    if _vazio(valor):
        return None
    momento = datetime.fromtimestamp(float(valor) / 1000, fuso)
    return momento.strftime("%Y-%m-%d") if so_data else momento.strftime("%Y-%m-%d %H:%M:%S")


def _data_hora_texto(data_txt: Any, hora_txt: Any) -> str | None:
    if _vazio(data_txt):
        return None
    hora = str(hora_txt).strip() if not _vazio(hora_txt) else "00:00:00"
    if len(hora) == 5:
        hora += ":00"
    return datetime.strptime(f"{str(data_txt).strip()} {hora}", "%d/%m/%Y %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")


def _numero(valor: Any) -> float | None:
    if _vazio(valor):
        return None
    try:
        return float(str(valor).replace(",", ".")) if isinstance(valor, str) else float(valor)
    except ValueError:
        return valor  # passa intacto: o contrato rejeita e registra o motivo


def _inteiro(valor: Any) -> int | None:
    if _vazio(valor):
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return valor  # o contrato rejeita
    return int(numero) if numero.is_integer() else valor


def _ponto(geometria: Any, indice: int) -> float | None:
    if isinstance(geometria, dict) and geometria.get("type") == "Point":
        return float(geometria["coordinates"][indice])
    return None


def converter(regra: dict[str, Any], atributos: dict[str, Any], geometria: Any, data_coleta: date) -> Any:
    """Aplica uma regra de conversão do YAML a uma feição."""
    tipo = regra["converter"]
    origem = regra.get("origem")
    valor = None if isinstance(origem, list) or origem is None else atributos.get(origem)
    if tipo == "texto":
        return None if _vazio(valor) else str(valor).strip()
    if tipo == "numero":
        return _numero(valor)
    if tipo == "inteiro":
        return _inteiro(valor)
    if tipo == "epoch_utc":
        return _epoch(valor, FUSO_RECIFE)
    if tipo == "epoch_local":
        return _epoch(valor, timezone.utc)  # o "UTC" da fonte já é o relógio local
    if tipo == "epoch_data":
        return _epoch(valor, timezone.utc, so_data=True)
    if tipo == "data_hora_texto":
        return _data_hora_texto(atributos.get(origem[0]), atributos.get(origem[1]))
    if tipo == "mes_nome":
        return None if _vazio(valor) else MESES.get(str(valor).strip().upper(), valor)
    if tipo == "ano_coleta":
        return data_coleta.year
    if tipo == "geometria":
        return json.dumps(geometria, ensure_ascii=False, separators=(",", ":")) if geometria else None
    if tipo == "longitude":
        return _ponto(geometria, 0)
    if tipo == "latitude":
        return _ponto(geometria, 1)
    raise ValueError(f"Conversão desconhecida no cop_recife.yml: {tipo!r}")


def transformar(conteudo_raw: dict[str, Any], camada: dict[str, Any], data_coleta: date) -> list[dict[str, Any]]:
    """Feições do ArcGIS -> linhas no formato do contrato (sem descartar nada aqui)."""
    linhas = []
    for feicao in conteudo_raw.get("features", []):
        if "attributes" in feicao:
            atributos, geometria = feicao["attributes"], None
        else:
            atributos, geometria = feicao.get("properties") or {}, feicao.get("geometry")
        linhas.append({destino: converter(regra, atributos, geometria, data_coleta)
                       for destino, regra in camada["campos"].items()})
    return linhas


# ------------------------------------------------------------------ padronizada
def materializar(
    fonte: str,
    data_coleta: date,
    diretorio_dados: Path = RAIZ_PROJETO / "data",
    caminho_config: Path | None = None,
    armazenamento: armaz.ArmazenamentoRaw | None = None,
    destino: padronizada.DestinoNeon | None = None,
) -> Path | str:
    """Lê a RAW gravada pelo runner, valida contra o contrato e grava a camada padronizada."""
    if armazenamento is None:
        armazenamento = armaz.ArmazenamentoArquivo(diretorio_dados)
    camada = _camada(fonte, carregar_configuracao_fonte(caminho_config))
    conteudo_raw = armaz.ler_json(armazenamento, fonte, data_coleta, ARQUIVO_RAW)
    lote = transformar(conteudo_raw, camada, data_coleta)
    return bronze.gravar_validado(lote, fonte, fonte, data_coleta, diretorio_dados, destino=destino)


def coletar_e_materializar(
    fonte: str,
    data_coleta: date | None = None,
    diretorio_dados: Path = RAIZ_PROJETO / "data",
    caminho_config: Path | None = None,
    armazenamento: armaz.ArmazenamentoRaw | None = None,
    destino: padronizada.DestinoNeon | None = None,
) -> dict[str, Any]:
    if armazenamento is None:
        armazenamento = armaz.ArmazenamentoArquivo(diretorio_dados)
    registro = runner.executar(fonte, data_coleta=data_coleta, diretorio_dados=diretorio_dados,
                               armazenamento=armazenamento)
    if registro.get("status") != "ok":
        return {"execucao": registro, "padronizada": None}
    data_particao = date.fromisoformat(registro["data_coleta"])
    try:
        resultado = materializar(fonte, data_particao, diretorio_dados, caminho_config, armazenamento, destino)
        return {"execucao": registro, "padronizada": str(resultado),
                "rejeitados": bronze.contar_rejeitados(diretorio_dados, fonte, data_particao, destino)}
    except Exception as erro:
        registro["status"] = "erro"
        registro["mensagem"] = f"Erro ao padronizar ({fonte}): {type(erro).__name__}: {erro}"
        return {"execucao": registro, "padronizada": None}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fonte", choices=camadas() + ["todas"], default="todas",
                        help="Camada do COP a coletar; padrão: todas")
    parser.add_argument("--frequencia", choices=["horaria", "diaria", "mensal"], default=None,
                        help="Só as camadas desta frequência (para o agendador)")
    parser.add_argument("--data", type=runner.interpretar_data, dest="data_coleta")
    parser.add_argument("--diretorio-dados", type=Path, default=RAIZ_PROJETO / "data")
    parser.add_argument("--armazenamento", choices=armaz.TIPOS, default=None,
                        help="Onde fica a RAW; padrão: AERVITA_ARMAZENAMENTO ou arquivo")
    parser.add_argument("--padronizada", choices=["arquivo", "neon"], default=None,
                        help="Onde gravar os dados validados; padrão: AERVITA_PADRONIZADA ou arquivo (Parquet)")
    opcoes = parser.parse_args()

    config = carregar_configuracao_fonte()
    fontes = camadas() if opcoes.fonte == "todas" else [opcoes.fonte]
    if opcoes.frequencia:
        fontes = [f for f in fontes if config["camadas"][f].get("frequencia") == opcoes.frequencia]
    destino_raw = armaz.criar(opcoes.armazenamento, opcoes.diretorio_dados)
    destino_padronizada = padronizada.criar(opcoes.padronizada)
    resultados = {f: coletar_e_materializar(f, opcoes.data_coleta, opcoes.diretorio_dados,
                                            armazenamento=destino_raw, destino=destino_padronizada)
                  for f in fontes}
    print(json.dumps(resultados, ensure_ascii=False, indent=2))
    falhou = any(r["execucao"].get("status") != "ok" or not r.get("padronizada") for r in resultados.values())
    return 1 if falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
