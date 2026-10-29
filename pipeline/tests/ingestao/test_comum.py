"""Testes da tipagem compartilhada (src/ingestao/comum.py) — BUG-03."""

from datetime import datetime

import pytest

from src.ingestao import comum


@pytest.mark.parametrize("entrada,esperado", [
    ("2025-04-03T00:00:00", "2025-04-03 00:00:00"),      # dengue (ISO)
    ("08/01/2025", "2025-01-08 00:00:00"),               # zika/chikungunya (DD/MM/AAAA)
    ("08/01/2025 00:00:00", "2025-01-08 00:00:00"),
    ("23/01/2025 14:05", "2025-01-23 14:05:00"),
    ("2025-04-03", "2025-04-03 00:00:00"),
    ("2026-09-24 10:00:00", "2026-09-24 10:00:00"),
    ("2026-09-24T10:00:00.000", "2026-09-24 10:00:00"),
    ("2026-09-24T10:00:00-03:00", "2026-09-24 10:00:00"),
    (datetime(2026, 9, 24, 8, 50), "2026-09-24 08:50:00"),
])
def test_normalizar_timestamp_formatos_conhecidos(entrada, esperado):
    assert comum.normalizar_timestamp(entrada) == esperado


def test_dia_e_mes_nao_sao_invertidos():
    # 01/02 é 1º de fevereiro (padrão brasileiro), nunca 2 de janeiro
    assert comum.normalizar_timestamp("01/02/2025") == "2025-02-01 00:00:00"


@pytest.mark.parametrize("vazio", [None, "", "   "])
def test_normalizar_timestamp_vazio_vira_none(vazio):
    assert comum.normalizar_timestamp(vazio) is None


def test_formato_desconhecido_volta_intacto_para_o_contrato_acusar():
    assert comum.normalizar_timestamp("ontem") == "ontem"
    assert comum.normalizar_timestamp("31/02/2025") == "31/02/2025"  # data inexistente


@pytest.mark.parametrize("entrada,esperado", [
    ("202502", 202502), (202510, 202510), (2025.0, 2025), (" 7 ", 7),
    ("", None), (None, None), ("abc", "abc"), (2.5, 2.5),
])
def test_para_int(entrada, esperado):
    assert comum.para_int(entrada) == esperado


@pytest.mark.parametrize("entrada,esperado", [
    (3059, "3059"), (3059.0, "3059"), (" PINA ", "PINA"), ("", None), ("  ", None), (None, None),
])
def test_para_texto(entrada, esperado):
    assert comum.para_texto(entrada) == esperado
