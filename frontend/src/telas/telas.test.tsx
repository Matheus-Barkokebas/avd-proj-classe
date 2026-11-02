import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { porSemana } from "../componentes/Graficos";
import { gerarCsv } from "../csv";
import { boletimEmMarkdown, montarSecoes } from "./Boletins";
import { FONTES } from "./FontesDados";
import { ajustarChuva } from "./Simulador";
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

// ------------------------------------------------------------ risco de alagamento
test("risco de alagamento: mostra a acurácia junto do chute e o recall, sem esconder os limites", async () => {
  simularApi(respostasApi());
  renderizar("/risco-alagamento");
  const acuracia = await screen.findByText(/Acurácia do modelo/);
  expect(acuracia.closest(".metrica")).toHaveTextContent("82,5%");
  expect(acuracia.closest(".metrica")).toHaveTextContent("contra 69,7% do chute");
  expect(screen.getByText("Alagamentos que o modelo encontra").closest(".metrica")).toHaveTextContent("98 de 147");
  expect(screen.getByRole("note")).toHaveTextContent("ainda não roda em tempo real");
  expect(await screen.findAllByText("Modelo experimental")).toHaveLength(2);
  expect(await screen.findByText(/a maré não melhorou a previsão/)).toBeInTheDocument();
});

test("risco de alagamento: ranking das rotas e troca de período chegam à API", async () => {
  const fetch = simularApi(respostasApi());
  renderizar("/risco-alagamento");
  const tabela = await screen.findByRole("table");
  expect(within(tabela).getAllByRole("row")[1]).toHaveTextContent("AV. NORTE >> CENTRO");
  await userEvent.click(within(screen.getByRole("group", { name: "Período dos alagamentos" })).getByRole("button", { name: "1 ano" }));
  expect(fetch.mock.calls.some(([url]) => String(url).includes("/v1/alagamento/rotas?dias=365"))).toBe(true);
  expect(fetch.mock.calls.some(([url]) => String(url).includes("/v1/alagamento/serie?dias=365"))).toBe(true);
});

test("sem modelo treinado, a aba mostra o resto dos dados e o erro só nos cards do modelo", async () => {
  const respostas = respostasApi();
  delete respostas["/v1/alagamento/modelo"];
  simularApi(respostas);
  renderizar("/risco-alagamento");
  expect(await screen.findByRole("table")).toBeInTheDocument();
  expect((await screen.findAllByRole("alert")).length).toBeGreaterThan(0);
});

test("próximas marés aparecem na visão geral e em chuva e rios, dizendo se é alta ou baixa", async () => {
  simularApi(respostasApi());
  const { unmount } = renderizar("/");
  const card = await screen.findByRole("region", { name: "Próximas marés" });
  expect(await within(card).findByText("2,10 m")).toBeInTheDocument();
  expect(within(card).getByText("Alta")).toBeInTheDocument();
  unmount();
  renderizar("/chuva-rios");
  expect(await screen.findByRole("region", { name: "Próximas marés" })).toBeInTheDocument();
});

test("previsto e observado somam as horas de teste por semana", () => {
  const semanas = porSemana(respostasApi()["/v1/alagamento/previsoes"] as never);
  expect(semanas).toEqual([
    { semana: "2026-05-24", previsto: 1, observado: 2 },
    { semana: "2026-05-31", previsto: 1, observado: 0 },
  ]);
});

// ------------------------------------------------------------ simulador, boletins, fontes e CSV
test("simulador: acumulados continuam coerentes ao mexer numa barra", () => {
  const base = { chuva_1h_mm: 2, chuva_3h_mm: 5, chuva_6h_mm: 8, chuva_12h_mm: 12, chuva_24h_mm: 18, chuva_72h_mm: 30, chuva_168h_mm: 50, mare_m: 1, mare_max_futura_m: 2, mare_subindo: 1 };
  const subiu = ajustarChuva(base, "chuva_6h_mm", 40);
  expect([subiu.chuva_3h_mm, subiu.chuva_12h_mm, subiu.chuva_24h_mm, subiu.chuva_168h_mm]).toEqual([5, 40, 40, 50]);
  const desceu = ajustarChuva(base, "chuva_12h_mm", 3);
  expect([desceu.chuva_1h_mm, desceu.chuva_3h_mm, desceu.chuva_6h_mm, desceu.chuva_24h_mm]).toEqual([2, 3, 3, 18]);
});

test("simulador: mostra resultado, regras e aviso de que não é previsão", async () => {
  const fetch = simularApi(respostasApi());
  renderizar("/simulador");
  const resultado = await screen.findByRole("region", { name: "Resultado" });
  expect(await within(resultado).findByText("83%")).toBeInTheDocument();
  expect(within(resultado).getByText(/Chuva em 12 h: 12,0 acima de 2,7/)).toBeInTheDocument();
  expect(screen.getByRole("note")).toHaveTextContent("não uma previsão");
  await userEvent.click(screen.getByRole("button", { name: "Chuva forte" }));
  await vi.waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).includes("chuva_12h_mm=60"))).toBe(true));
});

test("simulador: avisa quando o cenário sai do que o modelo viu", async () => {
  simularApi(respostasApi());
  renderizar("/simulador");
  await screen.findByRole("region", { name: "Resultado" });
  fireEvent.change(screen.getByRole("slider", { name: /Chuva em 12 h/ }), { target: { value: "150" } });
  expect(await screen.findByText("Cenário fora do que o modelo viu.")).toBeInTheDocument();
});

test("boletim traz os fatos dos dados, sem recomendação", async () => {
  simularApi(respostasApi());
  renderizar("/boletins");
  const boletim = await screen.findByRole("article", { name: "Boletim situacional" });
  expect(boletim).toHaveTextContent("Estágio: NORMALIDADE");
  expect(boletim).toHaveTextContent("AV. NORTE >> CENTRO: 120 horas");
  expect(boletim).toHaveTextContent("Não é medição");
  expect(boletim).not.toHaveTextContent(/recomenda/i);
});

test("boletim: dado antigo é sinalizado e falta de dado é dita, sem inventar", () => {
  const antigo = respostasApi({ chuvaHorasAtras: 20 })["/v1/chuva/atual"] as never;
  const secoes = montarSecoes({ chuva: antigo });
  expect(secoes[0].alerta).toMatch(/sem atualização há 20 h/);
  expect(secoes.find((s) => s.titulo === "Rios")?.linhas).toEqual(["Dado indisponível no momento em que o boletim foi gerado."]);
  expect(boletimEmMarkdown(secoes, "agora")).toContain("## Chuva e estágio operacional");
});

test("fontes de dados: mostra órgão, última carga e a ressalva do alaga", async () => {
  simularApi(respostasApi());
  renderizar("/fontes");
  const linha = (await screen.findByText("Alagamento por rota")).closest("tr")!;
  expect(linha).toHaveTextContent("COP Recife");
  expect(linha).toHaveTextContent("Waze");
  expect(FONTES.every((f) => f.link.startsWith("https://"))).toBe(true);
});

test("CSV usa ponto e vírgula e vírgula decimal, trata aspas e não deixa virar fórmula", () => {
  const csv = gerarCsv([{ nome: 'AV. "X"; Y', valor: 1.5 }, { nome: "=HYPERLINK(1)", valor: null }], [
    { titulo: "Nome", valor: (l: { nome: string }) => l.nome }, { titulo: "Valor", valor: (l: { valor: number | null }) => l.valor },
  ]);
  expect(csv).toBe('Nome;Valor\r\n"AV. ""X""; Y";1,5\r\n\'=HYPERLINK(1);');
});

test("mapa: rotas aparecem com legenda e painel ao ligar a camada", async () => {
  simularApi(respostasApi());
  mapas.length = 0;
  renderizar("/mapa");
  await screen.findByRole("region", { name: "Mapa do Recife" });
  await userEvent.click(screen.getByRole("checkbox", { name: "Rotas com alagamento reportado" }));
  expect(screen.getByLabelText("Legenda")).toHaveTextContent("rota com mais horas de alagamento");
  await vi.waitFor(() => expect(mapas.length).toBe(1));
  mapas[0].disparar("click", "rotas-fill", { features: [{ properties: { rota: "AV. NORTE >> CENTRO" } }] });
  const painel = await screen.findByRole("region", { name: "Rota" });
  expect(await within(painel).findByText("AV. NORTE >> CENTRO")).toBeInTheDocument();
  expect(within(painel).getByText("120")).toBeInTheDocument();
});
