"""Servidor MCP do AerVita: expõe a camada Gold do Neon como ferramentas para uma IA."""

import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from assistente import AssistenteGPT
from banco import BancoNeon

load_dotenv()

banco = BancoNeon(os.getenv("NEON_DATABASE_URL", ""))
mcp = FastMCP("AerVita: Neon (Gold) + GPT")


def _assistente() -> AssistenteGPT:
    """Criado só quando usado: as ferramentas de banco funcionam sem a chave do GPT."""
    chave = os.getenv("OPENAI_API_KEY")
    if not chave:
        raise RuntimeError("Defina OPENAI_API_KEY no .env para usar perguntar_ao_banco.")
    return AssistenteGPT(chave, os.getenv("OPENAI_MODELO", "gpt-6-luna"))


# Cada função com @mcp.tool vira uma ferramenta; a docstring é a descrição que a IA lê.

@mcp.tool
def listar_tabelas() -> list[str]:
    """Lista as tabelas e views da camada Gold do AerVita (chuva, maré, alagamento, arboviroses, território, modelo)."""
    return banco.listar_tabelas()


@mcp.tool
def descrever_tabela(tabela: str) -> list[dict]:
    """Mostra as colunas e os tipos de uma tabela da camada Gold."""
    return banco.descrever_tabela(tabela)


@mcp.tool
def executar_select(sql: str) -> list[dict]:
    """Executa um único comando SELECT na camada Gold (use gold.<tabela>) e devolve até 200 linhas."""
    return banco.consultar(sql)


@mcp.tool
def perguntar_ao_banco(pergunta: str) -> dict:
    """Responde uma pergunta em português: o GPT gera o SQL, o banco executa e o GPT explica."""
    gpt = _assistente()
    sql = gpt.gerar_sql(pergunta, banco.esquema_completo())
    dados = banco.consultar(sql)
    resposta = gpt.explicar_resultado(pergunta, dados)
    return {"sql": sql, "dados": dados, "resposta": resposta}


def app_http():
    """App HTTP do MCP (Streamable HTTP) para o painel: sem sessão e com CORS só para as origens do painel."""
    origens = [o.strip() for o in os.getenv("MCP_ORIGENS_CORS", "http://localhost:5173").split(",") if o.strip()]
    cors = Middleware(CORSMiddleware, allow_origins=origens, allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
                      allow_headers=["*"], expose_headers=["mcp-session-id"])
    return mcp.http_app(path="/mcp", middleware=[cors], stateless_http=True, json_response=True)


if __name__ == "__main__":
    # stdio para clientes locais (Claude, main.py); http para o painel web: python servidor.py --http
    if "--http" in sys.argv or os.getenv("MCP_TRANSPORTE", "stdio") == "http":
        uvicorn.run(app_http(), host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
    else:
        mcp.run()
