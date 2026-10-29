/* Páginas provisórias: telas desta release ainda em construção, telas sem dado real e 404. */

import { Link, useLocation } from "react-router-dom";

import { Icone } from "../componentes/Icone";
import { itemDaRota } from "../layout/menu";

function Aviso({ titulo, texto, children }: { titulo: string; texto: string; children?: React.ReactNode }) {
  return (
    <>
      <div className="ph"><div><h1>{titulo}</h1><p>{texto}</p></div></div>
      <div className="card"><div className="card-b" style={{ textAlign: "center", padding: 40 }}>{children}</div></div>
    </>
  );
}

/** Tela do protótipo que depende de dado que ainda não existe (ocorrências, equipes, simulador, boletins). */
export function EmBreve() {
  const item = itemDaRota(useLocation().pathname);
  return (
    <Aviso titulo={item?.titulo ?? ""}
           texto="Esta tela depende de dados que ainda não existem no pipeline. Ela não mostra dado simulado como se fosse real.">
      <p className="muted small" style={{ marginBottom: 14 }}>
        A versão de demonstração (com dados simulados) está no protótipo: <code>frontend/prototipo/v3-aervita-console.html</code>.
      </p>
      <Link to="/" className="btn"><Icone nome="painel" />Voltar para a visão geral</Link>
    </Aviso>
  );
}

export function NaoEncontrada() {
  return (
    <Aviso titulo="Página não encontrada" texto="O endereço não corresponde a nenhuma tela.">
      <Link to="/" className="btn"><Icone nome="painel" />Ir para a visão geral</Link>
    </Aviso>
  );
}
