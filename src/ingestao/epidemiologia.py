"""Coleta de dados epidemiológicos de arboviroses (ING-02).

Coleta dados de dengue, zika e chikungunya da API DataStore do CKAN do Recife
(reusando recife_ckan), persiste RAW fielmente particionada e materializa
a camada Bronze em Parquet validando contra o contrato de dados (FND-02).
"""

import argparse
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any
import yaml
import sys

# Executado como script (`python src/ingestao/<modulo>.py`), o Python põe
# src/ingestao/ no sys.path em vez da raiz do projeto — sem isto os imports
# `src.*` falham com ModuleNotFoundError (BUG-02).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestao import comum
from src.ingestao import bronze
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
        # Os recursos de cada agravo não usam os mesmos tipos/formatos
        # (ex.: dengue manda data ISO e NU_NOTIFIC numérico; zika e
        # chikungunya mandam DD/MM/AAAA e texto) — a tipagem é centralizada
        # em comum.py. Bairro segue sem normalização (INT-02).
        registros_bronze.append(
            {
                "protocolo": comum.para_texto(reg.get(col_protocolo)),
                "data_notificacao": comum.normalizar_timestamp(reg.get(col_data)),
                "semana_epidemiologica": comum.para_int(reg.get(col_semana)),
                "ano": comum.para_int(reg.get(col_ano)),
                "bairro": comum.para_texto(reg.get(col_bairro)),
                "agravo": agravo.lower(),
                "classificacao_final": comum.para_texto(reg.get(col_classi)),
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
    # Linhas inválidas vão para a quarentena; violação de lote ou todas as
    # linhas rejeitadas abortam sem gravar (BUG-06).
    return bronze.gravar_validado(lote_bronze, "epidemiologia", "epidemiologia", data_coleta, diretorio_dados)


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
        return {
            "execucao": registro,
            "bronze": str(caminho_bronze),
            "rejeitados": bronze.contar_rejeitados(diretorio_dados, "epidemiologia", data_particao),
        }
    except Exception as erro:
        registro["status"] = "erro"
        registro["mensagem"] = f"Erro ao materializar Bronze: {type(erro).__name__}: {erro}"
        return {"execucao": registro, "bronze": None}


def main() -> int:
    # Saída redirecionada no Windows usa cp1252 e quebra com caracteres fora
    # dessa tabela (ex.: "↔" nas docstrings) — forçar UTF-8 (BUG-02).
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
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
