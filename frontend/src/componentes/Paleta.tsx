/* Paleta de comandos: Ctrl+K (ou Cmd+K) abre, digitar filtra, setas e Enter escolhem. */

import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { MENU } from "../layout/menu";
import { Icone, type NomeIcone } from "./Icone";

type Comando = { id: string; rotulo: string; grupo: string; icone: NomeIcone; executar: () => void };

const semAcento = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function Paleta({ aberta, aoFechar, aoAlternarTema, temaEscuro }: {
  aberta: boolean; aoFechar: () => void; aoAlternarTema: () => void; temaEscuro: boolean;
}) {
  const navegar = useNavigate();
  const [busca, setBusca] = useState("");
  const [ativo, setAtivo] = useState(0);
  const campo = useRef<HTMLInputElement>(null);

  const comandos = useMemo<Comando[]>(() => [
    ...MENU.filter((m) => !m.emBreve).map((m) => ({
      id: m.caminho, rotulo: m.titulo, grupo: "Ir para", icone: m.icone, executar: () => navegar(m.caminho),
    })),
    { id: "tema", rotulo: temaEscuro ? "Usar tema claro" : "Usar tema escuro", grupo: "Ação",
      icone: temaEscuro ? "sol" : "lua", executar: aoAlternarTema },
  ], [navegar, aoAlternarTema, temaEscuro]);

  const filtrados = comandos.filter((c) => semAcento(c.rotulo).includes(semAcento(busca.trim())));

  useEffect(() => {
    if (!aberta) return;
    setBusca("");
    setAtivo(0);
    campo.current?.focus();
  }, [aberta]);

  if (!aberta) return null;

  const executar = (comando?: Comando) => {
    if (!comando) return;
    aoFechar();
    comando.executar();
  };
  const tecla = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") aoFechar();
    else if (e.key === "ArrowDown") { e.preventDefault(); setAtivo((a) => Math.min(a + 1, filtrados.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setAtivo((a) => Math.max(a - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); executar(filtrados[ativo]); }
  };

  return (
    <div className="paleta-veu nao-imprimir" onMouseDown={(e) => { if (e.target === e.currentTarget) aoFechar(); }}>
      <div className="paleta" role="dialog" aria-modal="true" aria-label="Paleta de comandos">
        <input ref={campo} className="paleta-busca" type="search" placeholder="Ir para uma tela ou executar uma ação…" value={busca}
               aria-label="Buscar comando" onChange={(e) => { setBusca(e.target.value); setAtivo(0); }} onKeyDown={tecla} />
        <ul className="paleta-lista" role="listbox" aria-label="Comandos">
          {filtrados.map((c, i) => (
            <li key={c.id} role="option" aria-selected={i === ativo} className={i === ativo ? "ativo" : ""}
                onMouseEnter={() => setAtivo(i)} onClick={() => executar(c)}>
              <Icone nome={c.icone} /><span>{c.rotulo}</span><em>{c.grupo}</em>
            </li>
          ))}
          {!filtrados.length && <li className="paleta-vazio">Nenhum comando encontrado.</li>}
        </ul>
      </div>
    </div>
  );
}
