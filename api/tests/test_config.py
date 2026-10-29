"""Configuração da API lida do ambiente."""

import pytest

from app import config


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch, tmp_path):
    for nome in ("NEON_DATABASE_URL", "API_ORIGENS_CORS", "API_CACHE_SEGUNDOS"):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv("NEON_DATABASE_URL", "postgresql://u:s@h/db")
    return tmp_path / "sem.env"  # .env inexistente: não lê o real do desenvolvedor


def test_sem_variavel_de_cors_libera_o_front_local(ambiente_limpo):
    assert config.carregar(ambiente_limpo).origens_cors == ("http://localhost:5173",)


def test_cors_vazio_desliga_todas_as_origens(ambiente_limpo, monkeypatch):
    monkeypatch.setenv("API_ORIGENS_CORS", "")
    assert config.carregar(ambiente_limpo).origens_cors == ()


def test_varias_origens_separadas_por_virgula(ambiente_limpo, monkeypatch):
    monkeypatch.setenv("API_ORIGENS_CORS", "https://painel.exemplo, http://localhost:5173")
    assert config.carregar(ambiente_limpo).origens_cors == ("https://painel.exemplo", "http://localhost:5173")


def test_sem_url_do_banco_falha_com_mensagem_clara(ambiente_limpo, monkeypatch):
    monkeypatch.delenv("NEON_DATABASE_URL")
    with pytest.raises(RuntimeError, match="NEON_DATABASE_URL"):
        config.carregar(ambiente_limpo)


def test_mascarar_esconde_a_senha():
    assert config.mascarar("postgresql://aervita_api:segredo@host/db") == "postgresql://aervita_api:***@host/db"
