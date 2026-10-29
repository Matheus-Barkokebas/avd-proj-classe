"""Camada padronizada no Neon de verdade (decisão 0001).

Opcional: roda só com `pytest -m integracao` e com NEON_DATABASE_URL no
ambiente ou no .env. Trabalha no schema `aervita_teste`, criado e apagado
pelo próprio teste — nunca toca nas tabelas da aplicação.
"""

from datetime import date

import pytest

from src.ingestao import ambiente
from src.ingestao import bronze
from src.ingestao import padronizada

pytestmark = pytest.mark.integracao
SCHEMA = "aervita_teste"


@pytest.fixture
def destino():
    psycopg = pytest.importorskip("psycopg")
    try:
        url = ambiente.obrigatoria("NEON_DATABASE_URL")
    except RuntimeError:
        pytest.skip("NEON_DATABASE_URL não configurada")

    def conectar():
        conexao = psycopg.connect(url, connect_timeout=20)
        conexao.execute(f"SET search_path TO {SCHEMA}")
        return conexao

    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        admin.execute(f"CREATE SCHEMA {SCHEMA}")
    yield padronizada.DestinoNeon(conectar), conectar
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")


def _linha(protocolo, bairro="PINA"):
    return {"protocolo": protocolo, "data_notificacao": "2025-04-03 00:00:00", "semana_epidemiologica": 202514,
            "ano": 2025, "bairro": bairro, "agravo": "dengue", "classificacao_final": "10", "contagem": 1}


def test_carga_no_neon_e_idempotente_com_quarentena(destino):
    neon, conectar = destino
    dia = date(2026, 1, 1)
    lote = [_linha("1"), _linha("2"), _linha("3", bairro="")]
    for _ in range(2):  # rodar duas vezes não duplica nada
        resumo = bronze.gravar_validado(lote, "epidemiologia", "epidemiologia", dia, None, destino=neon)
    assert resumo == "neon:epidemiologia (2 válidas enviadas, 1 rejeitadas)"
    with conectar() as c:
        assert c.execute("SELECT count(*) FROM epidemiologia").fetchone()[0] == 2
        assert c.execute("SELECT count(*) FROM rejeitados").fetchone()[0] == 1
        tipo = c.execute("SELECT pg_typeof(data_notificacao)::text FROM epidemiologia LIMIT 1").fetchone()[0]
    assert tipo == "timestamp without time zone"
    assert neon.contar_rejeitados("epidemiologia", dia) == 1
