"""Regras puras da API."""

from datetime import datetime
from pathlib import Path

import pytest

from app.servicos import regras


@pytest.mark.parametrize("nivel, esperado", [
    (100, "normal"), (320, "pre_alerta"), (339.9, "pre_alerta"), (340, "alerta"), (440, "inundacao"), (None, "sem_cota"),
])
def test_situacao_rio_contra_as_cotas(nivel, esperado):
    assert regras.situacao_rio(nivel, 320, 340, 440) == esperado


def test_situacao_rio_sem_cotas():
    assert regras.situacao_rio(100, None, None, None) == "sem_cota"
    assert regras.situacao_rio(500, None, 340, None) == "alerta"


def test_comparacao_mensal_usa_o_mes_da_leitura():
    meses = [{"ano_referencia": 2026, "mes": 10, "chuva_ano_atual_mm": 12.1, "media_historica_mm": 35.0}]
    assert regras.comparacao_mensal(meses, datetime(2026, 10, 28))["percentual_da_media"] == 34.6
    assert regras.comparacao_mensal(meses, datetime(2026, 11, 1)) is None


def test_media_dos_modelos_ignora_nulos():
    assert regras.media_modelos(1.0, None, 2.0, None) == 1.5
    assert regras.media_modelos(None, None) is None


def test_percentual_sem_divisao_por_zero():
    assert regras.percentual(10, 0) is None and regras.percentual(None, 10) is None


@pytest.mark.parametrize("nome, chave", [
    ("Água Fria", "AGUA FRIA"), ("  alto  do mandu ", "ALTO DO MANDU"),
    ("Sítio dos Pintos - São Brás", "SITIO DOS PINTOS"), ("Cohab - Ibura de Cima", "COHAB"), (None, ""),
])
def test_chave_bairro(nome, chave):
    assert regras.chave_bairro(nome) == chave


def test_chave_bairro_igual_a_do_pipeline():
    """A API não importa o pipeline; este teste garante que as duas normalizações não divergem."""
    arquivo = Path(__file__).resolve().parents[2] / "pipeline" / "src" / "ingestao" / "territorio.py"
    if not arquivo.is_file():
        pytest.skip("pipeline/ não está ao lado da api/")
    codigo = arquivo.read_text(encoding="utf-8")
    inicio = codigo.index("def chave_bairro")
    fim = codigo.index("\n\n\n", inicio)
    ns = {"Any": object, "unicodedata": __import__("unicodedata")}
    exec(codigo[inicio:fim], ns)
    for nome in ("Água Fria", "  alto  do mandu ", "Cohab", "BOA VIAGEM", "Jiquiá"):
        assert regras.chave_bairro(nome) == ns["chave_bairro"](nome)
