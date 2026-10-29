/* Gráficos (Recharts). Cores fixas: variáveis CSS não valem em atributos SVG,
   e estes tons funcionam nos temas claro e escuro. */

import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

import type { Esquemas } from "../api/cliente";
import { AGRAVOS, hora, nomeMes, numero, semanaEpi, type Agravo } from "../formato";

export const CORES = {
  chuva: "#3b6fe0", chuva24h: "#0f8a7e", previsao: "#7c5cd6", media: "#98a2b3",
  gfs: "#3b6fe0", ecmwf: "#0f8a7e", icon: "#d4a20b", wrf: "#e5534b",
  preAlerta: "#d4a20b", alerta: "#ea6a0c", inundacao: "#dc2626",
};
const EIXO = { fill: "#8a94a7", fontSize: 11 };
const GRADE = "rgba(138,148,167,.25)";
const DICA = {
  contentStyle: { background: "#0c111c", border: "none", borderRadius: 8, color: "#e6e9ef", fontSize: 12 },
  labelStyle: { color: "#e6e9ef", fontWeight: 600 }, itemStyle: { color: "#e6e9ef" },
};
const formatarMm = (v: unknown) => `${numero(Number(v), 1)} mm`;

function Caixa({ altura = 260, rotulo, children }: { altura?: number; rotulo: string; children: React.ReactElement }) {
  return (
    <div role="img" aria-label={rotulo} style={{ width: "100%", height: altura }}>
      <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>
    </div>
  );
}

export function GraficoSerieChuva({ dados }: { dados: Esquemas["PontoSerieChuva"][] }) {
  return (
    <Caixa rotulo="Chuva por hora e acumulado de 24 horas">
      <ComposedChart data={dados} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
        <CartesianGrid stroke={GRADE} vertical={false} />
        <XAxis dataKey="data_hora" tickFormatter={hora} tick={EIXO} minTickGap={40} />
        <YAxis tick={EIXO} />
        <Tooltip {...DICA} labelFormatter={(v) => hora(String(v))} formatter={formatarMm} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="chuva_media_1h_mm" name="Média da cidade na hora" fill={CORES.chuva} radius={[3, 3, 0, 0]} />
        <Line dataKey="chuva_media_24h_mm" name="Acumulado de 24h" stroke={CORES.chuva24h} strokeWidth={2} dot={false} />
      </ComposedChart>
    </Caixa>
  );
}

export function GraficoPrevisao({ dados }: { dados: Esquemas["PrevisaoHora"][] }) {
  const modelos = [["gfs_mm", "GFS", CORES.gfs], ["ecmwf_mm", "ECMWF", CORES.ecmwf], ["icon_mm", "ICON", CORES.icon],
                   ["wrf_mm", "WRF", CORES.wrf]] as const;
  return (
    <Caixa rotulo="Previsão de chuva por modelo">
      <LineChart data={dados} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
        <CartesianGrid stroke={GRADE} vertical={false} />
        <XAxis dataKey="data_hora_prevista" tickFormatter={hora} tick={EIXO} minTickGap={40} />
        <YAxis tick={EIXO} />
        <Tooltip {...DICA} labelFormatter={(v) => hora(String(v))} formatter={formatarMm} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {modelos.map(([chave, nome, cor]) => (
          <Line key={chave} dataKey={chave} name={nome} stroke={cor} strokeWidth={1.5} dot={false} connectNulls />
        ))}
        <Line dataKey="media_modelos_mm" name="Média dos modelos" stroke={CORES.previsao} strokeWidth={2.5}
              strokeDasharray="5 4" dot={false} connectNulls />
      </LineChart>
    </Caixa>
  );
}

export function GraficoChuvaMensal({ dados }: { dados: Esquemas["ChuvaMensal"] }) {
  const linhas = dados.meses.map((m) => ({ ...m, rotulo: nomeMes(m.mes) }));
  return (
    <Caixa rotulo={`Chuva por mês em ${dados.ano} comparada à média histórica`}>
      <ComposedChart data={linhas} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
        <CartesianGrid stroke={GRADE} vertical={false} />
        <XAxis dataKey="rotulo" tick={EIXO} />
        <YAxis tick={EIXO} />
        <Tooltip {...DICA} formatter={formatarMm} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="chuva_ano_atual_mm" name={String(dados.ano)} fill={CORES.chuva} radius={[3, 3, 0, 0]} />
        <Bar dataKey="chuva_ano_anterior_mm" name={String(dados.ano - 1)} fill="#a9b8d6" radius={[3, 3, 0, 0]} />
        <Line dataKey="media_historica_mm" name="Média histórica" stroke={CORES.alerta} strokeWidth={2} dot={{ r: 3 }} />
      </ComposedChart>
    </Caixa>
  );
}

export function GraficoSerieRio({ pontos, rio }: { pontos: Esquemas["PontoSerieRio"][]; rio: Esquemas["Rio"] }) {
  const cotas = [[rio.cota_pre_alerta, "pré-alerta", CORES.preAlerta], [rio.cota_alerta, "alerta", CORES.alerta],
                 [rio.cota_inundacao, "inundação", CORES.inundacao]] as const;
  const maximo = Math.max(...pontos.map((p) => p.nivel), rio.cota_inundacao ?? 0) * 1.08;
  return (
    <Caixa rotulo={`Nível do ${rio.rio} em ${rio.estacao} contra as cotas`}>
      <LineChart data={pontos} margin={{ top: 8, right: 8, left: -4, bottom: 0 }}>
        <CartesianGrid stroke={GRADE} vertical={false} />
        <XAxis dataKey="data_hora" tickFormatter={hora} tick={EIXO} minTickGap={40} />
        <YAxis tick={EIXO} domain={[0, Math.ceil(maximo)]} />
        <Tooltip {...DICA} labelFormatter={(v) => hora(String(v))} formatter={(v) => numero(Number(v), 1)} />
        {cotas.map(([valor, nome, cor]) => valor ? (
          <ReferenceLine key={nome} y={valor} stroke={cor} strokeDasharray="4 4"
                         label={{ value: nome, position: "insideTopRight", fill: cor, fontSize: 11 }} />
        ) : null)}
        <Line dataKey="nivel" name="Nível" stroke={CORES.chuva} strokeWidth={2} dot={pontos.length < 30} />
      </LineChart>
    </Caixa>
  );
}

export function GraficoArboSemanas({ linhas, ativos, modo }: {
  linhas: Esquemas["ArbovirosesSemana"][]; ativos: Agravo[]; modo: "notificacoes" | "nao_descartadas";
}) {
  const porSemana = new Map<number, Record<string, number>>();
  for (const l of linhas) {
    const atual = porSemana.get(l.semana) ?? { semana: l.semana };
    atual[l.agravo] = l[modo];
    porSemana.set(l.semana, atual);
  }
  const dados = [...porSemana.values()].sort((a, b) => a.semana - b.semana);
  return (
    <Caixa altura={280} rotulo="Notificações de arboviroses por semana epidemiológica">
      <LineChart data={dados} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
        <CartesianGrid stroke={GRADE} vertical={false} />
        <XAxis dataKey="semana" tickFormatter={(v) => semanaEpi(Number(v))} tick={EIXO} minTickGap={30} />
        <YAxis tick={EIXO} />
        <Tooltip {...DICA} labelFormatter={(v) => semanaEpi(Number(v))} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {ativos.map((a) => (
          <Line key={a} dataKey={a} name={AGRAVOS[a].nome} stroke={AGRAVOS[a].cor} strokeWidth={2} dot={false} />
        ))}
      </LineChart>
    </Caixa>
  );
}

export function GraficoColunas({ dados, rotulo, cor = "#e5534b" }: {
  dados: { rotulo: string; valor: number }[]; rotulo: string; cor?: string;
}) {
  return (
    <Caixa altura={180} rotulo={rotulo}>
      <BarChart data={dados} margin={{ top: 8, right: 4, left: -18, bottom: 0 }}>
        <CartesianGrid stroke={GRADE} vertical={false} />
        <XAxis dataKey="rotulo" tick={EIXO} interval={0} angle={-30} textAnchor="end" height={42} />
        <YAxis tick={EIXO} />
        <Tooltip {...DICA} formatter={(v) => numero(Number(v))} />
        <Bar dataKey="valor" name="Notificações" fill={cor} radius={[3, 3, 0, 0]} />
      </BarChart>
    </Caixa>
  );
}
