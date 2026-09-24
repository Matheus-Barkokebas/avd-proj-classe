"""Testes automatizados para o coletor ANA HidroWebService (ING-04).

Sem chamadas à rede; toda resposta HTTP e todo dado de estação são
fixtures locais (a API real não foi verificada ao vivo nesta issue — ver
docstring de src/ingestao/ana_hidroweb.py).
"""

from datetime import date
import json
from pathlib import Path
from unittest.mock import Mock, patch
import pyarrow.parquet as pq
import pytest
import yaml

from src.ingestao import ana_hidroweb
from src.ingestao import runner


def _config_teste(tmp_path: Path, estacoes: list[dict] | None = None) -> Path:
    """Grava um conf/sources/ana_estacoes.yml sintético e devolve o caminho."""
    config = {
        "nome": "ana_hidroweb",
        "base_url": "https://ana.exemplo.invalido/hidrowebservice",
        "autenticacao": {
            "identificador_env": "ANA_TESTE_ID",
            "senha_env": "ANA_TESTE_SENHA",
        },
        "estacoes": estacoes if estacoes is not None else [
            {"codigo": "38010000", "nome": "Rio Capibaribe - teste", "tipo": "fluviometrica"},
            {"codigo": "38020000", "nome": "Rio Beberibe - teste", "tipo": "fluviometrica"},
        ],
        "mapeamento_colunas_chuva": {
            "Data_Hora_Medicao": "data_hora_medicao",
            "Chuva_Adotada": "chuva_mm",
            "NivelConsistencia": "status_leitura",
        },
        "mapeamento_colunas_nivel": {
            "Data_Hora_Medicao": "data_hora_medicao",
            "Cota_Adotada": "nivel_cm",
            "Vazao_Adotada": "vazao_m3s",
            "NivelConsistencia": "status_leitura",
        },
        "mapa_consistencia": {"1": "bruto", "2": "consistido"},
    }
    caminho = tmp_path / "ana_estacoes.yml"
    caminho.write_text(yaml.dump(config, allow_unicode=True), encoding="utf-8")
    return caminho


def _resposta_mock(json_data, status_ok=True):
    resp = Mock()
    resp.json.return_value = json_data
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        import requests
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError("erro")
    return resp


@pytest.fixture(autouse=True)
def _credenciais_env(monkeypatch):
    monkeypatch.setenv("ANA_TESTE_ID", "usuario-teste")
    monkeypatch.setenv("ANA_TESTE_SENHA", "senha-teste")


def test_autenticar_extrai_token(tmp_path):
    caminho_config = _config_teste(tmp_path)
    config = ana_hidroweb.carregar_configuracao_fonte(caminho_config)

    with patch("src.ingestao.ana_hidroweb.requests.get",
               return_value=_resposta_mock({"items": {"tokenautenticacao": "TOKEN-ABC"}})):
        token = ana_hidroweb.autenticar(config)

    assert token == "TOKEN-ABC"


def test_autenticar_falha_sem_credenciais(tmp_path, monkeypatch):
    monkeypatch.delenv("ANA_TESTE_ID", raising=False)
    caminho_config = _config_teste(tmp_path)
    config = ana_hidroweb.carregar_configuracao_fonte(caminho_config)

    with pytest.raises(RuntimeError, match="Credenciais"):
        ana_hidroweb.autenticar(config)


def test_coletar_dados_chuva_uma_estacao_falha_nao_impede_as_demais(tmp_path):
    caminho_config = _config_teste(tmp_path)

    def fake_get(url, params=None, headers=None, auth=None, timeout=None):
        if "OAUth" in url:
            return _resposta_mock({"items": {"tokenautenticacao": "TOKEN-ABC"}})
        codigo = params["Código da Estação"]
        if codigo == "38010000":
            return _resposta_mock({"items": [
                {"Data_Hora_Medicao": "2026-09-24T10:00:00", "Chuva_Adotada": 12.5, "NivelConsistencia": 1},
            ]})
        # segunda estação falha
        return _resposta_mock({}, status_ok=False)

    with patch("src.ingestao.ana_hidroweb.requests.get", side_effect=fake_get):
        conteudo = ana_hidroweb.coletar_dados_chuva(date(2026, 9, 24), caminho_config=caminho_config)

    payload = json.loads(conteudo)
    assert "records" in payload["38010000"]
    assert len(payload["38010000"]["records"]) == 1
    assert "erro" in payload["38020000"]  # estação com falha, registrada, não propagada

    assert ana_hidroweb.contar_registros(conteudo) == 1  # só conta a estação que teve sucesso


def test_transformar_serie_chuva_mapeia_tipa_e_traduz_consistencia():
    registros = [{"Data_Hora_Medicao": "2026-09-24T10:00:00", "Chuva_Adotada": "12.5", "NivelConsistencia": 1}]
    mapeamento = {"Data_Hora_Medicao": "data_hora_medicao", "Chuva_Adotada": "chuva_mm", "NivelConsistencia": "status_leitura"}
    linhas = ana_hidroweb._transformar_serie(registros, mapeamento, {"1": "bruto", "2": "consistido"}, "38010000")

    assert len(linhas) == 1
    item = linhas[0]
    assert item["codigo_estacao"] == "38010000"
    assert item["data_hora_medicao"] == "2026-09-24 10:00:00"
    assert item["chuva_mm"] == 12.5
    assert item["status_leitura"] == "bruto"


def test_transformar_serie_nivel_inclui_vazao_opcional():
    registros = [{"Data_Hora_Medicao": "2026-09-24T10:00:00", "Cota_Adotada": 340.0, "Vazao_Adotada": None, "NivelConsistencia": 2}]
    mapeamento = {
        "Data_Hora_Medicao": "data_hora_medicao", "Cota_Adotada": "nivel_cm",
        "Vazao_Adotada": "vazao_m3s", "NivelConsistencia": "status_leitura",
    }
    linhas = ana_hidroweb._transformar_serie(registros, mapeamento, {"1": "bruto", "2": "consistido"}, "38020000")

    assert linhas[0]["nivel_cm"] == 340.0
    assert linhas[0]["vazao_m3s"] is None
    assert linhas[0]["status_leitura"] == "consistido"


def test_status_sem_mapeamento_passa_intacto():
    registros = [{"Data_Hora_Medicao": "2026-09-24T10:00:00", "Chuva_Adotada": 1.0, "NivelConsistencia": 9}]
    mapeamento = {"Data_Hora_Medicao": "data_hora_medicao", "Chuva_Adotada": "chuva_mm", "NivelConsistencia": "status_leitura"}
    linhas = ana_hidroweb._transformar_serie(registros, mapeamento, {"1": "bruto"}, "38010000")
    assert linhas[0]["status_leitura"] == "9"  # não mapeado, repassado (deve falhar a validação do contrato)


def test_runner_integra_ana_chuva_e_grava_raw(tmp_path):
    caminho_config = _config_teste(tmp_path)

    def fake_get(url, params=None, headers=None, auth=None, timeout=None):
        if "OAUth" in url:
            return _resposta_mock({"items": {"tokenautenticacao": "TOKEN-ABC"}})
        return _resposta_mock({"items": [
            {"Data_Hora_Medicao": "2026-09-24T10:00:00", "Chuva_Adotada": 5.0, "NivelConsistencia": 1},
        ]})

    with patch("src.ingestao.ana_hidroweb.requests.get", side_effect=fake_get), \
         patch("src.ingestao.ana_hidroweb.CAMINHO_CONFIG_PADRAO", caminho_config):
        registro = runner.executar("ana_chuva", data_coleta=date(2026, 9, 24), diretorio_dados=tmp_path)

    assert registro["status"] == "ok"
    caminho_raw = tmp_path / "raw" / "ana_chuva" / "2026" / "09" / "24" / "hidroweb.json"
    assert caminho_raw.is_file()


def test_materializar_bronze_chuva_ignora_bloco_de_erro_e_valida_contrato(tmp_path):
    caminho_config = _config_teste(tmp_path)
    data_coleta = date(2026, 9, 24)
    caminho_raw = tmp_path / "raw" / "ana_chuva" / "2026" / "09" / "24" / "hidroweb.json"
    caminho_raw.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "38010000": {"records": [
            {"Data_Hora_Medicao": "2026-09-24T10:00:00", "Chuva_Adotada": 5.0, "NivelConsistencia": 1},
        ], "total": 1},
        "38020000": {"erro": "RuntimeError: falha simulada"},
    }
    caminho_raw.write_text(json.dumps(payload), encoding="utf-8")

    caminho_parquet = ana_hidroweb.materializar_bronze(
        "chuva", data_coleta, diretorio_dados=tmp_path, caminho_config=caminho_config
    )
    assert caminho_parquet.is_file()
    assert caminho_parquet.name == "ana_chuva.parquet"

    tabela = pq.read_table(caminho_parquet)
    assert tabela.num_rows == 1  # só a estação que teve sucesso entra na Bronze
    assert tabela["codigo_estacao"].to_pylist() == ["38010000"]
    for esperado in ("codigo_estacao", "data_hora_medicao", "chuva_mm", "status_leitura"):
        assert esperado in tabela.column_names


def test_idempotencia_materializacao_bronze(tmp_path):
    caminho_config = _config_teste(tmp_path)
    data_coleta = date(2026, 9, 24)
    caminho_raw = tmp_path / "raw" / "ana_nivel" / "2026" / "09" / "24" / "hidroweb.json"
    caminho_raw.parent.mkdir(parents=True, exist_ok=True)
    payload = {"38010000": {"records": [
        {"Data_Hora_Medicao": "2026-09-24T10:00:00", "Cota_Adotada": 300.0, "NivelConsistencia": 1},
    ], "total": 1}}
    caminho_raw.write_text(json.dumps(payload), encoding="utf-8")

    p1 = ana_hidroweb.materializar_bronze("nivel", data_coleta, diretorio_dados=tmp_path, caminho_config=caminho_config)
    linhas1 = pq.read_table(p1).num_rows
    p2 = ana_hidroweb.materializar_bronze("nivel", data_coleta, diretorio_dados=tmp_path, caminho_config=caminho_config)
    linhas2 = pq.read_table(p2).num_rows

    assert linhas1 == 1
    assert linhas2 == 1


def test_violacao_contrato_nao_gera_bronze(tmp_path):
    caminho_config = _config_teste(tmp_path)
    data_coleta = date(2026, 9, 24)
    caminho_raw = tmp_path / "raw" / "ana_chuva" / "2026" / "09" / "24" / "hidroweb.json"
    caminho_raw.parent.mkdir(parents=True, exist_ok=True)
    # chuva_mm ausente (obrigatório no contrato) -> deve violar
    payload = {"38010000": {"records": [
        {"Data_Hora_Medicao": "2026-09-24T10:00:00", "NivelConsistencia": 1},
    ], "total": 1}}
    caminho_raw.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Violações do contrato de ana_chuva"):
        ana_hidroweb.materializar_bronze("chuva", data_coleta, diretorio_dados=tmp_path, caminho_config=caminho_config)

    caminho_bronze = tmp_path / "bronze" / "ana_chuva" / "2026" / "09" / "24" / "ana_chuva.parquet"
    assert not caminho_bronze.exists()


def test_falha_de_autenticacao_nao_gera_bronze(tmp_path):
    caminho_config = _config_teste(tmp_path)
    data_coleta = date(2026, 9, 24)

    with patch("src.ingestao.ana_hidroweb.requests.get",
               return_value=_resposta_mock({}, status_ok=False)), \
         patch("src.ingestao.ana_hidroweb.CAMINHO_CONFIG_PADRAO", caminho_config):
        resultado = ana_hidroweb.coletar_e_materializar("chuva", data_coleta, diretorio_dados=tmp_path)

    assert resultado["execucao"]["status"] == "erro"
    assert resultado["bronze"] is None
    assert not (tmp_path / "bronze").exists()


def test_coletar_e_materializar_fluxo_completo(tmp_path):
    caminho_config = _config_teste(tmp_path)
    data_coleta = date(2026, 9, 24)

    def fake_get(url, params=None, headers=None, auth=None, timeout=None):
        if "OAUth" in url:
            return _resposta_mock({"items": {"tokenautenticacao": "TOKEN-ABC"}})
        return _resposta_mock({"items": [
            {"Data_Hora_Medicao": "2026-09-24T10:00:00", "Cota_Adotada": 310.0, "NivelConsistencia": 2},
        ]})

    with patch("src.ingestao.ana_hidroweb.requests.get", side_effect=fake_get), \
         patch("src.ingestao.ana_hidroweb.CAMINHO_CONFIG_PADRAO", caminho_config):
        resultado = ana_hidroweb.coletar_e_materializar("nivel", data_coleta, diretorio_dados=tmp_path)

    assert resultado["execucao"]["status"] == "ok"
    assert resultado["bronze"] is not None
    assert Path(resultado["bronze"]).is_file()
