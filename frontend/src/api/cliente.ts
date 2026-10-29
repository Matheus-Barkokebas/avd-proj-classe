/* Cliente HTTP da API. Os tipos vêm de esquema.d.ts, gerado do api/openapi.json
   (`npm run gerar:tipos`): se a API mudar um campo, o TypeScript acusa aqui. */

import type { components, paths } from "./esquema";

export type Esquemas = components["schemas"];

export const URL_API = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

/** Erro no formato único da API ({"erro", "detalhe"}), mais o status HTTP. */
export class ErroApi extends Error {
  constructor(public status: number, public codigo: string, detalhe?: string | null) {
    super(detalhe || codigo);
  }
}

type RotaGet = { [R in keyof paths]: paths[R] extends { get: unknown } ? R : never }[keyof paths];
type RespostaDe<R extends RotaGet> = paths[R] extends {
  get: { responses: { 200: { content: { "application/json": infer T } } } };
} ? T : never;

/** GET tipado: `buscar("/v1/rios")` já devolve o tipo certo da resposta. */
export async function buscar<R extends RotaGet>(
  rota: R, parametros?: Record<string, string | number | undefined>, sinal?: AbortSignal,
): Promise<RespostaDe<R>> {
  const consulta = new URLSearchParams();
  for (const [chave, valor] of Object.entries(parametros ?? {})) {
    if (valor !== undefined) consulta.set(chave, String(valor));
  }
  const url = `${URL_API}${rota}${consulta.size ? `?${consulta}` : ""}`;
  let resposta: Response;
  try {
    // "no-cache": o navegador sempre consulta a API. O Cache-Control da API serve a proxies/CDN;
    // aqui quem controla quando buscar de novo é o TanStack Query, senão o painel podia mostrar dado já substituído no banco.
    resposta = await fetch(url, { signal: sinal, cache: "no-cache", headers: { Accept: "application/json" } });
  } catch (erro) {
    if ((erro as Error).name === "AbortError") throw erro;
    throw new ErroApi(0, "sem_conexao", "Não foi possível falar com a API. Ela está rodando?");
  }
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => ({}));
    throw new ErroApi(resposta.status, corpo.erro ?? "erro", corpo.detalhe);
  }
  return resposta.json();
}
