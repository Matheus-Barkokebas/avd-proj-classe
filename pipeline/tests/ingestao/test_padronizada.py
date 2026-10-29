"""Testes da camada padronizada no Neon (decisão 0001) — sem rede: a conexão é um dublê."""

from datetime import date
import json

import pytest

from src.ingestao import bronze
from src.ingestao import contratos
from src.ingestao import padronizada
from src.ingestao import territorio

DIA = date(2026, 10, 28)


class CopiaFalsa:
    def __init__(self, cursor, sql):
        self.cursor, self.sql = cursor, sql

    def __enter__(self):
        self.cursor.copias.append((self.sql, []))
        return self

    def __exit__(self, *a):
        return False

    def write_row(self, linha):
        self.cursor.copias[-1][1].append(list(linha))


class CursorFalso:
    def __init__(self, conexao):
        self.c = conexao
        self.copias = conexao.copias

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.c.comandos.append((" ".join(sql.split()), params))

    def copy(self, sql):
        return CopiaFalsa(self, sql)

    def fetchone(self):
        return (self.c.contagem,)


class ConexaoFalsa:
    def __init__(self, falhar_em=None):
        self.comandos, self.copias, self.contagem = [], [], 0
        self.commits = self.rollbacks = 0
        self.falhar_em = falhar_em

    def __enter__(self):
        return self

    def __exit__(self, tipo, *a):
        # mesmo contrato do psycopg: commit sem erro, rollback com erro
        if tipo is None:
            self.commits += 1
        else:
            self.rollbacks += 1
        return False

    def cursor(self):
        cur = CursorFalso(self)
        if self.falhar_em:
            original = cur.execute

            def execute(sql, params=None):
                if self.falhar_em in sql:
                    raise RuntimeError("falha simulada no banco")
                original(sql, params)
            cur.execute = execute
        return cur


def sqls(conexao):
    return [s for s, _ in conexao.comandos]


def test_ddl_vem_do_contrato_com_not_null_e_chave_unica():
    ddl = " ".join(padronizada.ddl_tabela(contratos.carregar_contrato("epidemiologia")).split())
    assert ddl.startswith("CREATE TABLE IF NOT EXISTS epidemiologia (")
    assert "protocolo text NOT NULL" in ddl
    assert "data_notificacao timestamp NOT NULL" in ddl
    assert "classificacao_final text," in ddl  # opcional: sem NOT NULL
    assert "CONSTRAINT uq_epidemiologia_chave UNIQUE (agravo, protocolo, data_notificacao)" in ddl
    assert "data_coleta date NOT NULL" in ddl


@pytest.mark.parametrize("nome", ["epidemiologia", "ocorrencias", "ana_chuva", "ana_nivel"])
def test_todos_os_contratos_geram_sql(nome):
    contrato = contratos.carregar_contrato(nome)
    padronizada.ddl_tabela(contrato)
    _, copy, insert = padronizada.sql_carga(contrato)
    assert copy.startswith(f"COPY carga_{nome} (")
    assert insert.startswith(f"INSERT INTO {nome} (")


def test_carga_e_idempotente_pela_chave_de_negocio():
    _, _, insert = padronizada.sql_carga(contratos.carregar_contrato("epidemiologia"))
    assert "ON CONFLICT ON CONSTRAINT uq_epidemiologia_chave DO UPDATE SET" in insert
    assert "DISTINCT ON (agravo, protocolo, data_notificacao)" in insert


def test_identificador_suspeito_e_recusado():
    with pytest.raises(ValueError, match="Identificador SQL inválido"):
        padronizada.ddl_tabela({"tabela": "x; DROP TABLE y", "campos": []})


def test_gravar_envia_validas_por_copy_e_rejeitadas_com_motivo():
    conexao = ConexaoFalsa()
    destino = padronizada.DestinoNeon(lambda: conexao)
    contrato = contratos.carregar_contrato("epidemiologia")
    validas = [{"protocolo": "1", "data_notificacao": "2025-04-03 00:00:00", "semana_epidemiologica": 202514,
                "ano": 2025, "bairro": "PINA", "agravo": "dengue", "classificacao_final": "10", "contagem": 1}]
    rejeitadas = [{"linha": 2, "motivos": ["[obrigatorio] bairro: vazio"], "registro": {"protocolo": "2"}}]
    resumo = destino.gravar(contrato, "epidemiologia", DIA, validas, rejeitadas)

    assert resumo == "neon:epidemiologia (1 válidas enviadas, 1 rejeitadas)"
    assert conexao.commits == 1 and conexao.rollbacks == 0
    sql_copy, linhas = conexao.copias[0]
    assert sql_copy.startswith("COPY carga_epidemiologia")
    assert linhas[0][0] == "1" and linhas[0][-1] == DIA  # última coluna: data_coleta
    assert any(s.startswith("DELETE FROM rejeitados") for s in sqls(conexao))
    params = [p for s, p in conexao.comandos if s.startswith("INSERT INTO rejeitados")][0]
    assert json.loads(params[3]) == ["[obrigatorio] bairro: vazio"]


def test_falha_no_meio_faz_rollback():
    conexao = ConexaoFalsa(falhar_em="INSERT INTO epidemiologia")
    destino = padronizada.DestinoNeon(lambda: conexao)
    with pytest.raises(RuntimeError, match="falha simulada"):
        destino.gravar(contratos.carregar_contrato("epidemiologia"), "epidemiologia", DIA, [], [])
    assert conexao.rollbacks == 1 and conexao.commits == 0


def test_bronze_com_destino_neon_aplica_a_mesma_quarentena(tmp_path):
    conexao = ConexaoFalsa()
    destino = padronizada.DestinoNeon(lambda: conexao)
    boa = {"protocolo": "1", "data_notificacao": "2025-04-03 00:00:00", "semana_epidemiologica": 202514,
           "ano": 2025, "bairro": "PINA", "agravo": "dengue", "classificacao_final": None, "contagem": 1}
    ruim = {**boa, "protocolo": "2", "bairro": ""}
    resumo = bronze.gravar_validado([boa, ruim], "epidemiologia", "epidemiologia", DIA, tmp_path, destino=destino)
    assert resumo == "neon:epidemiologia (1 válidas enviadas, 1 rejeitadas)"
    assert not (tmp_path / "bronze").exists()  # com Neon, nada de Parquet local


def test_criar_padrao_e_arquivo(monkeypatch, tmp_path):
    monkeypatch.setattr(padronizada.ambiente, "RAIZ_PROJETO", tmp_path)
    monkeypatch.delenv("AERVITA_PADRONIZADA", raising=False)
    assert padronizada.criar(None) is None
    with pytest.raises(ValueError):
        padronizada.criar("mysql")


def _raw_territorio(bairros_rpa, distritos):
    return {
        "bairros_rpa": {"tipo": "tabular", "records": bairros_rpa},
        "distritos_sanitarios": {"tipo": "tabular", "records": distritos},
        "bairros_geo": {"tipo": "arquivo", "formato": "geojson", "conteudo_base64": ""},
    }


def test_dimensoes_cruzam_bases_pelo_nome_normalizado():
    raw = _raw_territorio(
        [{"Bairro": "Alto Do Mandu", "rpa": 3}, {"Bairro": "Agua Fria", "rpa": 2}],
        [{"bairro": "Alto do Mandu", "distrito_sanitario": 3, "descricao_distrito": "DS III"},
         {"bairro": "Água Fria", "distrito_sanitario": 2, "descricao_distrito": "DS II"}],
    )
    d = territorio.dimensoes(raw, territorio.carregar_configuracao_fonte())
    assert d["dim_distrito"] == [{"distrito_sanitario": 2, "descricao_distrito": "DS II"},
                                 {"distrito_sanitario": 3, "descricao_distrito": "DS III"}]
    por_chave = {b["chave_bairro"]: b for b in d["dim_bairro"]}
    assert por_chave["AGUA FRIA"] == {"chave_bairro": "AGUA FRIA", "nome_bairro": "Água Fria", "rpa": 2, "distrito_sanitario": 2}
    assert d["sem_correspondencia"] == {"so_em_bairros_rpa": [], "so_em_distritos": []}


def test_dimensoes_relatam_bairro_sem_correspondencia():
    raw = _raw_territorio([{"Bairro": "Pina", "rpa": 6}], [{"bairro": "Ibura", "distrito_sanitario": 7, "descricao_distrito": "DS VII"}])
    d = territorio.dimensoes(raw, territorio.carregar_configuracao_fonte())
    assert d["sem_correspondencia"] == {"so_em_bairros_rpa": ["PINA"], "so_em_distritos": ["IBURA"]}
    assert len(d["dim_bairro"]) == 2  # nada é descartado em silêncio


def test_gravar_dimensoes_substitui_as_tabelas():
    conexao = ConexaoFalsa()
    raw = _raw_territorio([{"Bairro": "Pina", "rpa": 6}], [{"bairro": "Pina", "distrito_sanitario": 6, "descricao_distrito": "DS VI"}])
    r = territorio.gravar_dimensoes(raw, padronizada.DestinoNeon(lambda: conexao))
    assert r["dim_distrito"] == "neon:dim_distrito (1 linhas)" and r["dim_bairro"] == "neon:dim_bairro (1 linhas)"
    assert "DELETE FROM dim_bairro" in sqls(conexao)
