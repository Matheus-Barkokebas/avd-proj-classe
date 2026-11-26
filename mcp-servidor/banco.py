"""Acesso somente leitura à camada Gold do Neon."""

from datetime import date, datetime
from decimal import Decimal
import re

import psycopg

LIMITE_LINHAS = 200
TEMPO_MAXIMO_MS = 5000


def _para_json(valor):
    """Converte o que o PostgreSQL devolve em tipos que viram JSON."""
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return valor


def validar_select(sql: str) -> str:
    """Aceita um único SELECT (ou WITH ... SELECT); recusa qualquer outro comando."""
    comando = sql.strip().rstrip(";").strip()
    if ";" in comando:
        raise ValueError("Envie um único comando SQL.")
    if not re.match(r"(?is)^(select|with)\b", comando):
        raise ValueError("Só são permitidos comandos SELECT.")
    return comando


class BancoNeon:
    def __init__(self, url_conexao: str, schema: str = "gold"):
        self.url_conexao = url_conexao
        self.schema = schema

    def _conectar(self) -> psycopg.Connection:
        conexao = psycopg.connect(self.url_conexao)
        # Somente leitura: o banco recusa INSERT, UPDATE, DELETE, DROP...
        conexao.read_only = True
        return conexao

    def consultar(self, sql: str, parametros: tuple | None = None) -> list[dict]:
        """Executa um SELECT e devolve até LIMITE_LINHAS linhas como dicionários."""
        comando = validar_select(sql)
        with self._conectar() as conexao, conexao.cursor() as cursor:
            cursor.execute(f"SET statement_timeout = {TEMPO_MAXIMO_MS}")
            cursor.execute(comando, parametros)
            colunas = [coluna.name for coluna in cursor.description]
            linhas = cursor.fetchmany(LIMITE_LINHAS)
        return [{c: _para_json(v) for c, v in zip(colunas, linha)} for linha in linhas]

    def listar_tabelas(self) -> list[str]:
        """Tabelas e views do schema da Gold."""
        sql = """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = %s ORDER BY table_name
        """
        return [linha["table_name"] for linha in self.consultar(sql, (self.schema,))]

    def descrever_tabela(self, tabela: str) -> list[dict]:
        """Colunas e tipos de uma tabela. O %s evita SQL injection."""
        sql = """
            SELECT column_name AS coluna, data_type AS tipo FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position
        """
        return self.consultar(sql, (self.schema, tabela))

    def esquema_completo(self) -> str:
        """Texto com todas as tabelas e colunas, usado pelo GPT para escrever o SQL."""
        linhas = []
        for tabela in self.listar_tabelas():
            colunas = ", ".join(f"{c['coluna']} ({c['tipo']})" for c in self.descrever_tabela(tabela))
            linhas.append(f"- {self.schema}.{tabela}: {colunas}")
        return "\n".join(linhas)
