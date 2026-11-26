# `mcp-servidor/` — servidor MCP do AerVita

Servidor [MCP](https://modelcontextprotocol.io) (Model Context Protocol) feito com
[FastMCP](https://gofastmcp.com): expõe a **camada Gold** do Neon como ferramentas que uma IA pode chamar.
Segue o modelo da aula (`aula-mcp`), adaptado ao AerVita.

```text
Claude / main.py ──(stdio)──┐
                            ├──► servidor.py (FastMCP) ──► banco.py ──► Neon, schema gold (só leitura)
painel web ──(HTTP /mcp)────┘                └──► assistente.py ──► GPT (gera o SQL e explica o resultado)
```

O painel tem a tela **Assistente de dados** (`/assistente`), que é um cliente MCP feito com o SDK oficial
e fala com este servidor pelo transporte Streamable HTTP.

| Arquivo | Papel |
|---|---|
| `servidor.py` | cria o servidor e registra as ferramentas (`@mcp.tool`) |
| `banco.py` | classe `BancoNeon`: conexão somente leitura, só aceita um único `SELECT`, devolve até 200 linhas |
| `assistente.py` | classe `AssistenteGPT`: pergunta em português → SQL, e dados → resposta curta |
| `main.py` | cliente de demonstração: lista as ferramentas e faz perguntas em loop |
| `tests/` | ferramentas testadas com banco e GPT simulados, sem rede |

## Ferramentas

| Ferramenta | O que faz | Precisa do GPT |
|---|---|---|
| `listar_tabelas` | tabelas e views da Gold | não |
| `descrever_tabela` | colunas e tipos de uma tabela | não |
| `executar_select` | roda um `SELECT` (ex.: `SELECT * FROM gold.modelo_execucao`) | não |
| `perguntar_ao_banco` | pergunta em português: o GPT gera o SQL, o banco executa e o GPT explica | sim |

## Diferenças em relação ao modelo da aula

- Lê o schema `gold` (o que a API e o modelo usam), não o `public`.
- Usa o usuário **só leitura** `aervita_api`, o mesmo da API, além da sessão `read_only`.
- Recusa qualquer comando que não seja um único `SELECT`, inclusive o SQL gerado pelo GPT.
- Datas e decimais do PostgreSQL viram JSON; o resultado é limitado a 200 linhas e cada consulta a 5 segundos.
- Além do stdio, roda em HTTP (`--http`) para o painel, sem sessão e com CORS só para as origens do painel.
- O GPT recebe o contexto do projeto (fontes e fuso) e só é criado quando `perguntar_ao_banco` é usado.
- Variáveis com os nomes do projeto (`NEON_DATABASE_URL`, `OPENAI_API_KEY`) e driver `psycopg` 3, como na API.

## Como rodar

De dentro desta pasta:

```bash
python -m venv .venv && .venv\Scripts\activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                                 # NEON_DATABASE_URL do aervita_api e OPENAI_API_KEY, só aqui

python main.py            # demonstração no terminal
python servidor.py        # servidor MCP (stdio), para um cliente se conectar
python servidor.py --http # servidor MCP em http://localhost:8001/mcp, para a tela Assistente do painel
pytest                    # testes sem rede
```

Para usar no Claude Code, registre o servidor (caminhos absolutos):

```bash
claude mcp add aervita -- <pasta>/mcp-servidor/.venv/Scripts/python.exe <pasta>/mcp-servidor/servidor.py
```

## Publicar para o painel no ar (Render)

Novo **Web Service** no Render apontando para este repositório:

| Campo | Valor |
|---|---|
| Root Directory | `mcp-servidor` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python servidor.py --http` |
| Variáveis | `NEON_DATABASE_URL` (do `aervita_api`), `OPENAI_API_KEY`, `MCP_ORIGENS_CORS=https://avd-proj-classe.vercel.app` |

Na Vercel, defina `VITE_MCP_URL=https://<servico>.onrender.com/mcp` e publique de novo o painel.
Como o painel não tem login, qualquer pessoa com o link pode fazer perguntas, e cada uma gasta créditos da OpenAI:
acompanhe o uso no painel da OpenAI.

Segredos só no `.env` desta pasta (ignorado pelo Git) e nas variáveis do Render.
