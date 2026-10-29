import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { respostasApi } from "../test/dadosApi";
import { renderizar, simularApi } from "../test/utilitarios";
import { classe, limitesQuantis } from "./Mapa";

// O jsdom não tem WebGL: o MapLibre vira um dublê que guarda os eventos e deixa disparar o clique.
const mapas: { disparar: (evento: string, camada: string, dados: unknown) => void }[] = [];
vi.mock("maplibre-gl", () => {
  class Map {
    private handlers: Record<string, (e: unknown) => void> = {};
    constructor() {
      mapas.push(this as never);
      setTimeout(() => this.handlers["load"]?.({}), 0);
    }
    on(evento: string, camadaOuCb: string | ((e: unknown) => void), cb?: (e: unknown) => void) {
      if (typeof camadaOuCb === "function") this.handlers[evento] = camadaOuCb;
      else this.handlers[`${evento}:${camadaOuCb}`] = cb!;
    }
    disparar(evento: string, camada: string, dados: unknown) { this.handlers[`${evento}:${camada}`]?.(dados); }
    addControl() {} addSource() {} addLayer() {} setLayoutProperty() {} setFilter() {} remove() {}
    getSource() { return { setData: () => {} }; }
    getCanvas() { return { style: {} }; }
  }
  class NavigationControl {}
  return { Map, NavigationControl, setWorkerUrl: () => {} };
});

// ------------------------------------------------------------ visão geral
test("visão geral mostra chuva, mês contra a média, rios e estágio do COP", async () => {
  simularApi(respostasApi());
  renderizar("/");
  const chuva = await screen.findByText("Chuva média · 24h");
  expect(chuva.closest(".metrica")).toHaveTextContent("6,2mm");
  expect(chuva.closest(".metrica")).toHaveTextContent("Areias");
  expect(screen.getByText("Chuva em out/2026").closest(".metrica")).toHaveTextContent("35% da média histórica");
  const rios = await screen.findByText("Rios monitorados");
  expect(rios.closest(".metrica")).toHaveTextContent("Alerta");  // pior situação entre as estações
  expect(rios.closest(".metrica")).toHaveTextContent("1 acima de alguma cota");
  expect(screen.getByText("Estágio do COP").closest(".metrica")).toHaveTextContent("NORMALIDADE");
  expect(screen.queryByRole("note")).not.toBeInTheDocument();  // dado recente: sem aviso
});

test("visão geral avisa quando a chuva está sem atualização", async () => {
  simularApi(respostasApi({ chuvaHorasAtras: 20 }));
  renderizar("/");
  expect(await screen.findByRole("note")).toHaveTextContent("Dados de chuva e maré sem atualização há 20 h");
});

test("o texto 'Não Informado' do COP não aparece como nome de estação", async () => {
  const respostas = respostasApi();
  (respostas["/v1/chuva/atual"] as Record<string, unknown>).estacao_max_24h = "Não Informado";
  simularApi(respostas);
  renderizar("/");
  const chuva = await screen.findByText("Chuva média · 24h");
  expect(chuva.closest(".metrica")).not.toHaveTextContent("Não Informado");
});

// ------------------------------------------------------------ chuva e rios
test("chuva e rios: escolher outra estação troca a série e a janela vai para a API", async () => {
  const fetch = simularApi(respostasApi());
  renderizar("/chuva-rios");
  expect(await screen.findByRole("heading", { name: "RIO JABOATÃO — VILA NATAL" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /LIMOEIRO/ }));
  expect(await screen.findByRole("heading", { name: "RIO CAPIBARIBE — LIMOEIRO" })).toBeInTheDocument();
  await userEvent.click(within(screen.getByRole("group", { name: "Janela da série de chuva" })).getByRole("button", { name: "7 dias" }));
  expect(fetch.mock.calls.some(([url]) => String(url).includes("/v1/chuva/serie?horas=168"))).toBe(true);
  // o navegador não pode servir resposta guardada: o painel mostraria dado já substituído no banco
  expect(fetch.mock.calls.every(([, opcoes]) => (opcoes as RequestInit).cache === "no-cache")).toBe(true);
});

test("chuva e rios: quadro 'Agora' com chuva, maré e estágio", async () => {
  simularApi(respostasApi());
  renderizar("/chuva-rios");
  const agora = await screen.findByRole("region", { name: "Agora" });
  expect(await within(agora).findByText("1,1 m (subindo)")).toBeInTheDocument();
  expect(within(agora).getByText("NORMALIDADE")).toBeInTheDocument();
});

// ------------------------------------------------------------ arboviroses
test("arboviroses: números gerais, pico e descartadas", async () => {
  simularApi(respostasApi());
  renderizar("/arboviroses");
  const total = await screen.findByText("Notificações");
  expect(total.closest(".metrica")).toHaveTextContent("759");
  expect(screen.getByText("Semana de pico").closest(".metrica")).toHaveTextContent("SE 33/25");
  // 759 notificações, 475 não descartadas -> 284 descartadas = 37%
  expect(screen.getByText("Descartadas após investigação").closest(".metrica")).toHaveTextContent("37%");
  expect(screen.getByText("Bairros com notificação").closest(".metrica")).toHaveTextContent("2de 3");
});

test("arboviroses: tabela filtra sem acento e ordena pela coluna", async () => {
  simularApi(respostasApi());
  renderizar("/arboviroses");
  const tabela = await screen.findByRole("table");
  expect(within(tabela).getAllByRole("row")[1]).toHaveTextContent("Cohab");
  await userEvent.click(within(tabela).getByRole("button", { name: "Bairro" }));
  expect(within(tabela).getAllByRole("row")[1]).toHaveTextContent("Cohab");
  expect(within(tabela).getAllByRole("row")[2]).toHaveTextContent("Pina");
  await userEvent.type(screen.getByRole("searchbox", { name: "Filtrar bairro ou distrito" }), "ds vi");
  expect(within(tabela).getAllByRole("row")).toHaveLength(3);  // cabeçalho + DS VI e DS VII
  expect(screen.getByText(/21 notificações têm um nome de bairro/)).toBeInTheDocument();
});

// ------------------------------------------------------------ mapa
test("mapa: clicar num bairro abre o painel com distrito, arboviroses e pontos de alagamento", async () => {
  simularApi(respostasApi());
  mapas.length = 0;
  renderizar("/mapa");
  await screen.findByRole("region", { name: "Mapa do Recife" });
  await vi.waitFor(() => expect(mapas.length).toBe(1));
  mapas[0].disparar("click", "bairros-fill", { features: [{ properties: { chave_bairro: "PINA" } }] });
  const painel = await screen.findByRole("region", { name: "Bairro" });
  expect(await within(painel).findByText("Pina")).toBeInTheDocument();
  expect(within(painel).getByText("DS VI")).toBeInTheDocument();
  expect(within(painel).getByText("2º de 3")).toBeInTheDocument();
  expect(within(painel).getByText(/RUA DO PINA/)).toBeInTheDocument();
});

test("mapa: legenda muda com a camada", async () => {
  simularApi(respostasApi());
  renderizar("/mapa");
  const legenda = await screen.findByLabelText("Legenda");
  expect(legenda).toHaveTextContent("DS 1");
  await userEvent.click(screen.getByRole("button", { name: "Arboviroses" }));
  expect(screen.getByLabelText("Legenda")).toHaveTextContent("mais de");
  expect(screen.getByRole("combobox", { name: "Agravo" })).toBeInTheDocument();
});

test("classes por quantis do mapa", () => {
  const limites = limitesQuantis([0, 1, 2, 3, 4, 5, 6, 7, 8, 100]);
  expect(limites).toEqual([1, 3, 5, 7, 8]);
  expect([0, 1, 2, 7, 8, 9, 100].map((v) => classe(v, limites))).toEqual([0, 0, 1, 3, 4, 5, 5]);
});
