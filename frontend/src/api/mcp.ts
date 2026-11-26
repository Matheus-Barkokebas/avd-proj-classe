/* Cliente MCP do painel: fala com o mcp-servidor pelo transporte Streamable HTTP, com o SDK oficial. */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

export const URL_MCP = (import.meta.env.VITE_MCP_URL ?? "http://localhost:8001/mcp").replace(/\/$/, "");

export type Ferramenta = { nome: string; descricao: string };
export type Linha = Record<string, string | number | boolean | null>;
export type RespostaPergunta = { sql: string; dados: Linha[]; resposta: string };

let conexao: Promise<Client> | null = null;

function conectar(): Promise<Client> {
  conexao ??= (async () => {
    const cliente = new Client({ name: "aervita-painel", version: "1.0.0" });
    await cliente.connect(new StreamableHTTPClientTransport(new URL(URL_MCP)));
    return cliente;
  })().catch((erro) => {
    conexao = null;
    throw erro;
  });
  return conexao;
}

export async function listarFerramentas(): Promise<Ferramenta[]> {
  const { tools } = await (await conectar()).listTools();
  return tools.map((t) => ({ nome: t.name, descricao: t.description ?? "" }));
}

/** Chama uma ferramenta e devolve o resultado estruturado; erro da ferramenta vira exceção com a mensagem dela. */
export async function chamarFerramenta<T>(nome: string, argumentos: Record<string, unknown> = {}): Promise<T> {
  const resultado = await (await conectar()).callTool({ name: nome, arguments: argumentos });
  if (resultado.isError) {
    const texto = (resultado.content as { type: string; text?: string }[]).find((c) => c.type === "text")?.text;
    throw new Error((texto ?? "Erro na ferramenta").replace(/^Error calling tool '[^']+': /, ""));
  }
  const estruturado = resultado.structuredContent as Record<string, unknown> | undefined;
  return (estruturado && "result" in estruturado ? estruturado.result : estruturado) as T;
}
