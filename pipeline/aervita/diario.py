"""Execução diária: coleta as fontes, recalcula a Gold e registra o resultado.

Cada etapa roda em processo separado: uma falha não impede as seguintes, e a Gold
é recalculada com o que tiver chegado. O resultado fica em gold.execucao_pipeline.
O COP fica fora por padrão (os serviços exigem login desde nov/2026); use --com-cop.
"""

import argparse
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
import time

from aervita import ambiente

DESTINO = ["--armazenamento", "mongo", "--padronizada", "neon"]
ETAPAS = [
    ("territorio", ["territorio", *DESTINO]),
    ("arboviroses", ["arboviroses", *DESTINO]),
    ("cop_recife", ["cop", *DESTINO]),
    ("inmet", ["inmet"]),
    ("gold", ["gold"]),
]
LIMITE_SAIDA = 4000

TABELA = """
CREATE TABLE IF NOT EXISTS gold.execucao_pipeline (
    id bigserial PRIMARY KEY,
    inicio timestamptz NOT NULL,
    fim timestamptz NOT NULL,
    status text NOT NULL,
    etapas jsonb NOT NULL,
    origem text NOT NULL
)
"""


def rodar_etapa(nome: str, argumentos: list[str]) -> dict:
    inicio = time.monotonic()
    processo = subprocess.run([sys.executable, "-m", "aervita", *argumentos], cwd=ambiente.RAIZ_PROJETO, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    saida = (processo.stdout + processo.stderr).strip()
    print(f"=== {nome}: código {processo.returncode}\n{saida}", flush=True)
    return {"etapa": nome, "ok": processo.returncode == 0, "codigo": processo.returncode,
            "segundos": round(time.monotonic() - inicio, 1), "saida": saida[-LIMITE_SAIDA:]}


def registrar(inicio: datetime, fim: datetime, etapas: list[dict], origem: str) -> None:
    import psycopg

    status = "ok" if all(e["ok"] for e in etapas) else "falhou" if not any(e["ok"] for e in etapas) else "parcial"
    with psycopg.connect(ambiente.obrigatoria("NEON_DATABASE_URL")) as conexao, conexao.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS gold")
        cur.execute(TABELA)
        cur.execute("INSERT INTO gold.execucao_pipeline (inicio, fim, status, etapas, origem) VALUES (%s, %s, %s, %s, %s)",
                    (inicio, fim, status, json.dumps(etapas, ensure_ascii=False), origem))
    print(f"=== registrado: {status}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aervita diario", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--com-cop", action="store_true", help="inclui o COP Recife (exige acesso liberado e IP do Brasil)")
    parser.add_argument("--origem", default=ambiente.opcional("ORIGEM_EXECUCAO", "manual"),
                        help="quem disparou: agendamento, manual... (padrão: variável ORIGEM_EXECUCAO)")
    args = parser.parse_args(argv)

    etapas = [e for e in ETAPAS if args.com_cop or e[0] != "cop_recife"]
    inicio = datetime.now(timezone.utc)
    resultados = [rodar_etapa(nome, argumentos) for nome, argumentos in etapas]
    registrar(inicio, datetime.now(timezone.utc), resultados, args.origem)
    return 0 if all(r["ok"] for r in resultados) else 1
