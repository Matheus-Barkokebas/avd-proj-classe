"""Cliente de demonstração: lista as ferramentas do servidor MCP e faz perguntas ao banco."""

import asyncio

from fastmcp import Client

from servidor import mcp


async def main():
    async with Client(mcp) as cliente:
        print("Ferramentas disponíveis:")
        for ferramenta in await cliente.list_tools():
            print(f"  - {ferramenta.name}: {ferramenta.description}")

        tabelas = await cliente.call_tool("listar_tabelas", {})
        print("\nTabelas da Gold:", tabelas.data)

        while True:
            pergunta = input("\nFaça uma pergunta sobre os dados (ou Enter para sair): ")
            if not pergunta:
                break
            resultado = await cliente.call_tool("perguntar_ao_banco", {"pergunta": pergunta})
            print("\nSQL gerado:", resultado.data["sql"])
            print("Resposta:", resultado.data["resposta"])


if __name__ == "__main__":
    asyncio.run(main())
