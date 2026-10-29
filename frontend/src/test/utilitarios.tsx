import { QueryClient } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { App } from "../App";

/** Respostas da API por rota (sem a query string). Rota ausente -> 404 no formato da API. */
export type RespostasFalsas = Record<string, unknown | ((url: URL) => unknown)>;

export function simularApi(respostas: RespostasFalsas, { falhar = false } = {}) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (entrada) => {
    if (falhar) throw new TypeError("Failed to fetch");
    const url = new URL(String(entrada));
    const resposta = respostas[url.pathname];
    if (resposta === undefined) {
      return new Response(JSON.stringify({ erro: "nao_encontrado", detalhe: url.pathname }), { status: 404 });
    }
    const corpo = typeof resposta === "function" ? (resposta as (u: URL) => unknown)(url) : resposta;
    return new Response(JSON.stringify(corpo), { status: 200, headers: { "Content-Type": "application/json" } });
  });
}

export function renderizar(rota = "/") {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={[rota]}>
      <App cliente={cliente} />
    </MemoryRouter>,
  );
}
