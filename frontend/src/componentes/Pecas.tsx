/* Peças pequenas e reaproveitáveis das telas. */

import type { ReactNode } from "react";

import type { Esquemas } from "../api/cliente";
import { SITUACOES_RIO, haQuanto, horasDesde, numero, type SituacaoRio } from "../formato";
import { Icone } from "./Icone";

export function Card({ titulo, sub, real = true, acoes, children, corpo = true }: {
  titulo: string; sub?: string; real?: boolean; acoes?: ReactNode; children: ReactNode; corpo?: boolean;
}) {
  return (
    <section className="card" aria-label={titulo}>
      <div className="card-h">
        <h3>{titulo}</h3>
        {sub && <span className="sub">{sub}</span>}
        <div className="dir">
          {acoes}
          <span className={`fonte ${real ? "real" : ""}`}>{real ? "Real" : "Simulado"}</span>
        </div>
      </div>
      {corpo ? <div className="card-b">{children}</div> : children}
    </section>
  );
}

export function Metrica({ rotulo, valor, unidade, rodape, cor }: {
  rotulo: string; valor: ReactNode; unidade?: string; rodape?: ReactNode; cor?: string;
}) {
  return (
    <div className="card metrica">
      <div className="m-top"><span className="m-label">{rotulo}</span></div>
      <div className="m-val" style={cor ? { color: cor } : undefined}>{valor}{unidade && <small>{unidade}</small>}</div>
      {rodape && <div className="m-foot">{rodape}</div>}
    </div>
  );
}

export function PillSituacao({ situacao }: { situacao: SituacaoRio }) {
  const s = SITUACOES_RIO[situacao];
  return <span className={`sev ${s.nivel}`}>{s.nome}</span>;
}

/** Régua do nível do rio contra as cotas oficiais (pré-alerta, alerta, inundação). */
export function ReguaRio({ rio }: { rio: Esquemas["Rio"] }) {
  const topo = Math.max(rio.cota_inundacao ?? 0, rio.nivel) * 1.1 || 1;
  const pct = (v: number) => `${Math.min(100, (v / topo) * 100)}%`;
  const cor = { inundacao: "var(--sev-critico)", alerta: "var(--sev-alto)", pre_alerta: "var(--sev-moderado)",
                normal: "var(--sev-baixo)", sem_cota: "var(--faint)" }[rio.situacao];
  const marcas: [number | null | undefined, string, string][] = [
    [rio.cota_pre_alerta, "pré-alerta", "var(--sev-moderado)"],
    [rio.cota_alerta, "alerta", "var(--sev-alto)"],
    [rio.cota_inundacao, "inundação", "var(--sev-critico)"],
  ];
  return (
    <div className="regua" role="img"
         aria-label={`Nível ${numero(rio.nivel)}; alerta em ${numero(rio.cota_alerta)}; inundação em ${numero(rio.cota_inundacao)}`}>
      <div className="regua-f" style={{ width: pct(rio.nivel), background: cor }} />
      {marcas.map(([v, nome, c]) => v ? (
        <div key={nome} className="regua-m" style={{ left: pct(v), background: c }} title={`${nome}: ${numero(v)}`} />
      ) : null)}
    </div>
  );
}

/** Aviso quando o dado mais recente está velho (ex.: coleta horária parada). */
export function AvisoDadoAntigo({ iso, limiteHoras, oque }: { iso?: string | null; limiteHoras: number; oque: string }) {
  if (!iso || horasDesde(iso) <= limiteHoras) return null;
  return (
    <div className="aviso" role="note">
      <Icone nome="alerta" />
      <span><b>{oque} sem atualização {haQuanto(iso)}.</b> A coleta horária do COP precisa estar agendada para estes
        números acompanharem a situação atual.</span>
    </div>
  );
}
