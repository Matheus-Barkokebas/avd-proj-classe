"""Rotas da API com repositório falso: formato das respostas, erros, cache e CORS."""

from fastapi.testclient import TestClient

from app.main import criar_app
from tests.conftest import CONFIG, BancoFalso, RepositorioFalso


def test_saude_ok(cliente):
    r = cliente.get("/saude")
    assert r.status_code == 200 and r.json() == {"status": "ok", "banco": "ok"}


def test_saude_com_banco_fora_responde_503():
    with TestClient(criar_app(CONFIG, RepositorioFalso(BancoFalso(falhar=True))), raise_server_exceptions=False) as c:
        r = c.get("/saude")
    assert r.status_code == 503 and r.json()["banco"] == "indisponivel"


def test_chuva_atual_com_comparacao_do_mes(cliente):
    r = cliente.get("/v1/chuva/atual")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["chuva_media_24h_mm"] == 6.2 and corpo["estacao_max_24h"] == "Areias"
    assert corpo["data_hora"] == "2026-10-28T21:00:45-03:00"  # sempre com o fuso do Recife
    assert corpo["mes"] == {"mes": 10, "ano": 2026, "chuva_acumulada_mm": 12.1, "media_historica_mm": 35.0,
                            "percentual_da_media": 34.6}
    assert "data_coleta" not in corpo  # coluna de controle não vaza para o front


def test_chuva_atual_sem_dados_e_404_no_formato_padrao():
    with TestClient(criar_app(CONFIG, RepositorioFalso(vazio=True))) as c:
        r = c.get("/v1/chuva/atual")
    assert r.status_code == 404
    assert r.json() == {"erro": "nao_encontrado", "detalhe": "Ainda não há leituras de chuva no banco"}


def test_serie_respeita_a_janela_pedida(cliente, repo):
    r = cliente.get("/v1/chuva/serie?horas=48")
    assert r.status_code == 200 and len(r.json()) == 2
    _, desde = repo.chamadas[-1]
    assert 47.9 < (desde.now(desde.tzinfo) - desde).total_seconds() / 3600 < 48.1


def test_parametro_invalido_vira_422_no_formato_padrao(cliente):
    r = cliente.get("/v1/chuva/serie?horas=0")
    assert r.status_code == 422
    assert r.json()["erro"] == "parametro_invalido" and "horas" in r.json()["detalhe"]


def test_previsao_traz_media_dos_modelos_com_valor(cliente):
    hora = cliente.get("/v1/chuva/previsao").json()[0]
    assert (hora["gfs_mm"], hora["icon_mm"], hora["media_modelos_mm"]) == (0.4, None, 0.5)


def test_chuva_mensal(cliente):
    corpo = cliente.get("/v1/chuva/mensal").json()
    assert corpo["ano"] == 2026 and [m["mes"] for m in corpo["meses"]] == [9, 10]


def test_rios_com_situacao_calculada_e_mais_grave_primeiro(cliente):
    rios = cliente.get("/v1/rios").json()
    assert [r["estacao"] for r in rios] == ["VILA NATAL", "LIMOEIRO"]
    assert rios[0]["situacao"] == "alerta" and rios[0]["situacao_fonte"] == "Normal"
    assert rios[1]["situacao"] == "normal" and rios[1]["percentual_da_cota_alerta"] == 27.2


def test_serie_de_estacao_inexistente_e_404(cliente):
    assert cliente.get("/v1/rios/999/serie").status_code == 404
    assert cliente.get("/v1/rios/39145010/serie").status_code == 200


def test_arboviroses_por_semana_com_filtro(cliente):
    assert len(cliente.get("/v1/arboviroses/semanas").json()) == 2
    assert [l["agravo"] for l in cliente.get("/v1/arboviroses/semanas?agravo=zika").json()] == ["zika"]
    assert cliente.get("/v1/arboviroses/semanas?agravo=gripe").status_code == 422


def test_arboviroses_por_bairro_nao_descarta_o_que_nao_casa(cliente):
    corpo = cliente.get("/v1/arboviroses/bairros").json()
    pina = corpo["bairros"][0]
    assert (pina["nome_bairro"], pina["dengue"], pina["zika"], pina["total"]) == ("Pina", 30, 2, 32)
    assert corpo["bairros"][1]["nome_bairro"] == "Torre" and corpo["bairros"][1]["total"] == 0
    assert corpo["nao_georreferenciadas"] == 1 and corpo["grafias_nao_reconhecidas"] == ["JIQU]"]


def test_territorio(cliente, repo):
    assert cliente.get("/v1/territorio/bairros").json()[0]["descricao_distrito"] == "DS VI"
    assert cliente.get("/v1/territorio/distritos").json()[0]["bairros"] == 5
    areas = cliente.get("/v1/territorio/areas-alagaveis?distrito=8").json()
    assert areas["type"] == "FeatureCollection" and areas["features"][0]["geometry"]["type"] == "Polygon"
    assert ("areas_alagaveis", 8) in repo.chamadas
    assert cliente.get("/v1/territorio/areas-alagaveis?distrito=9").status_code == 422
    ponto = cliente.get("/v1/territorio/pontos-alagamento").json()["features"][0]
    assert ponto["geometry"] == {"type": "Point", "coordinates": [-34.897, -8.0714]}
    assert ponto["properties"]["inicio_intervencao"] == "2015-12-01" and "longitude" not in ponto["properties"]


def test_bairros_geo_em_geojson_com_distrito(cliente):
    corpo = cliente.get("/v1/territorio/bairros-geo").json()
    feicao = corpo["features"][0]
    assert feicao["geometry"]["type"] == "MultiPolygon"
    assert feicao["properties"] == {"chave_bairro": "PINA", "nome_bairro": "Pina", "rpa": 6, "distrito_sanitario": 6,
                                    "descricao_distrito": "DS VI", "area_km2": 2.0}


def test_atualizacao(cliente):
    corpo = cliente.get("/v1/atualizacao").json()
    assert corpo["tabelas"][0] == {"tabela": "cop_indicadores", "carregado_em": "2026-10-28T21:05:00Z", "linhas": 27}


def test_cache_so_nas_rotas_de_dados(cliente):
    assert cliente.get("/v1/rios").headers["cache-control"] == "public, max-age=300"
    assert "cache-control" not in cliente.get("/saude").headers
    assert "cache-control" not in cliente.get("/v1/rios/999/serie").headers  # erro não vai para o cache


def test_cors_libera_so_a_origem_configurada(cliente):
    liberada = cliente.get("/v1/rios", headers={"Origin": "http://localhost:5173"})
    assert liberada.headers["access-control-allow-origin"] == "http://localhost:5173"
    outra = cliente.get("/v1/rios", headers={"Origin": "https://site-qualquer.com"})
    assert "access-control-allow-origin" not in outra.headers


def test_erro_inesperado_nao_vaza_detalhe_interno():
    class Quebrado(RepositorioFalso):
        def bairros(self):
            raise ValueError("senha=xyz no traceback")

    with TestClient(criar_app(CONFIG, Quebrado()), raise_server_exceptions=False) as c:
        r = c.get("/v1/territorio/bairros")
    assert r.status_code == 500 and r.json() == {"erro": "erro_interno", "detalhe": None}


def test_openapi_documenta_as_rotas(cliente):
    caminhos = cliente.get("/openapi.json").json()["paths"]
    for rota in ("/v1/chuva/atual", "/v1/rios", "/v1/arboviroses/bairros", "/v1/territorio/areas-alagaveis"):
        assert rota in caminhos


def test_raiz_leva_para_a_documentacao(cliente):
    r = cliente.get("/", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/docs"


def test_openapi_versionado_esta_em_dia():
    """api/openapi.json é o contrato com o front: regenerar com `python -m app.openapi`."""
    from app import openapi

    assert openapi.ARQUIVO.read_text(encoding="utf-8") == openapi.gerar(), \
        "openapi.json desatualizado — rode `python -m app.openapi` dentro de api/"


def test_rota_inexistente_tambem_usa_o_formato_padrao(cliente):
    r = cliente.get("/v1/nao-existe")
    assert r.status_code == 404
    assert r.json() == {"erro": "nao_encontrado", "detalhe": "Not Found"}
    assert cliente.post("/v1/rios").json()["erro"] == "metodo_nao_permitido"
