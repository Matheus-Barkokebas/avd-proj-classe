"""Coleta de ocorrências e chamados da Defesa Civil (ING-03).

Coleta o feed "Sedec Solicitações Tempo Real" do Dados Abertos Recife
(reusando recife_ckan), persiste RAW fielmente particionada e materializa
a camada Bronze em Parquet validando contra o contrato de dados (FND-02).

Sem transformação semântica além de tipagem e tradução de status — nenhuma
validação geográfica ou vínculo com áreas de risco (isso é INT-02).
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

from src.ingestao import bronze
from src.ingestao import recife_ckan
from src.ingestao import runner


RAIZ_PROJETO = Path(__file__).resolve().parents[2]
CAMINHO_CONFIG_PADRAO = RAIZ_PROJETO / "conf" / "sources" / "ocorrencias.yml"


def carregar_configuracao_fonte(caminho_config: Path | None = None) -> dict[str, Any]:
    """Carrega o arquivo de configuração conf/sources/ocorrencias.yml."""
    caminho = caminho_config if caminho_config is not None else CAMINHO_CONFIG_PADRAO
    if not caminho.is_file():
        raise FileNotFoundError(f"Configuração de fonte não encontrada: {caminho}")
    with caminho.open(encoding="utf-8") as arquivo:
        config = yaml.safe_load(arquivo)
    if not isinstance(config, dict):
        raise ValueError(f"Conteúdo inválido na configuração de fonte: {caminho}")
    return config


def coletar_dados(data_coleta: date, caminho_config: Path | None = None) -> bytes:
    """Busca as ocorrências via CKAN e devolve bytes brutos.

    Compatível com runner.Coletor.coletar: não grava arquivo em disco,
    apenas consulta a API e serializa o payload combinado (RAW fiel).
    """
    config = carregar_configuracao_fonte(caminho_config)
    resource_id = config.get("resource_id")
    if not resource_id:
        raise ValueError("'resource_id' não configurado em ocorrencias.yml")

    registros, metadados = recife_ckan.coletar_todos(resource_id)
    payload = {
        "records": registros,
        "total": metadados.get("total", len(registros)),
        "coletado_em": metadados.get("coletado_em", datetime.now().isoformat()),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def contar_registros(conteudo: bytes) -> int:
    """Compatível com runner.Coletor.contar_registros."""
    dados = json.loads(conteudo)
    if isinstance(dados, dict) and "records" in dados:
        return len(dados["records"])
    if isinstance(dados, list):
        return len(dados)
    return 0


def _combinar_data_hora(data_str: Any, hora_str: Any) -> str | None:
    """Combina solicitacao_data ('YYYY-MM-DD') + solicitacao_hora ('HH:MM')
    no formato padrão 'YYYY-MM-DD HH:MM:SS' (PADROES §3)."""
    if not data_str:
        return None
    data_str = str(data_str).strip()[:10]
    hora_str = str(hora_str).strip() if hora_str else "00:00"
    partes_hora = hora_str.split(":")
    hh = partes_hora[0].zfill(2) if len(partes_hora) > 0 and partes_hora[0] else "00"
    mm = partes_hora[1].zfill(2) if len(partes_hora) > 1 and partes_hora[1] else "00"
    return f"{data_str} {hh}:{mm}:00"


def _transformar_para_bronze(
    registros_raw: list[dict[str, Any]],
    mapeamento: dict[str, str],
    mapa_status: dict[str, str],
) -> list[dict[str, Any]]:
    """Mapeia e tipa os registros brutos conforme o contrato Bronze.

    Sem normalização de bairro nem validação geográfica (INT-02) — bairro e
    coordenadas são repassados como vieram. Registros sem coordenada são
    mantidos (latitude/longitude ficam None — são opcionais no contrato).
    """
    # Mapeamento invertido: nome_destino -> nome_origem
    destino_para_origem = {destino: origem for origem, destino in mapeamento.items()}

    col_protocolo = destino_para_origem.get("protocolo", "processo_numero")
    col_bairro = destino_para_origem.get("bairro", "solicitacao_bairro")
    col_tipo = destino_para_origem.get("tipo_ocorrencia", "processo_solicitacao")
    col_status = destino_para_origem.get("status", "processo_situacao")
    col_descricao = destino_para_origem.get("descricao", "solicitacao_descricao")

    registros_bronze: list[dict[str, Any]] = []
    for reg in registros_raw:
        val_protocolo = reg.get(col_protocolo)
        if val_protocolo is not None:
            if isinstance(val_protocolo, (int, float)):
                protocolo = str(int(val_protocolo))
            else:
                protocolo = str(val_protocolo).strip()
        else:
            protocolo = None

        data_ocorrencia = _combinar_data_hora(
            reg.get("solicitacao_data"), reg.get("solicitacao_hora")
        )

        val_bairro = reg.get(col_bairro)
        bairro = str(val_bairro).strip() if val_bairro is not None else None

        val_tipo = reg.get(col_tipo)
        tipo_ocorrencia = str(val_tipo).strip() if val_tipo is not None else None

        val_status = reg.get(col_status)
        status_bruto = str(val_status).strip() if val_status is not None else None
        # Traduz pelo mapa; valor sem entrada passa intacto (falha a validação
        # do contrato de propósito, em vez de forçar um valor plausível).
        status = mapa_status.get(status_bruto, status_bruto) if status_bruto else None

        val_descricao = reg.get(col_descricao)
        descricao = str(val_descricao).strip() if val_descricao is not None else None

        # Esta fonte não possui campos de latitude/longitude (só localização
        # textual). Registro é mantido normalmente — não descartar.
        registros_bronze.append(
            {
                "protocolo": protocolo,
                "data_ocorrencia": data_ocorrencia,
                "tipo_ocorrencia": tipo_ocorrencia,
                "bairro": bairro,
                "latitude": None,
                "longitude": None,
                "status": status,
                "descricao": descricao,
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
        Path(diretorio_dados) / "raw" / "ocorrencias"
        / f"{data_coleta.year:04d}" / f"{data_coleta.month:02d}"
        / f"{data_coleta.day:02d}" / "datastore_search.json"
    )
    if not caminho_raw.is_file():
        raise FileNotFoundError(f"Arquivo RAW não encontrado para a data {data_coleta}: {caminho_raw}")

    conteudo_raw = json.loads(caminho_raw.read_text(encoding="utf-8"))
    config = carregar_configuracao_fonte(caminho_config)
    mapeamento = config.get("mapeamento_colunas", {})
    mapa_status = config.get("mapa_status", {})

    registros = conteudo_raw.get("records", []) if isinstance(conteudo_raw, dict) else conteudo_raw
    lote_bronze = _transformar_para_bronze(registros, mapeamento, mapa_status)

    # Validação do lote contra o contrato FND-02
    # Linhas inválidas vão para a quarentena; violação de lote ou todas as
    # linhas rejeitadas abortam sem gravar (BUG-06).
    return bronze.gravar_validado(lote_bronze, "ocorrencias", "ocorrencias", data_coleta, diretorio_dados)


def coletar_e_materializar(
    data_coleta: date | None = None,
    diretorio_dados: Path = RAIZ_PROJETO / "data",
    caminho_config: Path | None = None,
) -> dict[str, Any]:
    """Fluxo completo de ponta a ponta: coleta RAW via runner e materializa Bronze."""
    registro = runner.executar(
        "ocorrencias",
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
            "rejeitados": bronze.contar_rejeitados(diretorio_dados, "ocorrencias", data_particao),
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
