"""Testes automatizados para a coleta de bases territoriais (ING-05).

Sem chamadas à rede; respostas CKAN e download de arquivo são mockados.
"""

from datetime import date
import base64
import json
from pathlib import Path
from unittest.mock import Mock, patch
import pyarrow.parquet as pq
import pytest
import yaml

from src.ingestao import territorio
from src.ingestao import runner


FIXTURE_BAIRROS_RPA = [
    {"_id": 1, "Bairro": "Aflitos", "rpa": 3},
    {"_id": 2, "Bairro": "Afogados", "rpa": 5},
]

FIXTURE_DISTRITOS = [
    {"_id": 1, "bairro": "Boa Vista", "distrito_sanitario": "Distrito Sanitário 1", "descricao_distrito": "DS I"},
    {"_id": 2, "bairro": "Afogados", "distrito_sanitario": "Distrito Sanitário 5", "descricao_distrito": "DS V"},
]

FIXTURE_GEOJSON = b'{"type": "FeatureCollection", "features": []}'


def _config_teste(tmp_path: Path) -> Path:
    config = {
        "nome": "territorio",
        "bases_tabulares": {
            "bairros_rpa": {
                "resource_id": "a378d50a-teste",
                "mapeamento_colunas": {"Bairro": "nome_bairro", "rpa": "rpa"},
            },
            "distritos_sanitarios": {
                "resource_id": "d8d649d6-teste",
                "mapeamento_colunas": {
                    "bairro": "nome_bairro",
                    "distrito_sanitario": "distrito_sanitario",
                    "descricao_distrito": "descricao_distrito",
                },
            },
        },
        "bases_geometricas": {
            "bairros_geo": {"url": "https://exemplo.invalido/bairros.geojson", "formato": "geojson"},
        },
    }
    caminho = tmp_path / "territorio.yml"
    caminho.write_text(yaml.dump(config, allow_unicode=True), encoding="utf-8")
    return caminho


@pytest.fixture
def mock_ckan():
    def _mock(resource_id, *args, **kwargs):
        if "a378d50a" in resource_id:
            return FIXTURE_BAIRROS_RPA, {"total": len(FIXTURE_BAIRROS_RPA)}
        if "d8d649d6" in resource_id:
            return FIXTURE_DISTRITOS, {"total": len(FIXTURE_DISTRITOS)}
        return [], {"total": 0}

    return _mock


@pytest.fixture
def mock_download():
    resp = Mock()
    resp.content = FIXTURE_GEOJSON
    resp.raise_for_status.return_value = None
    return Mock(return_value=resp)


def test_coletar_dados_combina_tabulares_e_geometricas(tmp_path, mock_ckan, mock_download):
    caminho_config = _config_teste(tmp_path)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan), \
         patch("src.ingestao.territorio.requests.get", mock_download):
        conteudo = territorio.coletar_dados(date(2026, 9, 24), caminho_config=caminho_config)

    payload = json.loads(conteudo)
    assert payload["bairros_rpa"]["tipo"] == "tabular"
    assert len(payload["bairros_rpa"]["records"]) == 2
    assert payload["distritos_sanitarios"]["tipo"] == "tabular"
    assert len(payload["distritos_sanitarios"]["records"]) == 2
    assert payload["bairros_geo"]["tipo"] == "arquivo"
    assert base64.b64decode(payload["bairros_geo"]["conteudo_base64"]) == FIXTURE_GEOJSON

    total = territorio.contar_registros(conteudo)
    assert total == 2 + 2 + 1  # 2 bairros_rpa + 2 distritos + 1 arquivo geométrico


def test_runner_executa_territorio_e_grava_raw(tmp_path, mock_ckan, mock_download):
    caminho_config = _config_teste(tmp_path)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan), \
         patch("src.ingestao.territorio.requests.get", mock_download), \
         patch("src.ingestao.territorio.CAMINHO_CONFIG_PADRAO", caminho_config):
        registro = runner.executar("territorio", data_coleta=date(2026, 9, 24), diretorio_dados=tmp_path)

    assert registro["status"] == "ok"
    caminho_raw = tmp_path / "raw" / "territorio" / "2026" / "09" / "24" / "territorio.json"
    assert caminho_raw.is_file()


def test_transformar_tabular_bairros_rpa():
    mapeamento = {"Bairro": "nome_bairro", "rpa": "rpa"}
    linhas = territorio._transformar_tabular(FIXTURE_BAIRROS_RPA, mapeamento)
    assert linhas[0] == {"nome_bairro": "Aflitos", "rpa": 3}
    assert linhas[1] == {"nome_bairro": "Afogados", "rpa": 5}


def test_transformar_tabular_extrai_numero_distrito_sanitario():
    mapeamento = {"bairro": "nome_bairro", "distrito_sanitario": "distrito_sanitario", "descricao_distrito": "descricao_distrito"}
    linhas = territorio._transformar_tabular(FIXTURE_DISTRITOS, mapeamento)
    assert linhas[0]["distrito_sanitario"] == 1
    assert linhas[1]["distrito_sanitario"] == 5
    assert linhas[0]["descricao_distrito"] == "DS I"


def test_materializar_bronze_gera_parquet_para_bases_tabulares(tmp_path, mock_ckan, mock_download):
    caminho_config = _config_teste(tmp_path)
    data_coleta = date(2026, 9, 24)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan), \
         patch("src.ingestao.territorio.requests.get", mock_download):
        runner.executar("territorio", data_coleta=data_coleta, diretorio_dados=tmp_path)

    caminhos = territorio.materializar_bronze(data_coleta, diretorio_dados=tmp_path, caminho_config=caminho_config)

    caminho_bairros = caminhos["bairros_rpa"]
    assert caminho_bairros.is_file()
    assert caminho_bairros.name == "territorio_bairros_rpa.parquet"
    tabela = pq.read_table(caminho_bairros)
    assert tabela.num_rows == 2
    assert set(tabela.column_names) == {"nome_bairro", "rpa"}

    caminho_distritos = caminhos["distritos_sanitarios"]
    tabela_ds = pq.read_table(caminho_distritos)
    assert tabela_ds.num_rows == 2
    assert set(tabela_ds["distrito_sanitario"].to_pylist()) == {1, 5}


def test_materializar_bronze_preserva_geojson_para_base_geometrica(tmp_path, mock_ckan, mock_download):
    caminho_config = _config_teste(tmp_path)
    data_coleta = date(2026, 9, 24)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan), \
         patch("src.ingestao.territorio.requests.get", mock_download):
        runner.executar("territorio", data_coleta=data_coleta, diretorio_dados=tmp_path)

    caminhos = territorio.materializar_bronze(data_coleta, diretorio_dados=tmp_path, caminho_config=caminho_config)

    caminho_geo = caminhos["bairros_geo"]
    assert caminho_geo.is_file()
    assert caminho_geo.name == "territorio_bairros_geo.geojson"
    assert caminho_geo.read_bytes() == FIXTURE_GEOJSON  # preservado byte a byte, sem conversão


def test_idempotencia_materializacao_bronze(tmp_path, mock_ckan, mock_download):
    caminho_config = _config_teste(tmp_path)
    data_coleta = date(2026, 9, 24)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan), \
         patch("src.ingestao.territorio.requests.get", mock_download):
        runner.executar("territorio", data_coleta=data_coleta, diretorio_dados=tmp_path)

    caminhos1 = territorio.materializar_bronze(data_coleta, diretorio_dados=tmp_path, caminho_config=caminho_config)
    linhas1 = pq.read_table(caminhos1["bairros_rpa"]).num_rows
    caminhos2 = territorio.materializar_bronze(data_coleta, diretorio_dados=tmp_path, caminho_config=caminho_config)
    linhas2 = pq.read_table(caminhos2["bairros_rpa"]).num_rows

    assert linhas1 == 2
    assert linhas2 == 2


def test_falha_de_rede_nao_gera_bronze(tmp_path):
    caminho_config = _config_teste(tmp_path)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=RuntimeError("Falha de conexão")), \
         patch("src.ingestao.territorio.CAMINHO_CONFIG_PADRAO", caminho_config):
        resultado = territorio.coletar_e_materializar(date(2026, 9, 24), diretorio_dados=tmp_path)

    assert resultado["execucao"]["status"] == "erro"
    assert resultado["bronze"] is None
    assert not (tmp_path / "bronze").exists()


def test_coletar_e_materializar_fluxo_completo(tmp_path, mock_ckan, mock_download):
    caminho_config = _config_teste(tmp_path)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan), \
         patch("src.ingestao.territorio.requests.get", mock_download), \
         patch("src.ingestao.territorio.CAMINHO_CONFIG_PADRAO", caminho_config):
        resultado = territorio.coletar_e_materializar(date(2026, 9, 24), diretorio_dados=tmp_path)

    assert resultado["execucao"]["status"] == "ok"
    assert resultado["bronze"] is not None
    assert set(resultado["bronze"].keys()) == {"bairros_rpa", "distritos_sanitarios", "bairros_geo"}
    for caminho_str in resultado["bronze"].values():
        assert Path(caminho_str).is_file()
