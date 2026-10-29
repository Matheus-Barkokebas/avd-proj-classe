/* Formatação em português do Brasil, num lugar só. */

const FUSO = "America/Recife";

export const numero = (v: number | null | undefined, casas = 0) =>
  v === null || v === undefined ? "—" : v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

export const mm = (v: number | null | undefined, casas = 1) => (v === null || v === undefined ? "—" : `${numero(v, casas)} mm`);

export const dataHora = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short", timeZone: FUSO }) : "—";

export const hora = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", timeZone: FUSO });

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
export const nomeMes = (mes: number) => MESES[mes - 1] ?? String(mes);

/** 202533 -> "SE 33/25" */
export const semanaEpi = (se: number) => `SE ${String(se % 100).padStart(2, "0")}/${String(Math.floor(se / 100)).slice(2)}`;

/** Horas desde um instante ISO (para avisar dado parado). */
export const horasDesde = (iso: string, agora = Date.now()) => (agora - new Date(iso).getTime()) / 3_600_000;

/** "há 3 h", "há 2 dias" */
export function haQuanto(iso: string, agora = Date.now()) {
  const h = horasDesde(iso, agora);
  if (h < 1) return `há ${Math.max(1, Math.round(h * 60))} min`;
  if (h < 48) return `há ${Math.round(h)} h`;
  return `há ${Math.round(h / 24)} dias`;
}

export const AGRAVOS = {
  dengue: { nome: "Dengue", cor: "#e5534b" },
  chikungunya: { nome: "Chikungunya", cor: "#3b6fe0" },
  zika: { nome: "Zika", cor: "#0f8a7e" },
} as const;
export type Agravo = keyof typeof AGRAVOS;

export const SITUACOES_RIO = {
  inundacao: { nome: "Inundação", nivel: "critico" },
  alerta: { nome: "Alerta", nivel: "alto" },
  pre_alerta: { nome: "Pré-alerta", nivel: "moderado" },
  normal: { nome: "Normal", nivel: "baixo" },
  sem_cota: { nome: "Sem cota", nivel: "neutro" },
} as const;
export type SituacaoRio = keyof typeof SITUACOES_RIO;
