"""Chuva horária do INMET (decisão 0003): arquivos anuais oficiais, sem API.

Do ZIP do ano fica só o CSV da estação configurada: ele vai para a Bronze como
veio, comprimido com gzip, e as leituras validadas vão para a tabela `inmet_chuva`
da Silver. Rodar de novo não duplica.
"""

import argparse
import csv
from datetime import date, datetime, timedelta
import gzip
import io
import json
from pathlib import Path
import re
import sys
from typing import Any
import zipfile

import requests
import yaml

# Executado como script, o Python não põe a raiz do projeto no sys.path (BUG-02).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestao import armazenamento as armaz
from src.ingestao import bronze
from src.ingestao import padronizada

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
CAMINHO_CONFIG = RAIZ_PROJETO / "conf" / "sources" / "inmet.yml"
LINHAS_CABECALHO = 8
HORAS_UTC_RECIFE = 3
SEM_LEITURA = {"", "-9999"}
_FIM_DO_PERIODO = re.compile(r"_A_(\d{2})-(\d{2})-(\d{4})\.CSV$", re.IGNORECASE)


def carregar_configuracao(caminho: Path = CAMINHO_CONFIG) -> dict[str, Any]:
    with caminho.open(encoding="utf-8") as arquivo:
        return yaml.safe_load(arquivo)


def arquivo_da_estacao(nomes: list[str], estacao: str) -> str | None:
    """O ZIP pode trazer vários recortes da mesma estação: fica o que termina mais tarde."""
    candidatos = []
    for nome in nomes:
        achado = _FIM_DO_PERIODO.search(nome)
        if achado and f"_{estacao}_" in nome.upper():
            dia, mes, ano = achado.groups()
            candidatos.append((ano, mes, dia, nome))
    return max(candidatos)[3] if candidatos else None


def _data_hora_local(data_txt: str, hora_txt: str) -> str:
    """Datas vêm como 2026/01/31 ou 2026-01-31 e horas como '0100 UTC' ou '01:00'."""
    digitos = re.sub(r"\D", "", hora_txt)[:4].ljust(4, "0")
    utc = datetime.strptime(data_txt.replace("-", "/") + digitos, "%Y/%m/%d%H%M")
    return (utc - timedelta(hours=HORAS_UTC_RECIFE)).strftime("%Y-%m-%d %H:%M:%S")


def ler_csv(conteudo: bytes, estacao: str) -> list[dict[str, Any]]:
    """CSV da estação -> linhas do contrato. A hora sem leitura continua na lista, com chuva vazia."""
    texto = conteudo.decode("latin-1").splitlines()[LINHAS_CABECALHO:]
    leitor = csv.reader(texto, delimiter=";")
    cabecalho = next(leitor)
    if not cabecalho[2].upper().startswith("PRECIPITA"):
        raise ValueError(f"Coluna de chuva não encontrada no CSV do INMET: {cabecalho[:3]}")
    linhas = []
    for campos in leitor:
        if len(campos) < 3 or not campos[0].strip():
            continue
        valor = campos[2].strip()
        linhas.append({
            "estacao": estacao,
            "data_hora": _data_hora_local(campos[0].strip(), campos[1].strip()),
            "chuva_mm": None if valor in SEM_LEITURA else float(valor.replace(",", ".")),
        })
    return linhas


def carregar(config: dict[str, Any], armazenamento: armaz.ArmazenamentoRaw, destino: padronizada.DestinoNeon,
             data_coleta: date) -> dict[str, Any]:
    lote: list[dict[str, Any]] = []
    arquivos = {}
    for ano in config["anos"]:
        resposta = requests.get(config["url_arquivo"].format(ano=ano), timeout=300)
        resposta.raise_for_status()
        pacote = zipfile.ZipFile(io.BytesIO(resposta.content))
        nome = arquivo_da_estacao(pacote.namelist(), config["estacao"])
        arquivos[str(ano)] = nome
        if nome is None:
            continue
        conteudo = pacote.read(nome)
        armazenamento.gravar(config["nome"], data_coleta, f"{Path(nome).name}.gz", gzip.compress(conteudo, mtime=0))
        lote.extend(ler_csv(conteudo, config["estacao"]))
    contrato, validas, rejeitadas = bronze.separar(lote, "inmet_chuva")
    return {"arquivos": arquivos, "horas": len(lote), "com_leitura": sum(l["chuva_mm"] is not None for l in validas),
            "rejeitadas": len(rejeitadas), "silver": destino.gravar(contrato, config["nome"], data_coleta, validas, rejeitadas)}


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
