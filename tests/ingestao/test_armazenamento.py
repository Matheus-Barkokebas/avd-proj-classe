"""Testes dos adaptadores de RAW (decisão 0001) — sem rede: o MongoDB é um dublê."""

from datetime import date
import json

import pytest

from src.ingestao import armazenamento as armaz
from src.ingestao import runner

DIA = date(2026, 10, 28)


class ColecaoFalsa:
    def __init__(self):
        self.docs, self.indices = [], []

    def create_index(self, chaves, unique=False, name=None):
        self.indices.append((tuple(chaves), unique, name))

    def _casa(self, doc, filtro):
        return all(doc.get(k) == v for k, v in filtro.items())

    def find_one(self, filtro):
        return next((dict(d) for d in self.docs if self._casa(d, filtro)), None)

    def update_one(self, filtro, mudanca):
        for d in self.docs:
            if self._casa(d, filtro):
                d.update(mudanca["$set"])
                return

    def replace_one(self, filtro, novo, upsert=False):
        for i, d in enumerate(self.docs):
            if self._casa(d, filtro):
                self.docs[i] = dict(novo)
                return
        if upsert:
            self.docs.append(dict(novo))


class BucketFalso:
    def __init__(self):
        self.arquivos, self._seq = {}, 0

    def upload_from_stream(self, nome, dados, metadata=None):
        self._seq += 1
        self.arquivos[self._seq] = bytes(dados)
        return self._seq

    def open_download_stream(self, ident):
        return type("Fluxo", (), {"read": lambda _self: self.arquivos[ident]})()

    def delete(self, ident):
        del self.arquivos[ident]


@pytest.fixture
def mongo():
    coletas, bucket, execucoes = ColecaoFalsa(), BucketFalso(), ColecaoFalsa()
    return armaz.ArmazenamentoMongo(coletas=coletas, bucket=bucket, execucoes=execucoes), coletas, bucket, execucoes


def test_arquivo_grava_e_le_no_caminho_particionado(tmp_path):
    a = armaz.ArmazenamentoArquivo(tmp_path)
    assert a.ler("dummy", DIA, "dummy.json") is None
    a.gravar("dummy", DIA, "dummy.json", b"[1]")
    assert (tmp_path / "raw" / "dummy" / "2026" / "10" / "28" / "dummy.json").read_bytes() == b"[1]"
    assert a.ler("dummy", DIA, "dummy.json") == b"[1]"


def test_mongo_cria_indice_unico(mongo):
    _, coletas, _, _ = mongo
    assert coletas.indices == [((("fonte", 1), ("data_coleta", 1), ("arquivo", 1)), True, "uq_fonte_data_arquivo")]


def test_mongo_grava_e_le_bytes_originais(mongo):
    m, coletas, _, _ = mongo
    conteudo = '{"records": [{"bairro": "Várzea"}]}'.encode("utf-8")
    assert m.gravar("epidemiologia", DIA, "datastore_search.json", conteudo) is True
    assert m.ler("epidemiologia", DIA, "datastore_search.json") == conteudo
    doc = coletas.docs[0]
    assert (doc["fonte"], doc["data_coleta"], doc["arquivo"]) == ("epidemiologia", "2026-10-28", "datastore_search.json")
    assert doc["tamanho_bytes"] == len(conteudo) and len(doc["sha256"]) == 64


def test_mongo_mesmo_conteudo_nao_duplica(mongo):
    m, coletas, bucket, _ = mongo
    m.gravar("epidemiologia", DIA, "x.json", b"[1]")
    assert m.gravar("epidemiologia", DIA, "x.json", b"[1]") is False
    assert len(coletas.docs) == 1 and len(bucket.arquivos) == 1


def test_mongo_conteudo_novo_substitui_e_apaga_o_anterior(mongo):
    m, coletas, bucket, _ = mongo
    m.gravar("epidemiologia", DIA, "x.json", b"[1]")
    m.gravar("epidemiologia", DIA, "x.json", b"[1, 2]")
    assert m.ler("epidemiologia", DIA, "x.json") == b"[1, 2]"
    assert len(coletas.docs) == 1 and list(bucket.arquivos.values()) == [b"[1, 2]"]


def test_mongo_datas_diferentes_sao_coletas_diferentes(mongo):
    m, coletas, _, _ = mongo
    m.gravar("epidemiologia", DIA, "x.json", b"[1]")
    m.gravar("epidemiologia", date(2026, 10, 29), "x.json", b"[1]")
    assert len(coletas.docs) == 2


def test_runner_grava_raw_e_execucao_no_mongo(mongo):
    m, _, _, execucoes = mongo
    registro = runner.executar("dummy", armazenamento=m)
    assert registro["status"] == "ok"
    dia = date.fromisoformat(registro["data_coleta"])
    assert json.loads(m.ler("dummy", dia, "dummy.json"))[0]["simulado"] is True
    assert execucoes.find_one({"_id": registro["id"]})["status"] == "ok"


def test_runner_reprocessa_data_explicita_sem_recoletar(mongo):
    m, _, _, _ = mongo
    m.gravar("dummy", DIA, "dummy.json", b'[{"a": 1}, {"a": 2}]')
    chamado = []
    coletores = {"dummy": runner.Coletor(lambda d: chamado.append(d) or b"[]", lambda c: len(json.loads(c)), "dummy.json")}
    registro = runner.executar("dummy", DIA, coletores=coletores, armazenamento=m)
    assert registro["status"] == "ok" and registro["numero_registros"] == 2
    assert registro["mensagem"] == "RAW existente relida" and chamado == []


def test_runner_sem_armazenamento_usa_arquivo_mesmo_com_env_mongo(tmp_path, monkeypatch):
    # Um .env apontando para o Mongo nunca pode fazer o runner acessar a rede.
    monkeypatch.setenv("AERVITA_ARMAZENAMENTO", "mongo")
    registro = runner.executar("dummy", diretorio_dados=tmp_path)
    assert registro["status"] == "ok"
    assert list((tmp_path / "raw" / "dummy").rglob("dummy.json"))


def test_criar_rejeita_tipo_desconhecido(tmp_path):
    with pytest.raises(ValueError, match="Armazenamento desconhecido"):
        armaz.criar("postgres", tmp_path)


def test_criar_padrao_e_arquivo(tmp_path, monkeypatch):
    monkeypatch.setattr(armaz.ambiente, "RAIZ_PROJETO", tmp_path)  # ignora o .env real
    monkeypatch.delenv("AERVITA_ARMAZENAMENTO", raising=False)
    assert isinstance(armaz.criar(None, tmp_path), armaz.ArmazenamentoArquivo)


def test_ler_json_ausente_explica_onde_procurou(mongo):
    m, _, _, _ = mongo
    with pytest.raises(FileNotFoundError, match="MongoDB raw_coletas ocorrencias/2026-10-28"):
        armaz.ler_json(m, "ocorrencias", DIA, "datastore_search.json")


def test_fonte_materializa_bronze_a_partir_da_raw_no_mongo(mongo, tmp_path):
    # Etapa E: as fontes leem a RAW pela interface, não mais pelo caminho do arquivo.
    from pathlib import Path

    from src.ingestao import ocorrencias

    m, _, _, _ = mongo
    amostra = Path(__file__).parents[1] / "fixtures" / "amostras" / "ocorrencias.json"
    registros = json.loads(amostra.read_text(encoding="utf-8"))
    m.gravar("ocorrencias", DIA, "datastore_search.json",
             json.dumps({"records": registros}, ensure_ascii=False).encode("utf-8"))
    caminho = ocorrencias.materializar_bronze(DIA, diretorio_dados=tmp_path, armazenamento=m)
    assert caminho.is_file() and caminho.suffix == ".parquet"
    assert not (tmp_path / "raw").exists()  # nada de RAW em disco

