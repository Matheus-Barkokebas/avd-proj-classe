"""Testes automatizados para a coleta de epidemiologia (ING-02).

Sem chamadas à rede; todas as respostas CKAN são mockadas.
"""

from datetime import date
import json
from pathlib import Path
from unittest.mock import patch
import pyarrow.parquet as pq
import pytest

from src.ingestao import epidemiologia
from src.ingestao import runner


FIXTURE_RAW_DENGUE = [
    {
        "_id": 1,
        "NU_NOTIFIC": 3059,
        "DT_NOTIFIC": "2025-04-03T00:00:00",
        "SEM_NOT": 202510,
        "NU_ANO": 2025,
        "NM_BAIRRO": "PINA",
        "ID_AGRAVO": "A90",
        "CLASSI_FIN": 10,
    }
]

# Zika e chikungunya vêm num formato diferente da dengue na API real (BUG-03):
# data DD/MM/AAAA e campos numéricos como texto.
FIXTURE_RAW_ZIKA = [
    {
        "_id": 2,
        "NU_NOTIFIC": "4012",
        "DT_NOTIFIC": "08/01/2025",
        "SEM_NOT": "202502",
        "NU_ANO": "2025",
        "NM_BAIRRO": "BOA VIAGEM",
        "ID_AGRAVO": "A92.8",
        "CLASSI_FIN": "2",
    }
]

FIXTURE_RAW_CHIKUNGUNYA = [
    {
        "_id": 3,
        "NU_NOTIFIC": "5098",
        "DT_NOTIFIC": "04/04/2025",
        "SEM_NOT": "202514",
        "NU_ANO": "2025",
        "NM_BAIRRO": "DERBY",
        "ID_AGRAVO": "A92.0",
        "CLASSI_FIN": "5",
    }
]


@pytest.fixture(autouse=True)
def _hoje_fixo(monkeypatch):
    """A fonte não tem histórico (BUG-09): a data usada nos testes precisa ser "hoje"."""
    monkeypatch.setattr(runner, "_hoje", lambda: date(2026, 9, 22))


@pytest.fixture
def mock_ckan_respostas():
    """Mock que retorna registros sintéticos por resource_id."""
    def _mock_coletar(resource_id, *args, **kwargs):
        if "45a675e2" in resource_id:  # dengue
            return FIXTURE_RAW_DENGUE, {"resource_id": resource_id, "total": 1, "coletado_em": "2026-09-22T00:00:00"}
        if "cf7dc2c4" in resource_id:  # zika
            return FIXTURE_RAW_ZIKA, {"resource_id": resource_id, "total": 1, "coletado_em": "2026-09-22T00:00:00"}
        if "b300a634" in resource_id:  # chikungunya
            return FIXTURE_RAW_CHIKUNGUNYA, {"resource_id": resource_id, "total": 1, "coletado_em": "2026-09-22T00:00:00"}
        return [], {"resource_id": resource_id, "total": 0, "coletado_em": "2026-09-22T00:00:00"}

    return _mock_coletar


def test_coletar_dados_combina_tres_agravos(mock_ckan_respostas):
    """coletar_dados deve chamar coletar_todos para dengue, zika e chikungunya."""
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan_respostas) as mock_ckan:
        conteudo_bytes = epidemiologia.coletar_dados(date(2026, 9, 22))

    assert mock_ckan.call_count == 3
    dados = json.loads(conteudo_bytes.decode("utf-8"))
    assert "dengue" in dados
    assert "zika" in dados
    assert "chikungunya" in dados
    assert len(dados["dengue"]["records"]) == 1
    assert len(dados["zika"]["records"]) == 1
    assert len(dados["chikungunya"]["records"]) == 1

    total = epidemiologia.contar_registros(conteudo_bytes)
    assert total == 3


def test_runner_executa_epidemiologia_e_grava_raw(tmp_path, mock_ckan_respostas):
    """Integração com runner: executar('epidemiologia') grava RAW fiel e gera registro de execução."""
    data_coleta = date(2026, 9, 22)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan_respostas):
        registro = runner.executar("epidemiologia", data_coleta=data_coleta, diretorio_dados=tmp_path)

    assert registro["status"] == "ok"
    assert registro["numero_registros"] == 3

    caminho_raw = tmp_path / "raw" / "epidemiologia" / "2026" / "09" / "22" / "datastore_search.json"
    assert caminho_raw.is_file()

    conteudo = json.loads(caminho_raw.read_text(encoding="utf-8"))
    assert "dengue" in conteudo
    assert "zika" in conteudo
    assert "chikungunya" in conteudo


def test_transformar_para_bronze_mapeia_e_converte_tipos():
    """_transformar_para_bronze deve converter tipos e fixar agravo e contagem."""
    mapeamento = {
        "NU_NOTIFIC": "protocolo",
        "DT_NOTIFIC": "data_notificacao",
        "SEM_NOT": "semana_epidemiologica",
        "NU_ANO": "ano",
        "NM_BAIRRO": "bairro",
        "CLASSI_FIN": "classificacao_final",
    }
    bronze = epidemiologia._transformar_para_bronze(FIXTURE_RAW_DENGUE, mapeamento, "dengue")
    assert len(bronze) == 1
    item = bronze[0]
    assert item["protocolo"] == "3059"  # numérico convertido para string
    assert item["data_notificacao"] == "2025-04-03 00:00:00"
    assert item["semana_epidemiologica"] == 202510
    assert item["ano"] == 2025
    assert item["bairro"] == "PINA"
    assert item["agravo"] == "dengue"
    assert item["classificacao_final"] == "10"
    assert item["contagem"] == 1


def test_transformar_para_bronze_formato_brasileiro_de_zika_e_chikungunya():
    """BUG-03: zika/chikungunya mandam DD/MM/AAAA e números como texto."""
    mapeamento = {
        "NU_NOTIFIC": "protocolo", "DT_NOTIFIC": "data_notificacao", "SEM_NOT": "semana_epidemiologica",
        "NU_ANO": "ano", "NM_BAIRRO": "bairro", "CLASSI_FIN": "classificacao_final",
    }
    item = epidemiologia._transformar_para_bronze(FIXTURE_RAW_ZIKA, mapeamento, "zika")[0]
    assert item["data_notificacao"] == "2025-01-08 00:00:00"  # 8 de janeiro, não 1º de agosto
    assert item["semana_epidemiologica"] == 202502
    assert item["ano"] == 2025
    assert item["protocolo"] == "4012"
    assert item["classificacao_final"] == "2"


def test_materializar_bronze_gera_parquet_valido(tmp_path, mock_ckan_respostas):
    """materializar_bronze lê a RAW, valida com contratos.py e grava Parquet válido."""
    data_coleta = date(2026, 9, 22)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan_respostas):
        runner.executar("epidemiologia", data_coleta=data_coleta, diretorio_dados=tmp_path)

    caminho_parquet = epidemiologia.materializar_bronze(data_coleta, diretorio_dados=tmp_path)
    assert caminho_parquet.is_file()
    assert caminho_parquet.name == "epidemiologia.parquet"

    tabela = pq.read_table(caminho_parquet)
    assert tabela.num_rows == 3

    colunas = tabela.column_names
    assert "protocolo" in colunas
    assert "data_notificacao" in colunas
    assert "semana_epidemiologica" in colunas
    assert "ano" in colunas
    assert "bairro" in colunas
    assert "agravo" in colunas
    assert "classificacao_final" in colunas
    assert "contagem" in colunas

    agravos = set(tabela["agravo"].to_pylist())
    assert agravos == {"dengue", "zika", "chikungunya"}


def test_idempotencia_materializacao_bronze(tmp_path, mock_ckan_respostas):
    """Reexecutar materializar_bronze na mesma janela sobrescreve sem duplicar linhas."""
    data_coleta = date(2026, 9, 22)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan_respostas):
        runner.executar("epidemiologia", data_coleta=data_coleta, diretorio_dados=tmp_path)

    p1 = epidemiologia.materializar_bronze(data_coleta, diretorio_dados=tmp_path)
    linhas_primeira_exec = pq.read_table(p1).num_rows

    p2 = epidemiologia.materializar_bronze(data_coleta, diretorio_dados=tmp_path)
    linhas_segunda_exec = pq.read_table(p2).num_rows

    assert linhas_primeira_exec == 3
    assert linhas_segunda_exec == 3


def test_violacao_contrato_nao_gera_bronze(tmp_path):
    """Se a RAW contiver violação do contrato (ex. protocolo nulo), lança erro e não grava Parquet."""
    data_coleta = date(2026, 9, 22)
    caminho_raw = tmp_path / "raw" / "epidemiologia" / "2026" / "09" / "22" / "datastore_search.json"
    caminho_raw.parent.mkdir(parents=True, exist_ok=True)

    # Registro com NU_NOTIFIC nulo (viola campo obrigatório 'protocolo')
    payload_invalido = {
        "dengue": {
            "records": [
                {
                    "NU_NOTIFIC": None,
                    "DT_NOTIFIC": "2025-04-03T00:00:00",
                    "SEM_NOT": 202510,
                    "NU_ANO": 2025,
                    "NM_BAIRRO": "PINA",
                }
            ]
        }
    }
    caminho_raw.write_text(json.dumps(payload_invalido), encoding="utf-8")

    with pytest.raises(ValueError, match="Violações do contrato de epidemiologia"):
        epidemiologia.materializar_bronze(data_coleta, diretorio_dados=tmp_path)

    caminho_bronze = tmp_path / "bronze" / "epidemiologia" / "2026" / "09" / "22" / "epidemiologia.parquet"
    assert not caminho_bronze.exists()


def test_falha_de_rede_nao_gera_bronze(tmp_path):
    """Falha de rede em coletar_todos é registrada como erro e não gera Bronze parcial."""
    data_coleta = date(2026, 9, 22)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=RuntimeError("Falha de conexão com CKAN")):
        resultado = epidemiologia.coletar_e_materializar(data_coleta, diretorio_dados=tmp_path)

    assert resultado["execucao"]["status"] == "erro"
    assert "Falha de conexão com CKAN" in resultado["execucao"]["mensagem"]
    assert resultado["bronze"] is None

    assert not (tmp_path / "bronze").exists()


def test_coletar_e_materializar_fluxo_completo(tmp_path, mock_ckan_respostas):
    """Fluxo fim a fim: coleta RAW e materializa Bronze com sucesso."""
    data_coleta = date(2026, 9, 22)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan_respostas):
        resultado = epidemiologia.coletar_e_materializar(data_coleta, diretorio_dados=tmp_path)

    assert resultado["execucao"]["status"] == "ok"
    assert resultado["bronze"] is not None
    assert Path(resultado["bronze"]).is_file()
