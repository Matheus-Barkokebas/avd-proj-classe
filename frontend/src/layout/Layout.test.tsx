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
  await userEvent.click(screen.getByRole("link", { name: /Equipes de campo/ }));
  expect(await screen.findByRole("heading", { level: 1, name: "Equipes de campo" })).toBeInTheDocument();
  expect(screen.getByText(/não mostra dado simulado como se fosse real/)).toBeInTheDocument();
  expect(document.title).toBe("Equipes de campo · AerVita Console");
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


test("paleta de comandos abre com Ctrl+K, filtra sem acento e navega", async () => {
  simularApi(respostasApi());
  renderizar();
  await userEvent.keyboard("{Control>}k{/Control}");
  const paleta = await screen.findByRole("dialog", { name: "Paleta de comandos" });
  await userEvent.type(within(paleta).getByRole("searchbox"), "visao");
  expect(within(paleta).getAllByRole("option")).toHaveLength(1);
  await userEvent.clear(within(paleta).getByRole("searchbox"));
  await userEvent.type(within(paleta).getByRole("searchbox"), "boletins{Enter}");
  expect(await screen.findByRole("heading", { level: 1, name: "Boletins" })).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("a paleta não oferece telas que ainda não existem e fecha com Esc", async () => {
  simularApi(respostasApi());
  renderizar();
  await userEvent.click(screen.getByRole("button", { name: "Abrir paleta de comandos" }));
  const paleta = await screen.findByRole("dialog");
  expect(within(paleta).queryByText("Ocorrências")).not.toBeInTheDocument();
  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
