import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useSaude } from "../api/consultas";
import { Icone } from "../componentes/Icone";
import s from "./Layout.module.css";
import { MENU, itemDaRota } from "./menu";
import { useTema } from "./useTema";

function StatusApi() {
  const { data, isError, isPending } = useSaude();
  const online = !isError && data?.banco === "ok";
  const texto = isPending ? "Conectando…" : online ? "Dados conectados" : "API indisponível";
  return (
    <div className={`${s.status} ${isPending ? "" : online ? s.online : s.offline}`} role="status"
         title={online ? "API e banco respondendo" : "A API ou o banco não respondem"}>
      <i className={s.pt} /><span>{texto}</span>
    </div>
  );
}

export function Layout() {
  const { tema, alternar } = useTema();
  const { pathname } = useLocation();
  const [recolhida, setRecolhida] = useState(false);
  const [menuAberto, setMenuAberto] = useState(false);
  const atual = itemDaRota(pathname);

  useEffect(() => {
    setMenuAberto(false);
    document.title = `${atual?.titulo ?? "AerVita"} · AerVita Console`;
  }, [pathname, atual]);

  let grupo = "";
  return (
    <div className={`${s.app} ${recolhida ? s.recolhida : ""} ${menuAberto ? s.menuAberto : ""}`}>
      <aside className={s.sidebar} aria-label="Menu principal">
        <div className={s.marca}>
          <div className={s.logo}><Icone nome="marca" tamanho={17} traco={2.1} /></div>
          <div className={s.nomeMarca}>AerVita <span>Console</span></div>
        </div>
        <nav className={s.nav}>
          {MENU.map((item) => {
            const novoGrupo = item.grupo !== grupo;
            grupo = item.grupo;
            return (
              <div key={item.caminho}>
                {novoGrupo && <div className={s.grupo}>{item.grupo}</div>}
                <NavLink to={item.caminho} end title={item.titulo}
                         className={({ isActive }) => `${s.item} ${isActive ? s.ativo : ""} ${item.emBreve ? s.emBreve : ""}`}>
                  <Icone nome={item.icone} tamanho={18} />
                  <span>{item.titulo}</span>
                  {item.emBreve && <em className={s.etiqueta}>em breve</em>}
                </NavLink>
              </div>
            );
          })}
        </nav>
        <div className={s.rodape}>
          <button className={s.recolherBtn} onClick={() => setRecolhida((r) => !r)}>
            <Icone nome="recolher" /><span>Recolher menu</span>
          </button>
        </div>
      </aside>

      <div className={s.main}>
        <header className={s.topbar}>
          <button className={`${s.ib} ${s.hamb}`} aria-label="Abrir menu" onClick={() => setMenuAberto((m) => !m)}>
            <Icone nome="menu" tamanho={18} />
          </button>
          <div className={s.crumbs}>
            <span className={s.grupoCrumb}>{atual?.grupo ?? "AerVita"}</span>
            <span className={s.grupoCrumb}><Icone nome="dir" tamanho={14} /></span>
            <b>{atual?.titulo ?? "Página não encontrada"}</b>
          </div>
          <div className={s.esp} />
          <StatusApi />
          <button className={s.ib} onClick={alternar} aria-label={tema === "escuro" ? "Usar tema claro" : "Usar tema escuro"}>
            <Icone nome={tema === "escuro" ? "sol" : "lua"} tamanho={18} />
          </button>
        </header>
        <main className={s.conteudo}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
