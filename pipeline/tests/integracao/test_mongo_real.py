"""RAW no MongoDB Atlas de verdade (decisão 0001).

Opcional: roda só com `pytest -m integracao` e com MONGODB_URI no ambiente
ou no .env. Usa o banco `aervita_teste` e apaga tudo ao final — nunca toca
no banco da aplicação.
"""

from datetime import date

import pytest

from src.ingestao import ambiente
from src.ingestao import armazenamento as armaz
from src.ingestao import runner

pytestmark = pytest.mark.integracao


@pytest.fixture
def banco_teste():
    pymongo = pytest.importorskip("pymongo")
    try:
        uri = ambiente.obrigatoria("MONGODB_URI")
    except RuntimeError:
        pytest.skip("MONGODB_URI não configurada")
    cliente = pymongo.MongoClient(uri, serverSelectionTimeoutMS=15000)
    cliente.drop_database("aervita_teste")
    yield cliente["aervita_teste"]
    cliente.drop_database("aervita_teste")
    cliente.close()


def test_raw_no_atlas_e_idempotente(banco_teste):
    m = armaz.ArmazenamentoMongo(banco_teste)
    dia = date(2026, 1, 1)
    assert m.gravar("teste", dia, "x.json", b'{"ok": true}') is True
    assert m.gravar("teste", dia, "x.json", b'{"ok": true}') is False
    assert m.ler("teste", dia, "x.json") == b'{"ok": true}'
    assert banco_teste["raw_coletas"].count_documents({}) == 1
    assert banco_teste["raw_conteudo.files"].count_documents({}) == 1


def test_runner_completo_no_atlas(banco_teste):
    m = armaz.ArmazenamentoMongo(banco_teste)
    registro = runner.executar("dummy", armazenamento=m)
    assert registro["status"] == "ok"
    assert banco_teste["execucoes"].count_documents({"_id": registro["id"]}) == 1
