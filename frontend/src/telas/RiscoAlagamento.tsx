import { useState } from "react";

import { useAlagamentoRotas, useAlagamentoSerie, useModeloAlagamento, usePrevisoesAlagamento } from "../api/consultas";
import { CardMares } from "../componentes/CardMares";
import { Carregando, ErroCarga, Vazio } from "../componentes/Estados";
import { GraficoAlagamentoDia, GraficoPrevistoObservado } from "../componentes/Graficos";
import { Card, Metrica } from "../componentes/Pecas";
import { NOME_VARIAVEL, dataHora, numero, percentual } from "../formato";
import { baixarCsv } from "../csv";

const SELO_MODELO = "Modelo experimental";
const PERIODOS = [[30, "30 dias"], [90, "90 dias"], [365, "1 ano"]] as const;

export function RiscoAlagamento() {
  const [dias, setDias] = useState<number>(90);
  const rotas = useAlagamentoRotas(dias);
  const serie = useAlagamentoSerie(dias);
  const modelo = useModeloAlagamento();
  const previsoes = usePrevisoesAlagamento();

  const horasComAlagamento = serie.data?.reduce((soma, d) => soma + d.horas_com_alagamento, 0);
  const maisAfetada = rotas.data?.[0];
  const m = modelo.data;

  return (
    <>
      <div className="ph">
        <div>
          <h1>Risco de alagamento</h1>
          <p>Alagamentos reportados nas rotas monitoradas pelo COP e como o modelo de previsão se saiu no histórico.</p>
        </div>
      </div>

      <div className="aviso" role="note">
        <span><b>A previsão ainda não roda em tempo real.</b> O modelo foi avaliado em horas passadas, com a chuva do INMET, que é
          publicada com atraso. O alagamento é o reportado por rota, não uma medição: rotas sem movimento podem alagar sem registro.</span>
      </div>

      <div className="metricas">
        {serie.error ? <ErroCarga erro={serie.error} tentarDeNovo={() => serie.refetch()} /> : serie.isPending ? <Carregando /> : (
          <Metrica rotulo={`Horas com alagamento · ${dias} dias`} valor={numero(horasComAlagamento)}
                   rodape={`${numero(serie.data.length)} dias com registro`} />
        )}
        {rotas.error ? <ErroCarga erro={rotas.error} /> : rotas.isPending ? <Carregando /> : (
          <Metrica rotulo="Rota mais afetada" valor={maisAfetada ? numero(maisAfetada.leituras_com_alagamento) : "—"}
                   rodape={maisAfetada ? maisAfetada.rota : "nenhum alagamento no período"} />
        )}
        {modelo.error ? <ErroCarga erro={modelo.error} /> : modelo.isPending ? <Carregando /> : (
          <>
            <Metrica rotulo={`Acurácia do modelo · ${m!.horizonte_horas} h à frente`} valor={percentual(m!.acuracia)}
                     rodape={`contra ${percentual(m!.linha_de_base)} do chute na classe mais comum`} />
            <Metrica rotulo="Alagamentos que o modelo encontra" valor={percentual(m!.recall)}
                     rodape={`${numero(m!.verdadeiros_positivos)} de ${numero(m!.verdadeiros_positivos + m!.falsos_negativos)} nas horas de teste`} />
          </>
        )}
      </div>

      <div className="grade">
        <div className="c8">
          <Card titulo="Alagamentos reportados por dia" sub="horas com alagamento em alguma rota" acoes={
            <div className="seg" role="group" aria-label="Período dos alagamentos">
              {PERIODOS.map(([valor, rotulo]) => (
                <button key={valor} aria-pressed={dias === valor} onClick={() => setDias(valor)}>{rotulo}</button>
              ))}
            </div>}>
            {serie.isPending ? <Carregando /> : serie.error ? <ErroCarga erro={serie.error} /> :
              serie.data.length ? <GraficoAlagamentoDia dados={serie.data} /> : <Vazio texto="Nenhum alagamento reportado no período." />}
          </Card>
        </div>
        <div className="c4"><CardMares /></div>

        <div className="c8">
          <Card titulo="Previsto e observado" sub="horas de teste por semana" selo={SELO_MODELO}>
            {previsoes.isPending ? <Carregando /> : previsoes.error ? <ErroCarga erro={previsoes.error} /> :
              previsoes.data.length ? <GraficoPrevistoObservado dados={previsoes.data} /> : <Vazio texto="Sem previsões no banco." />}
          </Card>
        </div>
        <div className="c4">
          <Card titulo="Como o modelo se saiu" selo={SELO_MODELO}>
            {modelo.isPending ? <Carregando /> : modelo.error ? <ErroCarga erro={modelo.error} /> : (
              <>
                <dl className="kv">
                  <dt>Quando prevê alagamento, acerta</dt><dd>{percentual(m!.precisao)}</dd>
                  <dt>Alarmes falsos no teste</dt><dd>{numero(m!.falsos_positivos)}</dd>
                  <dt>Alagamentos perdidos no teste</dt><dd>{numero(m!.falsos_negativos)}</dd>
                  <dt>Treino no passado, teste no futuro</dt>
                  <dd>{percentual(m!.tempo_acuracia)} (chute: {percentual(m!.tempo_linha_de_base)})</dd>
                  <dt>Período dos dados</dt><dd>{dataHora(m!.inicio).slice(0, 10)} a {dataHora(m!.fim).slice(0, 10)}</dd>
                </dl>
                <h5 className="secao-painel">O que mais pesa na previsão</h5>
                <dl className="kv">
                  {m!.importancia.slice(0, 4).map((v) => [
                    <dt key={`${v.variavel}-nome`}>{NOME_VARIAVEL[v.variavel] ?? v.variavel}</dt>,
                    <dd key={`${v.variavel}-valor`}>{percentual(v.importancia)}</dd>,
                  ])}
                </dl>
                <p className="muted small" style={{ marginTop: 12 }}>Nestes dados, a maré não melhorou a previsão de forma mensurável.
                  Isso não prova que ela não importe: o período é curto e tem poucas horas de maré alta com chuva forte.</p>
              </>
            )}
          </Card>
        </div>

        <div className="c12">
          <Card titulo="Rotas com mais alagamentos reportados" sub={`últimos ${dias} dias`} corpo={false} acoes={
            <button className="btn" disabled={!rotas.data?.length} onClick={() => baixarCsv(`alagamentos-por-rota-${dias}-dias`, rotas.data ?? [], [
              { titulo: "Rota", valor: (r) => r.rota }, { titulo: "Horas com alagamento", valor: (r) => r.leituras_com_alagamento },
              { titulo: "Alertas", valor: (r) => r.alertas }, { titulo: "Último registro", valor: (r) => dataHora(r.ultimo) },
            ])}>Exportar CSV</button>}>
            {rotas.isPending ? <Carregando /> : rotas.error ? <ErroCarga erro={rotas.error} tentarDeNovo={() => rotas.refetch()} /> :
             !rotas.data.length ? <Vazio texto="Nenhum alagamento reportado no período." /> : (
              <div className="tabela-rolagem">
                <table className="tabela">
                  <thead><tr><th>#</th><th>Rota</th><th className="r">Horas com alagamento</th><th className="r">Alertas</th><th className="r">Último registro</th></tr></thead>
                  <tbody>
                    {rotas.data.slice(0, 15).map((r, i) => (
                      <tr key={r.rota}>
                        <td className="num muted">{i + 1}</td><td><b>{r.rota}</b></td>
                        <td className="r num">{numero(r.leituras_com_alagamento)}</td><td className="r num">{numero(r.alertas)}</td>
                        <td className="r num">{dataHora(r.ultimo)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
