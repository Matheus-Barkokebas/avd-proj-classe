"""Carga do histórico de arboviroses, 2013 a 2024 (decisão 0003).

Cada recurso do portal vai para a Bronze (Atlas) como veio, comprimido com gzip
para caber no plano gratuito, e as linhas validadas pelo contrato de epidemiologia
vão para a tabela `epidemiologia_historico` da Silver. Rodar de novo não duplica.
Dengue de 2015 e 2019 só existem em CSV; os demais vêm do DataStore.
"""

import argparse
import csv
from datetime import date
import gzip
import io
import json
from pathlib import Path
import re
import sys
from typing import Any

import requests
import yaml

# Executado como script, o Python não põe a raiz do projeto no sys.path (BUG-02).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestao import armazenamento as armaz
from src.ingestao import bronze
from src.ingestao import comum
from src.ingestao import padronizada
from src.ingestao import recife_ckan
from src.processamento import gold

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
CAMINHO_CONFIG = RAIZ_PROJETO / "conf" / "sources" / "epidemiologia_historico.yml"
URL_PACOTE = "https://dados.recife.pe.gov.br/api/3/action/package_show"
_TITULO_CASOS = re.compile(r"^Casos .*?(\d{4})\s*$")


def carregar_configuracao(caminho: Path = CAMINHO_CONFIG) -> dict[str, Any]:
    with caminho.open(encoding="utf-8") as arquivo:
        return yaml.safe_load(arquivo)


def recursos_historicos(recursos: list[dict[str, Any]], ano_maximo: int) -> list[dict[str, Any]]:
    """Recursos de casos até `ano_maximo`, sem os metadados e as tabelas auxiliares do pacote."""
    selecionados = []
    for recurso in recursos:
        achado = _TITULO_CASOS.match((recurso.get("name") or "").strip())
        if achado and int(achado.group(1)) <= ano_maximo:
            selecionados.append({**recurso, "ano": int(achado.group(1))})
    return sorted(selecionados, key=lambda r: (r["ano"], r["name"]))


def agravo_do_cid(cid: Any, cid_agravo: dict[str, str]) -> str | None:
    return cid_agravo.get(re.sub(r"[^A-Z0-9]", "", str(cid or "").upper()))


def _classificacao(valor: Any) -> str | None:
    """Código como texto, igual à Silver corrente: o CSV pode trazer 5.0 onde o DataStore traz 5."""
    numero = comum.para_int(valor)
    return str(numero) if isinstance(numero, int) else comum.para_texto(valor)


def padronizar(registro: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Uma linha da fonte, em qualquer layout, nos campos do contrato. CID desconhecido deixa o agravo vazio."""
    linha = {str(chave).lower(): valor for chave, valor in registro.items()}
    campos = next((l["campos"] for l in config["layouts"] if l["identificador"] in linha), None)
    if campos is None:
        raise ValueError(f"Layout desconhecido: {sorted(linha)[:8]}")
    return {
        "protocolo": comum.para_texto(linha.get(campos["protocolo"])),
        "data_notificacao": comum.normalizar_timestamp(linha.get(campos["data_notificacao"])),
        "semana_epidemiologica": comum.para_int(linha.get(campos["semana_epidemiologica"])),
        "ano": comum.para_int(linha.get(campos["ano"])),
        "bairro": comum.para_texto(linha.get(campos["bairro"])),
        "agravo": agravo_do_cid(linha.get(campos["cid"]), config["cid_agravo"]),
        "classificacao_final": _classificacao(linha.get(campos["classificacao_final"])),
        "contagem": 1,
    }


def ler_csv(conteudo: bytes) -> list[dict[str, Any]]:
    return list(csv.DictReader(io.StringIO(conteudo.decode("utf-8-sig"))))


def _baixar(recurso: dict[str, Any]) -> list[dict[str, Any]]:
    if recurso.get("datastore_active"):
        return recife_ckan.coletar_todos(recurso["id"])[0]
    resposta = requests.get(recurso["url"], timeout=120)
    resposta.raise_for_status()
    return ler_csv(resposta.content)


def carregar(config: dict[str, Any], armazenamento: armaz.ArmazenamentoRaw, destino: padronizada.DestinoNeon,
             data_coleta: date) -> dict[str, Any]:
    resposta = requests.get(URL_PACOTE, params={"id": config["pacote"]}, timeout=60)
    resposta.raise_for_status()
    recursos = recursos_historicos(resposta.json()["result"]["resources"], config["ano_maximo"])

    lote: list[dict[str, Any]] = []
    por_recurso = {}
    for recurso in recursos:
        registros = _baixar(recurso)
        bruto = gzip.compress(json.dumps(registros, ensure_ascii=False).encode("utf-8"), mtime=0)
        armazenamento.gravar(config["nome"], data_coleta, f"{recurso['id']}.json.gz", bruto)
        lote.extend(padronizar(r, config) for r in registros)
        por_recurso[recurso["name"].strip()] = len(registros)
        print(f"{recurso['name'].strip()}: {len(registros)} linhas, {len(bruto) / 1e6:.1f} MB na Bronze", flush=True)

    contrato, validas, rejeitadas = bronze.separar(lote, "epidemiologia")
    gravacao = destino.gravar({**contrato, "tabela": config["tabela"]}, config["nome"], data_coleta, validas, rejeitadas)
    return {"recursos": por_recurso, "linhas": len(lote), "validas": len(validas), "rejeitadas": len(rejeitadas),
            "silver": gravacao, "gold": gold.construir(destino, gold.carregar_configuracao())}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=date.fromisoformat, default=date.today(), dest="data_coleta")
    opcoes = parser.parse_args()
    resultado = carregar(carregar_configuracao(), armaz.criar("mongo", RAIZ_PROJETO / "data"),
                         padronizada.DestinoNeon.do_ambiente(), opcoes.data_coleta)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
