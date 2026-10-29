"""API contra o Neon de verdade (usuário só de leitura do api/.env).

Opcional: `pytest -m integracao`. Confere que cada rota responde 200 com dados
reais e no formato declarado — se o pipeline mudar uma tabela, quebra aqui.
"""

import pytest
from fastapi.testclient import TestClient

from app import config as cfg
from app.main import criar_app

pytestmark = pytest.mark.integracao


@pytest.fixture(scope="module")
def cliente():
    try:
        configuracao = cfg.carregar()
    except RuntimeError:
        pytest.skip("NEON_DATABASE_URL não configurada em api/.env")
    with TestClient(criar_app(configuracao)) as c:
        yield c


@pytest.mark.parametrize("rota", [
    "/saude", "/v1/atualizacao", "/v1/chuva/atual", "/v1/chuva/serie?horas=720", "/v1/chuva/mensal",
    "/v1/chuva/previsao", "/v1/rios", "/v1/arboviroses/semanas", "/v1/arboviroses/bairros",
    "/v1/territorio/bairros", "/v1/territorio/distritos", "/v1/territorio/areas-alagaveis",
    "/v1/territorio/pontos-alagamento", "/v1/territorio/bairros-geo",
])
def test_rota_responde_com_dado_real(cliente, rota):
    r = cliente.get(rota)
    assert r.status_code == 200, r.text


def test_numeros_batem_com_o_pipeline(cliente):
    bairros = cliente.get("/v1/arboviroses/bairros").json()
    total = sum(b["total"] for b in bairros["bairros"]) + bairros["nao_georreferenciadas"]
    assert total == 11931  # notificações válidas carregadas pelo pipeline
    assert len(bairros["bairros"]) == 94
    assert len(cliente.get("/v1/territorio/distritos").json()) == 8
    assert len(cliente.get("/v1/rios").json()) == 5
    assert len(cliente.get("/v1/territorio/bairros-geo").json()["features"]) == 94


def test_api_nao_consegue_escrever(cliente):
    repo = cliente.app.state.repositorio
    with pytest.raises(Exception):
        repo.banco.consultar("DELETE FROM dim_distrito WHERE false")
