import { Link } from "react-router-dom";

import type { Esquemas } from "../api/cliente";
import { useArboSemanas, useAtualizacao, useChuvaAtual, useChuvaSerie, useRios } from "../api/consultas";
import { Carregando, ErroCarga } from "../componentes/Estados";
import { GraficoColunas, GraficoSerieChuva } from "../componentes/Graficos";
import { AvisoDadoAntigo, Card, Metrica, PillSituacao, ReguaRio } from "../componentes/Pecas";
import { SITUACOES_RIO, dataHora, mm, nomeMes, numero, semanaEpi, type SituacaoRio } from "../formato";

const NOMES_TABELA: Record<string, string> = {
  cop_indicadores: "Chuva e maré (COP, horária)",
  cop_rios: "Nível dos rios (COP, horária)",
  cop_previsao_chuva: "Previsão de chuva (COP)",
  cop_chuva_mensal: "Chuva mensal (COP)",
  epidemiologia: "Arboviroses",
  cop_areas_alagaveis: "Áreas alagáveis",
  cop_pontos_alagamento: "Pontos de alagamento",
};
const GRAVIDADE: SituacaoRio[] = ["inundacao", "alerta", "pre_alerta", "normal", "sem_cota"];
const COR_SITUACAO = { inundacao: "var(--sev-critico)", alerta: "var(--sev-alto)", pre_alerta: "var(--sev-moderado)",
                       normal: "var(--sev-baixo)", sem_cota: "var(--muted)" };

/** O COP usa o texto "Não Informado" quando não há estação: mostra como vazio. */
const estacao = (nome?: string | null) => (!nome || /n[aã]o informado/i.test(nome) ? null : nome);

function MetricasChuva({ chuva }: { chuva: Esquemas["ChuvaAtual"] }) {
  const mes = chuva.mes;
  const pct = mes?.percentual_da_media;
  const maxima = estacao(chuva.estacao_max_24h);
  return (
    <>
      <Metrica rotulo="Chuva média · 24h" valor={numero(chuva.chuva_media_24h_mm, 1)} unidade="mm"
               rodape={<>Maior acumulado: <b>{mm(chuva.chuva_max_24h_mm)}</b>{maxima && <> em {maxima}</>}</>} />
      <Metrica rotulo={mes ? `Chuva em ${nomeMes(mes.mes)}/${mes.ano}` : "Chuva no mês"}
               valor={numero(mes?.chuva_acumulada_mm, 1)} unidade="mm"
               rodape={pct == null ? "sem média histórica" : (
                 <><span className={`delta ${pct > 100 ? "up" : "down"}`}>{numero(pct, 0)}%</span>{" "}
                   da média histórica ({mm(mes?.media_historica_mm, 0)})</>
               )} />
    </>
  );
}

function MetricaRios({ rios }: { rios: Esquemas["Rio"][] }) {
  const pior = GRAVIDADE.find((s) => rios.some((r) => r.situacao === s)) ?? "sem_cota";
  const fora = rios.filter((r) => r.situacao !== "normal" && r.situacao !== "sem_cota").length;
  return (
    <Metrica rotulo="Rios monitorados" valor={SITUACOES_RIO[pior].nome} cor={COR_SITUACAO[pior]}
             rodape={`${rios.length} estações · ${fora ? `${fora} acima de alguma cota` : "todas abaixo das cotas"}`} />
  );
}

export function VisaoGeral() {
  const chuva = useChuvaAtual();
  const serie = useChuvaSerie(72);
  const rios = useRios();
  const arbo = useArboSemanas();
  const atualizacao = useAtualizacao();

  const ultimasSemanas = (() => {
    if (!arbo.data) return [];
    const total = new Map<number, number>();
    for (const l of arbo.data) total.set(l.semana, (total.get(l.semana) ?? 0) + l.notificacoes);
    return [...total.entries()].sort((a, b) => a[0] - b[0]).slice(-12)
      .map(([se, valor]) => ({ rotulo: semanaEpi(se), valor }));
  })();

  return (
    <>
      <div className="ph">
        <div>
          <h1>Visão geral</h1>
          <p>Situação consolidada do Recife a partir dos dados reais do pipeline: chuva, rios, estágio operacional e arboviroses.</p>
        </div>
      </div>

      <AvisoDadoAntigo iso={chuva.data?.data_hora} limiteHoras={3} oque="Dados de chuva e maré" />

      {chuva.error ? <ErroCarga erro={chuva.error} tentarDeNovo={() => chuva.refetch()} /> : (
        <div className="metricas">
          {chuva.data ? <MetricasChuva chuva={chuva.data} /> : <><Carregando /><Carregando /></>}
          {rios.data ? <MetricaRios rios={rios.data} /> : <Carregando />}
          {chuva.data ? (
            <Metrica rotulo="Estágio do COP" valor={chuva.data.estagio ?? "—"}
                     cor={chuva.data.estagio === "NORMALIDADE" ? "var(--sev-baixo)" : "var(--sev-alto)"}
                     rodape={<>{numero(chuva.data.ocorrencias)} ocorrências · {numero(chuva.data.alagamentos)} alagamentos ·
                       {" "}{numero(chuva.data.abrigos)} abrigos · {dataHora(chuva.data.data_hora)}</>} />
          ) : <Carregando />}
        </div>
      )}

      <div className="grade">
        <div className="c8 pilha">
          <Card titulo="Chuva nas últimas 72 horas" sub="média da cidade (COP)"
                acoes={<Link className="btn" to="/chuva-rios">Detalhar</Link>}>
            {serie.isPending ? <Carregando /> : serie.error ? <ErroCarga erro={serie.error} /> :
              serie.data.length ? <GraficoSerieChuva dados={serie.data} /> :
              <p className="muted small">Sem leituras nas últimas 72 horas.</p>}
          </Card>
          <Card titulo="Arboviroses" sub="notificações nas últimas 12 semanas com dado (2025)"
                acoes={<Link className="btn" to="/arboviroses">Detalhar</Link>}>
            {arbo.isPending ? <Carregando /> : arbo.error ? <ErroCarga erro={arbo.error} /> :
              <GraficoColunas dados={ultimasSemanas} rotulo="Notificações de arboviroses por semana" />}
          </Card>
        </div>
        <div className="c4 pilha">
          <Card titulo="Rios" sub="nível vs. cotas oficiais">
            {rios.isPending ? <Carregando /> : rios.error ? <ErroCarga erro={rios.error} /> : (
              <ul className="lista-rios">
                {rios.data.map((r) => (
                  <li key={r.codigo_estacao}>
                    <div className="lr-topo"><b>{r.rio}</b><PillSituacao situacao={r.situacao as SituacaoRio} /></div>
                    <div className="small muted">{r.estacao}</div>
                    <ReguaRio rio={r} />
                    <div className="small muted num">nível {numero(r.nivel, 1)} · alerta {numero(r.cota_alerta, 0)}
                      {r.percentual_da_cota_alerta != null && ` · ${numero(r.percentual_da_cota_alerta, 0)}% da cota de alerta`}</div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card titulo="Atualização dos dados" sub="última carga no banco" corpo={false}>
            {atualizacao.isPending ? <Carregando /> : atualizacao.error ? <ErroCarga erro={atualizacao.error} /> : (
              <table className="tabela">
                <thead><tr><th>Dado</th><th>Última carga</th><th className="r">Linhas</th></tr></thead>
                <tbody>
                  {atualizacao.data.tabelas.map((t) => (
                    <tr key={t.tabela}>
                      <td>{NOMES_TABELA[t.tabela] ?? t.tabela}</td>
                      <td className="num">{dataHora(t.carregado_em)}</td>
                      <td className="num r">{numero(t.linhas)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
