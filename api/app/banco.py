"""Conexão com o Neon: pool de conexões e consulta que devolve dicionários.

Único módulo que conhece o psycopg. Os repositórios recebem um objeto com o
método `consultar(sql, parametros)`; os testes passam um dublê sem rede.
"""

from typing import Any, Protocol


class Banco(Protocol):
    def consultar(self, sql: str, parametros: tuple | dict | None = None) -> list[dict[str, Any]]: ...
    def verificar(self) -> None: ...


class BancoNeon:
    """Pool de conexões com o Neon (PostgreSQL). Abre sob demanda, fecha no desligamento."""

    def __init__(self, url: str, minimo: int = 1, maximo: int = 5):
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        self._pool = ConnectionPool(
            url, min_size=minimo, max_size=maximo, open=False,
            kwargs={"row_factory": dict_row, "application_name": "aervita-api", "connect_timeout": 20},
        )

    def abrir(self) -> None:
        self._pool.open(wait=False)

    def fechar(self) -> None:
        self._pool.close()

    def consultar(self, sql: str, parametros: tuple | dict | None = None) -> list[dict[str, Any]]:
        with self._pool.connection() as conexao:
            # sessão só de leitura: mesmo com um usuário com mais permissão, a API não grava
            conexao.read_only = True
            return conexao.execute(sql, parametros).fetchall()

    def verificar(self) -> None:
        self.consultar("SELECT 1 AS ok")
