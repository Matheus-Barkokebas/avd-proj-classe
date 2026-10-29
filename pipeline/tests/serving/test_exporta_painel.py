"""Testes da exportação do painel a partir do pipeline (decisão 0001, etapa F) — sem rede."""

import base64
from datetime import date
import json

import pytest

from src.ingestao import armazenamento as armaz
from src.serving import exporta_painel as ep

DIA = date(2026, 10, 28)


class ResultadoFalso:
    def __init__(self, linhas):
        self.linhas = linhas

    def fetchall(self):
        return self.linhas

    def fetchone(self):
        return self.linhas[0]


class ConexaoNeonFalsa:
    """Responde às consultas do exportador com dados fixos."""

    def __init__(self, dims=None):
        self.dims = dims if dims is not None else [("PINA", "DS VI"), ("SITIO DOS PINTOS", "DS III")]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        if "FROM dim_bairro" in sql:
            return ResultadoFalso(self.dims)
        if "semana_epidemiologica" in sql:
            assert params == ("5",)
            return ResultadoFalso([("dengue", 202501, 3, 2), ("dengue", 202502, 1, 1), ("zika", 202502, 2, 2)])
        if "GROUP BY 1, 2" in sql:
            return ResultadoFalso([("PINA", "dengue", 3), ("Sítio dos Pintos", "zika", 2), ("JABOATAO", "dengue", 1)])
        if "FROM rejeitados" in sql:
            return ResultadoFalso([(19,)])
        raise AssertionError(f"consulta inesperada: {sql}")


class DestinoFalso:
    def __init__(self, conexao):
        self._c = conexao

    def conexao(self):
        return self._c


QUADRADO = [[-34.9, -8.05], [-34.89, -8.05], [-34.89, -8.04], [-34.9, -8.04], [-34.9, -8.05]]
GEOJSON = {"type": "FeatureCollection", "features": [
    {"properties": {"EBAIRRNOMEOF": "Pina", "CRPAAACODI": 6, "DB2GSE.ST_Area(SHAPE)": 2_000_000},
     "geometry": {"type": "Polygon", "coordinates": [QUADRADO]}},
    {"properties": {"EBAIRRNOMEOF": "Sítio dos Pintos - São Brás", "CRPAAACODI": 3, "DB2GSE.ST_Area(SHAPE)": 1_500_000},
     "geometry": {"type": "MultiPolygon", "coordinates": [[QUADRADO]]}},
]}


def _raw_territorio(arm):
    raw = {"bairros_geo": {"tipo": "arquivo", "formato": "geojson",
                           "conteudo_base64": base64.b64encode(json.dumps(GEOJSON).encode()).decode()}}
    arm.gravar("territorio", DIA, "territorio.json", json.dumps(raw).encode())


def test_agrega_series_e_bairros_do_neon():
    epi = ep.agregar_epidemiologia(ConexaoNeonFalsa(), {"PINA": "DS VI", "SITIO DOS PINTOS": "DS III"})
    assert epi["semanas"] == [202501, 202502]
    assert epi["notificacoes"] == {"dengue": [3, 1], "zika": [0, 2]}
    assert epi["nao_descartadas"] == {"dengue": [2, 1], "zika": [0, 2]}
    assert epi["por_bairro"] == {"PINA": {"dengue": 3}, "SITIO DOS PINTOS": {"zika": 2}}
    assert epi["nao_georreferenciadas"] == {"dengue": 1}  # JABOATAO: fora de dim_bairro, mas contado
    assert epi["totais"] == {"dengue": 4, "zika": 2} and epi["rejeitadas_no_contrato"] == 19


def test_malha_usa_apelido_para_ligar_ao_distrito():
    bairros = ep.bairros_da_malha(GEOJSON, {"PINA": "DS VI", "SITIO DOS PINTOS": "DS III"})
    assert [(b["nome"], b["chave"], b["ds"]) for b in bairros] == [
        ("Pina", "PINA", "DS VI"), ("Sítio dos Pintos - São Brás", "SITIO DOS PINTOS", "DS III")]
    assert bairros[0]["area_km2"] == 2.0 and len(bairros[0]["poligonos"][0]) >= 4


def test_exportar_gera_o_js_que_o_console_le(tmp_path):
    arm = armaz.ArmazenamentoArquivo(tmp_path)
    _raw_territorio(arm)
    saida = tmp_path / "recife-real.js"
    r = ep.exportar(DestinoFalso(ConexaoNeonFalsa()), arm, DIA, saida)
    assert r["bairros"] == 2 and r["bairros_sem_distrito"] == [] and r["notificacoes"] == 6
    texto = saida.read_text(encoding="utf-8")
    dados = json.loads(texto[texto.index("window.AERVITA_DADOS = ") + 23:].rstrip().rstrip(";"))
    assert set(dados) == {"bairros", "epidemiologia"}
    assert dados["epidemiologia"]["por_bairro"]["PINA"] == {"dengue": 3}


def test_exportar_sem_dimensoes_explica_o_que_rodar(tmp_path):
    arm = armaz.ArmazenamentoArquivo(tmp_path)
    _raw_territorio(arm)
    with pytest.raises(ValueError, match="dim_bairro vazia"):
        ep.exportar(DestinoFalso(ConexaoNeonFalsa(dims=[])), arm, DIA, tmp_path / "x.js")


def test_exportar_sem_raw_do_territorio(tmp_path):
    with pytest.raises(FileNotFoundError, match="RAW não encontrada"):
        ep.exportar(DestinoFalso(ConexaoNeonFalsa()), armaz.ArmazenamentoArquivo(tmp_path), DIA, tmp_path / "x.js")
