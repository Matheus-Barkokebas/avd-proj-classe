import { ErroApi } from "../api/cliente";
import { mensagemErro } from "./Estados";

test("mensagens de erro em português para cada situação", () => {
  expect(mensagemErro(new ErroApi(0, "sem_conexao", "Não foi possível falar com a API. Ela está rodando?")))
    .toMatch(/Não foi possível falar com a API/);
  expect(mensagemErro(new ErroApi(404, "nao_encontrado", "Estação 999 não encontrada"))).toBe("Estação 999 não encontrada");
  expect(mensagemErro(new ErroApi(404, "nao_encontrado", "Not Found"))).toMatch(/versão antiga/);
  expect(mensagemErro(new ErroApi(503, "indisponivel", "pool timeout"))).toMatch(/banco de dados não respondeu/);
  expect(mensagemErro(new ErroApi(500, "erro"))).toMatch(/erro interno/);
  expect(mensagemErro(new Error("x"))).toBe("Erro inesperado ao carregar os dados.");
});
