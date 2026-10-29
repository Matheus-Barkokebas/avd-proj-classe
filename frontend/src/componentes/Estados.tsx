/* Estados de carregamento, erro e vazio — iguais em todas as telas. */

import { ErroApi } from "../api/cliente";
import { Icone } from "./Icone";
import s from "./Estados.module.css";

export function Carregando({ texto = "Carregando…" }: { texto?: string }) {
  return <div className={s.estado} role="status" aria-live="polite">{texto}</div>;
}

/** Texto para quem opera o painel; o detalhe técnico da API só aparece quando já está em português. */
export function mensagemErro(erro: unknown): string {
  if (!(erro instanceof ErroApi)) return "Erro inesperado ao carregar os dados.";
  if (erro.status === 0) return erro.message;
  if (erro.codigo === "nao_encontrado" && erro.message !== "Not Found") return erro.message;
  if (erro.status === 404) return "A API não tem esta consulta. Ela pode estar numa versão antiga.";
  if (erro.status === 503) return "O banco de dados não respondeu. Tente de novo em instantes.";
  if (erro.status >= 500) return "A API teve um erro interno ao buscar estes dados.";
  return erro.message;
}

export function ErroCarga({ erro, tentarDeNovo }: { erro: unknown; tentarDeNovo?: () => void }) {
  const mensagem = mensagemErro(erro);
  return (
    <div className={`${s.estado} ${s.erro}`} role="alert">
      <Icone nome="alerta" tamanho={20} />
      <span>{mensagem}</span>
      {tentarDeNovo && <button className="btn" onClick={tentarDeNovo}>Tentar de novo</button>}
    </div>
  );
}

export function Vazio({ texto }: { texto: string }) {
  return <div className={s.estado}>{texto}</div>;
}
