"""Coleta de bases cadastrais territoriais do Recife (ING-05).

Coleta, para cada base configurada em conf/sources/territorio.yml:
- bases TABULARES via recife_ckan.coletar_todos (datastore_search do CKAN);
- bases GEOMÉTRICAS via download direto do arquivo (GeoJSON, preservado no
  formato de origem — não convertido para Parquet).

RAW combina todas as bases num único payload (a fonte "territorio" é uma só,
conforme conf/schedule.yml). Bronze materializa UMA TABELA POR BASE — nenhuma
é cruzada com outra aqui: montar a correspondência bairro ↔ RPA ↔ Distrito
Sanitário é escopo da INT-02 (Silver), não desta issue.

Nota de escopo: diferente de epidemiologia.py/ocorrencias.py, este módulo
NÃO valida contra conf/contracts/territorio.yml via contratos.validar(). Esse
contrato descreve a tabela já RESOLVIDA (com distrito_sanitario obrigatório
por bairro), que só existe depois do cruzamento feito pela INT-02 — exigir
isso aqui contradiria o "Fora de escopo" desta história. Cada base é
materializada tal como a fonte publica.
"""

import argparse
import base64
from datetime import date
import io
import json
from pathlib import Path
import re
import time
from typing import Any
import pyarrow as pa
import pyarrow.parquet as pq
import requests
import yaml

from src.ingestao import recife_ckan
from src.ingestao import runner


RAIZ_PROJETO = Path(__file__).resolve().parents[2]
CAMINHO_CONFIG_PADRAO = RAIZ_PROJETO / "conf" / "sources" / "territorio.yml"

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF = 0


def carregar_configuracao_fonte(caminho_config: Path | None = None) -> dict[str, Any]:
    """Carrega o arquivo de configuração conf/sources/territorio.yml."""
    caminho = caminho_config if caminho_config is not None else CAMINHO_CONFIG_PADRAO
    if not caminho.is_file():
        raise FileNotFoundError(f"Configuração de fonte não encontrada: {caminho}")
    with caminho.open(encoding="utf-8") as arquivo:
        config = yaml.safe_load(arquivo)
    if not isinstance(config, dict):
        raise ValueError(f"Conteúdo inválido na configuração de fonte: {caminho}")
    return config


def _baixar_arquivo(url: str, max_retries: int = DEFAULT_MAX_RETRIES, backoff: int = DEFAULT_BACKOFF) -> bytes:
    """Baixa um arquivo (ex.: GeoJSON) tal como publicado, com retry."""
    tentativa = 0
    while True:
        try:
            resposta = requests.get(url, timeout=60)
            resposta.raise_for_status()
            return resposta.content
        except requests.exceptions.RequestException as exc:
            tentativa += 1
            if tentativa > max_retries:
                raise RuntimeError(f"Falha ao baixar arquivo ({url}) após {max_retries} tentativas: {exc}")
            if backoff:
                time.sleep(backoff)


def coletar_dados(data_coleta: date, caminho_config: Path | None = None) -> bytes:
    """Compatível com runner.Coletor.coletar — coleta as bases tabulares e
    geométricas configuradas e devolve o payload combinado, sem gravar nada."""
    config = carregar_configuracao_fonte(caminho_config)
    payload: dict[str, Any] = {}

    for nome_base, cfg_base in config.get("bases_tabulares", {}).items():
        resource_id = cfg_base.get("resource_id")
        if not resource_id:
            continue
        registros, metadados = recife_ckan.coletar_todos(resource_id)
        payload[nome_base] = {
            "tipo": "tabular",
            "records": registros,
            "total": metadados.get("total", len(registros)),
        }

    for nome_base, cfg_base in config.get("bases_geometricas", {}).items():
        url = cfg_base.get("url")
        if not url:
            continue
        conteudo = _baixar_arquivo(url)
        payload[nome_base] = {
            "tipo": "arquivo",
            "formato": cfg_base.get("formato", "geojson"),
            "conteudo_base64": base64.b64encode(conteudo).decode("ascii"),
        }

    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def contar_registros(conteudo: bytes) -> int:
    """Compatível com runner.Coletor.contar_registros.

    Soma linhas das bases tabulares; cada base geométrica conta como 1
    (é um arquivo, não uma coleção de registros)."""
    dados = json.loads(conteudo)
    total = 0
    for bloco in dados.values():
        if not isinstance(bloco, dict):
            continue
        if bloco.get("tipo") == "tabular":
            total += len(bloco.get("records", []))
        elif bloco.get("tipo") == "arquivo":
            total += 1
    return total


def _extrair_numero_distrito(valor: Any) -> int | None:
    """Extrai o número de textos como 'Distrito Sanitário 3' -> 3."""
    if valor is None:
        return None
    match = re.search(r"(\d+)", str(valor))
    return int(match.group(1)) if match else None


def _transformar_tabular(registros_raw: list[dict[str, Any]], mapeamento: dict[str, str]) -> list[dict[str, Any]]:
    """Aplica o de/para de colunas de uma base tabular, sem cruzar com outra base."""
    linhas: list[dict[str, Any]] = []
    for reg in registros_raw:
        linha: dict[str, Any] = {}
        for origem, destino in mapeamento.items():
            valor = reg.get(origem)
            if destino == "distrito_sanitario":
                linha[destino] = _extrair_numero_distrito(valor)
            elif destino == "rpa" and valor is not None:
                linha[destino] = int(valor)
            elif valor is not None:
                linha[destino] = str(valor).strip()
            else:
                linha[destino] = None
        linhas.append(linha)
    return linhas


def materializar_bronze(
    data_coleta: date,
    diretorio_dados: Path = RAIZ_PROJETO / "data",
    caminho_config: Path | None = None,
) -> dict[str, Path]:
    """Lê a RAW já persistida pelo runner e materializa UMA saída por base:
    Parquet para bases tabulares, arquivo preservado (ex. GeoJSON) para
    bases geométricas. Sem validação contra conf/contracts/territorio.yml
    (ver nota de escopo no topo do módulo) e sem cruzar bases entre si.

    Idempotência garantida pela substituição atômica de cada partição.
    Devolve {nome_base: caminho_gravado}.
    """
    caminho_raw = (
        Path(diretorio_dados) / "raw" / "territorio"
        / f"{data_coleta.year:04d}" / f"{data_coleta.month:02d}"
        / f"{data_coleta.day:02d}" / "territorio.json"
    )
    if not caminho_raw.is_file():
        raise FileNotFoundError(f"Arquivo RAW não encontrado para a data {data_coleta}: {caminho_raw}")

    conteudo_raw = json.loads(caminho_raw.read_text(encoding="utf-8"))
    config = carregar_configuracao_fonte(caminho_config)
    bases_tabulares = config.get("bases_tabulares", {})

    caminhos_gravados: dict[str, Path] = {}
    particao = f"{data_coleta.year:04d}/{data_coleta.month:02d}/{data_coleta.day:02d}"

    for nome_base, bloco in conteudo_raw.items():
        if not isinstance(bloco, dict):
            continue

        if bloco.get("tipo") == "tabular":
            mapeamento = bases_tabulares.get(nome_base, {}).get("mapeamento_colunas", {})
            linhas = _transformar_tabular(bloco.get("records", []), mapeamento)
            tabela_pa = pa.Table.from_pylist(linhas)
            buffer = io.BytesIO()
            pq.write_table(tabela_pa, buffer)
            caminho = (
                Path(diretorio_dados) / "bronze" / f"territorio_{nome_base}"
                / particao / f"territorio_{nome_base}.parquet"
            )
            runner.gravar_atomico(caminho, buffer.getvalue())
            caminhos_gravados[nome_base] = caminho

        elif bloco.get("tipo") == "arquivo":
            formato = bloco.get("formato", "geojson")
            conteudo_bytes = base64.b64decode(bloco["conteudo_base64"])
            caminho = (
                Path(diretorio_dados) / "bronze" / f"territorio_{nome_base}"
                / particao / f"territorio_{nome_base}.{formato}"
            )
            runner.gravar_atomico(caminho, conteudo_bytes)
            caminhos_gravados[nome_base] = caminho

    return caminhos_gravados


def coletar_e_materializar(
    data_coleta: date | None = None,
    diretorio_dados: Path = RAIZ_PROJETO / "data",
    caminho_config: Path | None = None,
) -> dict[str, Any]:
    """Fluxo completo de ponta a ponta: coleta RAW via runner e materializa Bronze."""
    registro = runner.executar("territorio", data_coleta=data_coleta, diretorio_dados=diretorio_dados)

    if registro.get("status") != "ok":
        return {"execucao": registro, "bronze": None}

    data_particao = date.fromisoformat(registro["data_coleta"])
    try:
        caminhos = materializar_bronze(data_particao, diretorio_dados=diretorio_dados, caminho_config=caminho_config)
        return {"execucao": registro, "bronze": {k: str(v) for k, v in caminhos.items()}}
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

    resultado = coletar_e_materializar(data_coleta=opcoes.data_coleta, diretorio_dados=opcoes.diretorio_dados)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado["execucao"].get("status") == "ok" and resultado.get("bronze") else 1


if __name__ == "__main__":
    raise SystemExit(main())
