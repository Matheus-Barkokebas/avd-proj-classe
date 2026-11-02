/* Exportação em CSV no formato que o Excel em português abre direto: `;` entre colunas e vírgula decimal. */

export type ColunaCsv<T> = { titulo: string; valor: (linha: T) => string | number | null | undefined };

function celula(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined) return "";
  if (typeof valor === "number") return String(valor).replace(".", ",");
  // Texto começando com = + - @ viraria fórmula ao abrir na planilha.
  const texto = /^[=+\-@\t\r]/.test(valor) ? `'${valor}` : valor;
  return /[;"\n\r]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto;
}

export function gerarCsv<T>(linhas: T[], colunas: ColunaCsv<T>[]): string {
  const cabecalho = colunas.map((c) => celula(c.titulo)).join(";");
  const corpo = linhas.map((l) => colunas.map((c) => celula(c.valor(l))).join(";"));
  return [cabecalho, ...corpo].join("\r\n");
}

export function baixarCsv<T>(nome: string, linhas: T[], colunas: ColunaCsv<T>[]) {
  // O BOM faz o Excel reconhecer os acentos.
  const url = URL.createObjectURL(new Blob(["﻿" + gerarCsv(linhas, colunas)], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `${nome}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
