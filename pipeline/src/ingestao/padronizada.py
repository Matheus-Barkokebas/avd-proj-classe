"""Camada padronizada no Neon/PostgreSQL (decisão 0001).

Substitui a Bronze em Parquet nesta release: as linhas já validadas pelo
contrato (bronze.separar) vão para uma tabela por contrato, e as rejeitadas
para a tabela `rejeitados`, com o motivo.

As tabelas nascem dos próprios contratos de conf/contracts/: cada campo vira
coluna tipada, `obrigatorio: true` vira NOT NULL e `chave_negocio` vira UNIQUE.
A carga é idempotente (ON CONFLICT na chave de negócio) e atômica (uma única
transação por lote: se falhar no meio, nada muda).
"""

from datetime import date
import json
import re
from typing import Any, Callable

from src.ingestao import ambiente

TIPOS_SQL = {
    "string": "text",
    "int": "bigint",
    "float": "double precision",
    "datetime": "timestamp",
    "date": "date",
    "bool": "boolean",
}
COLUNAS_CONTROLE = ("data_coleta", "carregado_em")
_IDENTIFICADOR = re.compile(r"[a-z][a-z0-9_]*")

DDL_REJEITADOS = """
CREATE TABLE IF NOT EXISTS rejeitados (
    id bigserial PRIMARY KEY,
    fonte text NOT NULL,
    data_coleta date NOT NULL,
    linha integer NOT NULL,
    motivos jsonb NOT NULL,
    registro jsonb NOT NULL,
    gravado_em timestamptz NOT NULL DEFAULT now()
)"""
INDICE_REJEITADOS = "CREATE INDEX IF NOT EXISTS ix_rejeitados_fonte_data ON rejeitados (fonte, data_coleta)"


def _ident(nome: str) -> str:
    """Só aceita snake_case simples: os nomes vêm do contrato e entram no SQL."""
    if not _IDENTIFICADOR.fullmatch(nome or ""):
        raise ValueError(f"Identificador SQL inválido no contrato: {nome!r}")
    return nome


def colunas(contrato: dict[str, Any]) -> list[str]:
    nomes = [_ident(c["nome"]) for c in contrato["campos"]]
    conflito = set(nomes) & set(COLUNAS_CONTROLE)
    if conflito:
        raise ValueError(f"Campo do contrato colide com coluna de controle: {sorted(conflito)}")
    return nomes


def ddl_tabela(contrato: dict[str, Any]) -> str:
    """CREATE TABLE gerado a partir do contrato (FND-02)."""
    tabela = _ident(contrato["tabela"])
    linhas = []
    for campo in contrato["campos"]:
        tipo = TIPOS_SQL.get(campo["tipo"])
        if tipo is None:
            raise ValueError(f"Tipo sem correspondência SQL: {campo['tipo']!r} ({campo['nome']})")
        linhas.append(f"    {_ident(campo['nome'])} {tipo}{' NOT NULL' if campo.get('obrigatorio') else ''}")
    linhas.append("    data_coleta date NOT NULL")
    linhas.append("    carregado_em timestamptz NOT NULL DEFAULT now()")
    chave = [_ident(c) for c in contrato.get("chave_negocio") or []]
    if chave:
        linhas.append(f"    CONSTRAINT uq_{tabela}_chave UNIQUE ({', '.join(chave)})")
    return f"CREATE TABLE IF NOT EXISTS {tabela} (\n" + ",\n".join(linhas) + "\n)"


def sql_carga(contrato: dict[str, Any]) -> tuple[str, str, str]:
    """(tabela temporária, COPY, INSERT definitivo) para um lote do contrato."""
    tabela = _ident(contrato["tabela"])
    cols = colunas(contrato) + ["data_coleta"]
    lista = ", ".join(cols)
    temp = f"CREATE TEMP TABLE carga_{tabela} (LIKE {tabela} INCLUDING DEFAULTS) ON COMMIT DROP"
    copy = f"COPY carga_{tabela} ({lista}) FROM STDIN"
    chave = [_ident(c) for c in contrato.get("chave_negocio") or []]
    if chave:
        # DISTINCT ON: se a fonte repetir a chave no mesmo lote, fica a última
        # ocorrência — sem isso o ON CONFLICT falha ao tocar a mesma linha duas vezes.
        atualiza = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c not in chave)
        insert = (
            f"INSERT INTO {tabela} ({lista}) "
            f"SELECT DISTINCT ON ({', '.join(chave)}) {lista} FROM carga_{tabela} "
            f"ORDER BY {', '.join(chave)}, ctid DESC "
            f"ON CONFLICT ON CONSTRAINT uq_{tabela}_chave DO UPDATE SET {atualiza}, carregado_em = now()"
        )
    else:
        insert = f"INSERT INTO {tabela} ({lista}) SELECT {lista} FROM carga_{tabela}"
    return temp, copy, insert


class DestinoNeon:
    """Grava a camada padronizada no Neon (PostgreSQL)."""

    def __init__(self, conectar: Callable[[], Any]):
        # `conectar` devolve uma conexão psycopg; os testes passam um dublê.
        self._conectar = conectar

    def conexao(self) -> Any:
        """Conexão nova para leitura (ex.: a exportação do painel)."""
        return self._conectar()

    @classmethod
    def do_ambiente(cls) -> "DestinoNeon":
        url = ambiente.obrigatoria("NEON_DATABASE_URL")

        def conectar():
            import psycopg

            return psycopg.connect(url, connect_timeout=20, application_name="aervita-ingestao")

        return cls(conectar)

    def gravar(
        self,
        contrato: dict[str, Any],
        fonte: str,
        data_coleta: date,
        validas: list[dict[str, Any]],
        rejeitadas: list[dict[str, Any]],
    ) -> str:
        cols = colunas(contrato)
        temp, copy, insert = sql_carga(contrato)
        with self._conectar() as conexao:  # commit no fim, rollback se der erro
            with conexao.cursor() as cur:
                cur.execute(ddl_tabela(contrato))
                cur.execute(DDL_REJEITADOS)
                cur.execute(INDICE_REJEITADOS)
                cur.execute(temp)
                with cur.copy(copy) as dados:
                    for reg in validas:
                        dados.write_row([reg.get(c) for c in cols] + [data_coleta])
                cur.execute(insert)
                cur.execute("DELETE FROM rejeitados WHERE fonte = %s AND data_coleta = %s", (fonte, data_coleta))
                for rej in rejeitadas:
                    cur.execute(
                        "INSERT INTO rejeitados (fonte, data_coleta, linha, motivos, registro) "
                        "VALUES (%s, %s, %s, %s::jsonb, %s::jsonb)",
                        (fonte, data_coleta, rej["linha"], json.dumps(rej["motivos"], ensure_ascii=False),
                         json.dumps(rej["registro"], ensure_ascii=False, default=str)),
                    )
        return f"neon:{contrato['tabela']} ({len(validas)} válidas enviadas, {len(rejeitadas)} rejeitadas)"

    def contar_rejeitados(self, fonte: str, data_coleta: date) -> int:
        with self._conectar() as conexao, conexao.cursor() as cur:
            cur.execute(DDL_REJEITADOS)
            cur.execute("SELECT count(*) FROM rejeitados WHERE fonte = %s AND data_coleta = %s", (fonte, data_coleta))
            return int(cur.fetchone()[0])

    def gravar_tabela(self, nome: str, ddl: str, colunas_tabela: list[str], linhas: list[dict[str, Any]]) -> str:
        """Substitui por completo uma tabela de referência (ex.: dimensões do território)."""
        nome = _ident(nome)
        cols = [_ident(c) for c in colunas_tabela]
        with self._conectar() as conexao, conexao.cursor() as cur:
            cur.execute(ddl)
            cur.execute(f"DELETE FROM {nome}")
            with cur.copy(f"COPY {nome} ({', '.join(cols)}) FROM STDIN") as dados:
                for linha in linhas:
                    dados.write_row([linha.get(c) for c in cols])
        return f"neon:{nome} ({len(linhas)} linhas)"


def criar(tipo: str | None = None) -> DestinoNeon | None:
    """Destino da camada padronizada: 'neon' ou 'arquivo' (None = Parquet local, comportamento antigo)."""
    tipo = tipo or ambiente.opcional("AERVITA_PADRONIZADA", "arquivo")
    if tipo not in ("arquivo", "neon"):
        raise ValueError(f"Camada padronizada desconhecida: {tipo!r}. Use 'arquivo' ou 'neon'")
    return DestinoNeon.do_ambiente() if tipo == "neon" else None
