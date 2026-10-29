import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { respostasApi } from "../test/dadosApi";
import { renderizar, simularApi } from "../test/utilitarios";

test("menu lateral mostra as telas e marca as que ainda não têm dado real", async () => {
  simularApi(respostasApi());
  renderizar();
  const menu = screen.getByRole("complementary", { name: "Menu principal" });
  for (const nome of ["Visão geral", "Mapa", "Chuva e rios", "Arboviroses"]) {
    expect(within(menu).getByRole("link", { name: nome })).toBeInTheDocument();
  }
  expect(within(menu).getByRole("link", { name: /Ocorrências/ })).toHaveTextContent("em breve");
});

test("status da API aparece como conectado quando a API e o banco respondem", async () => {
  simularApi(respostasApi());
  renderizar();
  expect(await screen.findByText("Dados conectados")).toBeInTheDocument();
});

test("sem API: status indisponível e cada card mostra o erro com opção de tentar de novo", async () => {
  simularApi({}, { falhar: true });
  renderizar();
  expect(await screen.findByText("API indisponível")).toBeInTheDocument();
  const alertas = await screen.findAllByRole("alert");
  expect(alertas[0]).toHaveTextContent("Não foi possível falar com a API");
  expect(screen.getAllByRole("button", { name: "Tentar de novo" }).length).toBeGreaterThan(0);
});

test("navegar pelo menu troca a tela e o título", async () => {
  simularApi(respostasApi());
  renderizar();
  await userEvent.click(screen.getByRole("link", { name: /Simulador/ }));
  expect(await screen.findByRole("heading", { level: 1, name: "Simulador" })).toBeInTheDocument();
  expect(screen.getByText(/não mostra dado simulado como se fosse real/)).toBeInTheDocument();
  expect(document.title).toBe("Simulador · AerVita Console");
});

test("tema alterna entre claro e escuro e fica salvo", async () => {
  simularApi(respostasApi());
  renderizar();
  await userEvent.click(screen.getByRole("button", { name: "Usar tema escuro" }));
  expect(document.documentElement.dataset.theme).toBe("escuro");
  expect(localStorage.getItem("aervita.tema")).toBe("escuro");
});

test("rota desconhecida mostra página não encontrada", async () => {
  simularApi(respostasApi());
  renderizar("/nao-existe");
  expect(await screen.findByRole("heading", { level: 1, name: "Página não encontrada" })).toBeInTheDocument();
});
