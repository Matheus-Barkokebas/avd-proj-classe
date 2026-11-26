"""Ferramentas do servidor MCP com banco e GPT simulados, sem rede."""

import asyncio
from datetime import datetime
from decimal import Decimal

from fastmcp import Client
import pytest

from banco import _para_json, validar_select
import servidor


class BancoFalso:
    def __init__(self):
        self.consultas = []

    def listar_tabelas(self):
        return ["chuva_inmet_hora", "modelo_execucao"]

    def descrever_tabela(self, tabela):
        return [{"coluna": "hora", "tipo": "timestamp without time zone"}]

    def consultar(self, sql):
        self.consultas.append(validar_select(sql))
        return [{"total": 2424}]

    def esquema_completo(self):
        return "- gold.modelo_execucao: horas (integer)"


class GptFalso:
    def gerar_sql(self, pergunta, esquema):
        return "SELECT horas AS total FROM gold.modelo_execucao"

    def explicar_resultado(self, pergunta, dados):
        return f"O modelo foi treinado com {dados[0]['total']} horas."


@pytest.fixture
def banco(monkeypatch):
    falso = BancoFalso()
    monkeypatch.setattr(servidor, "banco", falso)
    monkeypatch.setattr(servidor, "_assistente", lambda: GptFalso())
    return falso


def chamar(ferramenta, argumentos):
    async def rodar():
        async with Client(servidor.mcp) as cliente:
            conteudo = (await cliente.call_tool(ferramenta, argumentos)).structured_content
            return conteudo.get("result", conteudo)
    return asyncio.run(rodar())


def test_quatro_ferramentas_do_modelo():
    async def listar():
        async with Client(servidor.mcp) as cliente:
            return {f.name for f in await cliente.list_tools()}
    assert asyncio.run(listar()) == {"listar_tabelas", "descrever_tabela", "executar_select", "perguntar_ao_banco"}


def test_listar_e_descrever(banco):
    assert chamar("listar_tabelas", {}) == ["chuva_inmet_hora", "modelo_execucao"]
    assert chamar("descrever_tabela", {"tabela": "chuva_inmet_hora"})[0]["coluna"] == "hora"


def test_perguntar_ao_banco_gera_executa_e_explica(banco):
    resultado = chamar("perguntar_ao_banco", {"pergunta": "Com quantas horas o modelo foi treinado?"})
    assert resultado["sql"].startswith("SELECT") and resultado["dados"] == [{"total": 2424}]
    assert "2424" in resultado["resposta"]
    assert banco.consultas == ["SELECT horas AS total FROM gold.modelo_execucao"]


@pytest.mark.parametrize("sql", [
    "DELETE FROM gold.mare", "DROP TABLE gold.mare", "SELECT 1; DROP TABLE gold.mare", "UPDATE gold.mare SET mare_m = 0",
])
def test_so_aceita_um_select(sql):
    with pytest.raises(ValueError):
        validar_select(sql)


def test_aceita_select_e_with():
    assert validar_select("  select 1; ") == "select 1"
    assert validar_select("WITH x AS (SELECT 1) SELECT * FROM x").startswith("WITH")


def test_valores_do_banco_viram_json():
    assert _para_json(Decimal("0.825")) == 0.825
    assert _para_json(datetime(2026, 10, 31, 20)) == "2026-10-31T20:00:00"
    assert _para_json("texto") == "texto"


def test_http_responde_mcp_e_libera_o_painel_no_cors(banco):
    from starlette.testclient import TestClient

    cabecalhos = {"Accept": "application/json, text/event-stream", "Origin": "http://localhost:5173"}
    with TestClient(servidor.app_http()) as http:
        resposta = http.post("/mcp", headers=cabecalhos, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert resposta.status_code == 200
        assert resposta.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert {f["name"] for f in resposta.json()["result"]["tools"]} >= {"executar_select", "perguntar_ao_banco"}
        assert "access-control-allow-origin" not in http.post(
            "/mcp", headers={**cabecalhos, "Origin": "https://outro.site"},
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}).headers
