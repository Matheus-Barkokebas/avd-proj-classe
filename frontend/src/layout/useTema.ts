import { useCallback, useEffect, useState } from "react";

export type Tema = "claro" | "escuro";
const CHAVE = "aervita.tema";

function temaInicial(): Tema {
  try {
    const salvo = localStorage.getItem(CHAVE);
    if (salvo === "claro" || salvo === "escuro") return salvo;
  } catch {
    /* armazenamento indisponível: segue o sistema */
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "escuro" : "claro";
}

/** Tema claro/escuro, aplicado em <html data-theme> e lembrado no navegador. */
export function useTema() {
  const [tema, setTema] = useState<Tema>(temaInicial);

  useEffect(() => {
    document.documentElement.dataset.theme = tema;
    try {
      localStorage.setItem(CHAVE, tema);
    } catch {
      /* sem armazenamento: o tema vale só nesta aba */
    }
  }, [tema]);

  const alternar = useCallback(() => setTema((t) => (t === "escuro" ? "claro" : "escuro")), []);
  return { tema, alternar };
}
