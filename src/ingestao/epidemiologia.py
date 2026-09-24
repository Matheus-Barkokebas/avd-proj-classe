"""Coleta de dados epidemiológicos de arboviroses (ING-02).

Coleta dados de dengue, zika e chikungunya da API DataStore do CKAN do Recife
(reusando recife_ckan), persiste RAW fielmente particionada e materializa
a camada Bronze em Parquet validando contra o contrato de dados (FND-02).
"""

import argparse
from datetime import date, datetime
import io
import json
from pathlib import Path
from typing import Any
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from src.ingestao import contratos
from src.ingestao import recife_ckan
from src.ingestao import runner


RAIZ_PROJETO = Path(__file__).resolve().parents[2]
CAMINHO_CONFIG_PADRAO = RAIZ_PROJETO / "conf" / "sources" / "epidemiologia.yml"


def carregar_configuracao_fonte(caminho_config: Path | None = None) -> dict[str, Any]:
    """Carrega o arquivo de configuração conf/sources/epidemiologia.yml."""
    caminho = caminho_config if caminho_config is not None else CAMINHO_CONFIG_PADRAO
    if not caminho.is_file():
        raise FileNotFoundError(f"Configuração de fonte não encontrada: {caminho}")
    with caminho.open(encoding="utf-8") as arquivo:
        config = yaml.safe_load(arquivo)
    if not isinstance(config, dict):
        raise ValueError(f"Conteúdo inválido na configuração de fonte: {caminho}")
    return config


def coletar_dados(data_coleta: date, caminho_config: Path | None = None) -> bytes:
    """Busca os dados de cada agravo configurado via CKAN e devolve bytes brutos.

    Compatível com runner.Coletor.coletar: não grava arquivos em disco,
    apenas consulta a API e monta o payload combinado com os dados brutos.
    """
    config = carregar_configuracao_fonte(caminho_config)
    recursos = config.get("recursos", {})
    if not recursos:
        raise ValueError("Nenhum recurso configurado em 'recursos' de epidemiologia.yml")

    payload_combinado: dict[str, Any] = {}
    for agravo, resource_id in recursos.items():
        registros, metadados = recife_ckan.coletar_todos(resource_id)
        payload_combinado[agravo] = {
            "records": registros,
            "total": metadados.get("total", len(registros)),
            "coletado_em": metadados.get("coletado_em", datetime.now().isoformat()),
        }

    return json.dumps(payload_combinado, ensure_ascii=False, indent=2).encode("utf-8")


def contar_registros(conteudo: bytes) -> int:
    """Compatível com runner.Coletor.contar_registros: soma registros dos agravos."""
    dados = json.loads(conteudo)
    if isinstance(dados, dict):
        # Soma os records de cada bloco de agravo
        total = 0
        for bloco in dados.values():
            if isinstance(bloco, dict) and "records" in bloco:
                total += len(bloco["records"])
            elif isinstance(bloco, list):
                total += len(bloco)
        return total
    if isinstance(dados, list):
        return len(dados)
    return 0


def _normalizar_timestamp(valor: Any) -> str:
    """Converte valor de data/hora para o formato padrão 'YYYY-MM-DD HH:MM:SS'."""
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(valor, str):
        v = valor.strip().replace("T", " ")
        if len(v) == 10:  # YYYY-MM-DD
            return f"{v} 00:00:00"
        if len(v) >= 19:
            return v[:19]
        return v
    return str(valor)


def _transformar_para_bronze(
    registros_raw: list[dict[str, Any]],
    mapeamento: dict[str, str],
    agravo: str,
) -> list[dict[str, Any]]:
    """Mapeia e tipa os registros brutos de um agravo conforme o contrato Bronze."""
    # Mapeamento invertido: nome_destino -> nome_origem
    destino_para_origem = {destino: origem for origem, destino in mapeamento.items()}

    col_protocolo = destino_para_origem.get("protocolo", "NU_NOTIFIC")
    col_data = destino_para_origem.get("data_notificacao", "DT_NOTIFIC")
    col_semana = destino_para_origem.get("semana_epidemiologica", "SEM_NOT")
    col_ano = destino_para_origem.get("ano", "NU_ANO")
    col_bairro = destino_para_origem.get("bairro", "NM_BAIRRO")
    col_classi = destino_para_origem.get("classificacao_final", "CLASSI_FIN")

    registros_bronze: list[dict[str, Any]] = []
    for reg in registros_raw:
        # Conversão de protocolo para string
        val_protocolo = reg.get(col_protocolo)
        if val_protocolo is not None:
            if isinstance(val_protocolo, (int, float)):
                protocolo = str(int(val_protocolo))
            else:
                protocolo = str(val_protocolo)
        else:
            protocolo = None

        # Data de notificação formatada
        val_data = reg.get(col_data)
        data_notificacao = _normalizar_timestamp(val_data) if val_data is not None else None

        # Semana e ano inteiros
        val_semana = reg.get(col_semana)
        semana_epi = int(val_semana) if val_semana is not None else None

        val_ano = reg.get(col_ano)
        ano = int(val_ano) if val_ano is not None else None

        # Bairro como string original (sem normalização nesta etapa)
        val_bairro = reg.get(col_bairro)
        bairro = str(val_bairro).strip() if val_bairro is not None else None

        # Classificação final como string (opcional)
        val_classi = reg.get(col_classi)
        classificacao = str(val_classi).strip() if val_classi is not None else None

        registros_bronze.append(
            {
                "protocolo": protocolo,
                "data_notificacao": data_notificacao,
                "semana_epidemiologica": semana_epi,
                "ano": ano,
                "bairro": bairro,
                "agravo": agravo.lower(),
                "classificacao_final": classificacao,
                "contagem": 1,
            }
        )

    return registros_bronze


def materializar_bronze(
    data_coleta: date,
    diretorio_dados: Path = RAIZ_PROJETO / "data",
    caminho_config: Path | None = None,
) -> Path:
    """Lê a RAW já persistida pelo runner, valida contra o contrato e grava Parquet.

    Se houver violações de contrato, lança exceção e NÃO grava Bronze parcial.
    Idempotência garantida pela substituição atômica da partição da data.
    """
    caminho_raw = (
        Path(diretorio_dados) / "raw" / "epidemiologia"
        / f"{data_coleta.year:04d}" / f"{data_coleta.month:02d}"
        / f"{data_coleta.day:02d}" / "datastore_search.json"
    )
    if not caminho_raw.is_file():
        raise FileNotFoundError(f"Arquivo RAW não encontrado para a data {data_coleta}: {caminho_raw}")

    conteudo_raw = json.loads(caminho_raw.read_text(encoding="utf-8"))
    config = carregar_configuracao_fonte(caminho_config)
    mapeamento = config.get("mapeamento_colunas", {})

    lote_bronze: list[dict[str, Any]] = []

    if isinstance(conteudo_raw, dict):
        for agravo, bloco in conteudo_raw.items():
            if isinstance(bloco, dict) and "records" in bloco:
                registros = bloco["records"]
            elif isinstance(bloco, list):
                registros = bloco
            else:
                continue
            lote_bronze.extend(_transformar_para_bronze(registros, mapeamento, agravo))
    elif isinstance(conteudo_raw, list):
        lote_bronze.extend(_transformar_para_bronze(conteudo_raw, mapeamento, "dengue"))

    # Validação do lote contra o contrato FND-02
    contrato = contratos.carregar_contrato("epidemiologia")
    violacoes = contratos.validar(lote_bronze, contrato)
    if violacoes:
        resumo = "; ".join(f"[{v.tipo}] {v.campo}: {v.mensagem}" for v in violacoes[:5])
        raise ValueError(f"Violações do contrato de epidemiologia detectadas ({len(violacoes)}): {resumo}")

    # Materialização em Parquet usando PyArrow
    tabela_pa = pa.Table.from_pylist(lote_bronze)
    buffer = io.BytesIO()
    pq.write_table(tabela_pa, buffer)
    conteudo_parquet = buffer.getvalue()

    caminho_bronze = (
        Path(diretorio_dados) / "bronze" / "epidemiologia"
        / f"{data_coleta.year:04d}" / f"{data_coleta.month:02d}"
        / f"{data_coleta.day:02d}" / "epidemiologia.parquet"
    )
    runner.gravar_atomico(caminho_bronze, conteudo_parquet)
    return caminho_bronze


def coletar_e_materializar(
    data_coleta: date | None = None,
    diretorio_dados: Path = RAIZ_PROJETO / "data",
    caminho_config: Path | None = None,
) -> dict[str, Any]:
    """Fluxo completo de ponta a ponta: coleta RAW via runner e materializa Bronze."""
    registro = runner.executar(
        "epidemiologia",
        data_coleta=data_coleta,
        diretorio_dados=diretorio_dados,
    )

    if registro.get("status") != "ok":
        return {"execucao": registro, "bronze": None}

    data_particao = date.fromisoformat(registro["data_coleta"])
    try:
        caminho_bronze = materializar_bronze(
            data_particao,
            diretorio_dados=diretorio_dados,
            caminho_config=caminho_config,
        )
        return {"execucao": registro, "bronze": str(caminho_bronze)}
    except Exception as erro:
        registro["status"] = "erro"
        registro["mensagem"] = f"Erro ao materializar Bronze: {type(erro).__name__}: {erro}"
        return {"execucao": registro, "bronze": None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=runner.interpretar_data, dest="data_coleta")
    parser.add_argument(
        "--diretorio-dados", type=Path, default=RAIZ_PROJETO / "data",
        help="Diretório raiz de dados; padrão: data/ do projeto",
    )
    opcoes = parser.parse_args()

    resultado = coletar_e_materializar(
        data_coleta=opcoes.data_coleta,
        diretorio_dados=opcoes.diretorio_dados,
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado["execucao"].get("status") == "ok" and resultado.get("bronze") else 1


if __name__ == "__main__":
    raise SystemExit(main())
