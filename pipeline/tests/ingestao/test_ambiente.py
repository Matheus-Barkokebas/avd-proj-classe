"""Testes da leitura de variáveis de ambiente (decisão 0001)."""

import pytest

from src.ingestao import ambiente


@pytest.fixture(autouse=True)
def sem_env_real(monkeypatch, tmp_path):
    # isola os testes do .env real do desenvolvedor
    monkeypatch.setattr(ambiente, "RAIZ_PROJETO", tmp_path)
    for nome in ("MONGODB_URI", "MONGODB_DB"):
        monkeypatch.delenv(nome, raising=False)


def test_obrigatoria_ausente_falha_com_mensagem_clara():
    with pytest.raises(RuntimeError, match="MONGODB_URI"):
        ambiente.obrigatoria("MONGODB_URI")


def test_le_do_arquivo_env(tmp_path):
    (tmp_path / ".env").write_text("# comentário\nMONGODB_URI=mongodb+srv://u:s@h.net/\nMONGODB_DB=teste\n", encoding="utf-8")
    assert ambiente.config_mongo() == {"uri": "mongodb+srv://u:s@h.net/", "banco": "teste"}


def test_variavel_do_sistema_tem_prioridade_sobre_env(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("MONGODB_URI=do-arquivo\n", encoding="utf-8")
    monkeypatch.setenv("MONGODB_URI", "do-sistema")
    assert ambiente.obrigatoria("MONGODB_URI") == "do-sistema"


def test_banco_padrao_quando_nao_definido(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb+srv://u:s@h.net/")
    assert ambiente.config_mongo()["banco"] == "aervita"


def test_mascarar_esconde_senha():
    assert ambiente.mascarar("mongodb+srv://barko:segredo@cluster.net/") == "mongodb+srv://barko:***@cluster.net/"
