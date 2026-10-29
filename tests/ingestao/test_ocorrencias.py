"""Testes automatizados para a coleta de ocorrências / Defesa Civil (ING-03).

Sem chamadas à rede; todas as respostas CKAN são mockadas com registros
modelados na amostra real do recurso "Sedec Solicitações Tempo Real".
"""

from datetime import date
import json
from pathlib import Path
from unittest.mock import patch
import pyarrow.parquet as pq
import pytest

from src.ingestao import ocorrencias
from src.ingestao import runner


FIXTURE_RAW = [
    {
        "_id": 1,
        "ano": 2026,
        "mes": "09-setembro",
        "processo_numero": 8024764523,
        "solicitacao_data": "2026-09-24",
        "solicitacao_hora": "08:50",
        "solicitacao_descricao": "Colocação de lonas plásticas e capinação na barreira",
        "solicitacao_regional": "NORTE",
        "solicitacao_bairro": "AGUA FRIA",
        "rpa_codigo": 2,
        "rpa_nome": "2-NORTE",
        "processo_situacao": "execucao",
        "processo_tipo": "ATENDIMENTO",
        "processo_solicitacao": "Colocacao de Lonas Plasticas",
    },
    {
        "_id": 2,
        "ano": 2026,
        "mes": "09-setembro",
        "processo_numero": 8024834323,
        "solicitacao_data": "2026-09-24",
        "solicitacao_hora": "9:5",  # sem zero à esquerda, propositalmente
        "solicitacao_descricao": "Vistoria de infiltração de água de residência vizinha",
        "solicitacao_regional": "NORTE",
        "solicitacao_bairro": "AGUA FRIA",
        "rpa_codigo": 2,
        "rpa_nome": "2-NORTE",
        "processo_situacao": "execucao",
        "processo_tipo": "ATENDIMENTO",
        "processo_solicitacao": "Vistoria",
    },
]


@pytest.fixture(autouse=True)
def _hoje_fixo(monkeypatch):
    """A fonte não tem histórico (BUG-09): a data usada nos testes precisa ser "hoje"."""
    monkeypatch.setattr(runner, "_hoje", lambda: date(2026, 9, 24))


@pytest.fixture
def mock_ckan_resposta():
    """Mock que devolve os registros sintéticos de ocorrências para qualquer resource_id."""
    def _mock_coletar(resource_id, *args, **kwargs):
        return FIXTURE_RAW, {"resource_id": resource_id, "total": len(FIXTURE_RAW), "coletado_em": "2026-09-24T00:00:00"}

    return _mock_coletar


def test_coletar_dados_devolve_payload_com_records(mock_ckan_resposta):
    """coletar_dados deve chamar coletar_todos uma vez (fonte única, sem múltiplos agravos)."""
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan_resposta) as mock_ckan:
        conteudo_bytes = ocorrencias.coletar_dados(date(2026, 9, 24))

    assert mock_ckan.call_count == 1
    dados = json.loads(conteudo_bytes.decode("utf-8"))
    assert len(dados["records"]) == 2

    total = ocorrencias.contar_registros(conteudo_bytes)
    assert total == 2


def test_runner_executa_ocorrencias_e_grava_raw(tmp_path, mock_ckan_resposta):
    """Integração com runner: executar('ocorrencias') grava RAW fiel e gera registro de execução."""
    data_coleta = date(2026, 9, 24)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan_resposta):
        registro = runner.executar("ocorrencias", data_coleta=data_coleta, diretorio_dados=tmp_path)

    assert registro["status"] == "ok"
    assert registro["numero_registros"] == 2

    caminho_raw = tmp_path / "raw" / "ocorrencias" / "2026" / "09" / "24" / "datastore_search.json"
    assert caminho_raw.is_file()
    conteudo = json.loads(caminho_raw.read_text(encoding="utf-8"))
    assert len(conteudo["records"]) == 2


def test_transformar_para_bronze_mapeia_tipa_e_traduz_status():
    """_transformar_para_bronze deve mapear colunas, combinar data+hora e traduzir status."""
    mapeamento = {
        "processo_numero": "protocolo",
        "solicitacao_bairro": "bairro",
        "processo_solicitacao": "tipo_ocorrencia",
        "processo_situacao": "status",
        "solicitacao_descricao": "descricao",
    }
    mapa_status = {"execucao": "em_atendimento"}

    bronze = ocorrencias._transformar_para_bronze(FIXTURE_RAW, mapeamento, mapa_status)
    assert len(bronze) == 2

    item = bronze[0]
    assert item["protocolo"] == "8024764523"  # numérico convertido para string
    assert item["data_ocorrencia"] == "2026-09-24 08:50:00"
    assert item["bairro"] == "AGUA FRIA"
    assert item["tipo_ocorrencia"] == "Colocacao de Lonas Plasticas"
    assert item["status"] == "em_atendimento"  # traduzido via mapa_status
    assert item["latitude"] is None
    assert item["longitude"] is None

    # hora sem zero à esquerda ("9:5") deve virar "09:05:00"
    assert bronze[1]["data_ocorrencia"] == "2026-09-24 09:05:00"


def test_status_sem_mapeamento_passa_intacto_para_validacao_falhar():
    """Valor de status fora do mapa_status não é inventado — segue intacto (e deve falhar o contrato)."""
    registro = dict(FIXTURE_RAW[0])
    registro["processo_situacao"] = "arquivado"  # valor não observado/mapeado
    mapeamento = {"processo_numero": "protocolo", "processo_situacao": "status"}

    bronze = ocorrencias._transformar_para_bronze([registro], mapeamento, {"execucao": "em_atendimento"})
    assert bronze[0]["status"] == "arquivado"  # não mapeado, repassado como veio


def test_materializar_bronze_gera_parquet_valido_com_coordenadas_nulas(tmp_path, mock_ckan_resposta):
    """materializar_bronze lê a RAW, valida com contratos.py e grava Parquet válido.

    Confirma que registros sem coordenada são MANTIDOS (não descartados) —
    critério de aceitação da ING-03.
    """
    data_coleta = date(2026, 9, 24)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan_resposta):
        runner.executar("ocorrencias", data_coleta=data_coleta, diretorio_dados=tmp_path)

    caminho_parquet = ocorrencias.materializar_bronze(data_coleta, diretorio_dados=tmp_path)
    assert caminho_parquet.is_file()
    assert caminho_parquet.name == "ocorrencias.parquet"

    tabela = pq.read_table(caminho_parquet)
    assert tabela.num_rows == 2  # nenhum registro descartado por falta de coordenada

    colunas = tabela.column_names
    for esperado in ("protocolo", "data_ocorrencia", "tipo_ocorrencia", "bairro",
                      "latitude", "longitude", "status", "descricao"):
        assert esperado in colunas

    assert set(tabela["latitude"].to_pylist()) == {None}
    assert set(tabela["longitude"].to_pylist()) == {None}


def test_idempotencia_materializacao_bronze(tmp_path, mock_ckan_resposta):
    """Reexecutar materializar_bronze na mesma janela sobrescreve sem duplicar linhas."""
    data_coleta = date(2026, 9, 24)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan_resposta):
        runner.executar("ocorrencias", data_coleta=data_coleta, diretorio_dados=tmp_path)

    p1 = ocorrencias.materializar_bronze(data_coleta, diretorio_dados=tmp_path)
    linhas_primeira_exec = pq.read_table(p1).num_rows

    p2 = ocorrencias.materializar_bronze(data_coleta, diretorio_dados=tmp_path)
    linhas_segunda_exec = pq.read_table(p2).num_rows

    assert linhas_primeira_exec == 2
    assert linhas_segunda_exec == 2


def test_violacao_contrato_nao_gera_bronze(tmp_path):
    """Status fora do domínio do contrato (ex. 'arquivado', não mapeado) falha a validação."""
    data_coleta = date(2026, 9, 24)
    caminho_raw = tmp_path / "raw" / "ocorrencias" / "2026" / "09" / "24" / "datastore_search.json"
    caminho_raw.parent.mkdir(parents=True, exist_ok=True)

    payload_invalido = {
        "records": [
            {
                "processo_numero": 123,
                "solicitacao_data": "2026-09-24",
                "solicitacao_hora": "10:00",
                "solicitacao_bairro": "BOA VIAGEM",
                "processo_solicitacao": "Vistoria",
                "processo_situacao": "arquivado",  # fora do domínio e do mapa_status
            }
        ]
    }
    caminho_raw.write_text(json.dumps(payload_invalido), encoding="utf-8")

    with pytest.raises(ValueError, match="Violações do contrato de ocorrencias"):
        ocorrencias.materializar_bronze(data_coleta, diretorio_dados=tmp_path)

    caminho_bronze = tmp_path / "bronze" / "ocorrencias" / "2026" / "09" / "24" / "ocorrencias.parquet"
    assert not caminho_bronze.exists()


def test_falha_de_rede_nao_gera_bronze(tmp_path):
    """Falha de rede em coletar_todos é registrada como erro e não gera Bronze parcial."""
    data_coleta = date(2026, 9, 24)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=RuntimeError("Falha de conexão com CKAN")):
        resultado = ocorrencias.coletar_e_materializar(data_coleta, diretorio_dados=tmp_path)

    assert resultado["execucao"]["status"] == "erro"
    assert "Falha de conexão com CKAN" in resultado["execucao"]["mensagem"]
    assert resultado["bronze"] is None
    assert not (tmp_path / "bronze").exists()


def test_coletar_e_materializar_fluxo_completo(tmp_path, mock_ckan_resposta):
    """Fluxo fim a fim: coleta RAW e materializa Bronze com sucesso."""
    data_coleta = date(2026, 9, 24)
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=mock_ckan_resposta):
        resultado = ocorrencias.coletar_e_materializar(data_coleta, diretorio_dados=tmp_path)

    assert resultado["execucao"]["status"] == "ok"
    assert resultado["bronze"] is not None
    assert Path(resultado["bronze"]).is_file()


def _mock_com_data(solicitacao_data):
    registros = [dict(FIXTURE_RAW[0], solicitacao_data=solicitacao_data)]
    return lambda resource_id, *a, **k: (registros, {"total": 1})


def test_fonte_congelada_e_recusada_sem_gravar(tmp_path):
    """BUG-11: o feed 'tempo real' está parado em 2023 — não pode virar dado de hoje."""
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=_mock_com_data("2023-03-29T00:00:00")):
        resultado = ocorrencias.coletar_e_materializar(date(2026, 9, 24), diretorio_dados=tmp_path)

    assert resultado["execucao"]["status"] == "erro"
    assert "desatualizada" in resultado["execucao"]["mensagem"]
    assert "2023-03-29" in resultado["execucao"]["mensagem"]
    assert not (tmp_path / "raw").exists()
    assert not (tmp_path / "bronze").exists()


def test_fonte_dentro_do_limite_de_defasagem_e_coletada(tmp_path):
    with patch("src.ingestao.recife_ckan.coletar_todos", side_effect=_mock_com_data("2026-09-20T00:00:00")):
        resultado = ocorrencias.coletar_e_materializar(date(2026, 9, 24), diretorio_dados=tmp_path)

    assert resultado["execucao"]["status"] == "ok"
    assert resultado["bronze"]


def test_limite_de_defasagem_configurado():
    assert ocorrencias.carregar_configuracao_fonte()["max_defasagem_dias"] == 7
