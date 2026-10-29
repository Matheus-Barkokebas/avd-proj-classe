import { useState } from "react";

import { useChuvaAtual, useChuvaMensal, useChuvaSerie, usePrevisao, useRios, useSerieRio } from "../api/consultas";
import { Carregando, ErroCarga, Vazio } from "../componentes/Estados";
import { GraficoChuvaMensal, GraficoPrevisao, GraficoSerieChuva, GraficoSerieRio } from "../componentes/Graficos";
import { AvisoDadoAntigo, Card, PillSituacao, ReguaRio } from "../componentes/Pecas";
import { dataHora, numero, type SituacaoRio } from "../formato";

const JANELAS = [[24, "24 h"], [72, "3 dias"], [168, "7 dias"], [720, "30 dias"]] as const;

function SeletorJanela({ valor, aoMudar, rotulo }: { valor: number; aoMudar: (h: number) => void; rotulo: string }) {
  return (
    <div className="seg" role="group" aria-label={rotulo}>
      {JANELAS.map(([h, nome]) => (
        <button key={h} aria-pressed={valor === h} onClick={() => aoMudar(h)}>{nome}</button>
      ))}
    </div>
  );
}

export function ChuvaRios() {
  const [horasChuva, setHorasChuva] = useState(72);
  const [horasRio, setHorasRio] = useState(72);
  const [estacaoSel, setEstacaoSel] = useState<string | null>(null);

  const atual = useChuvaAtual();
  const serie = useChuvaSerie(horasChuva);
  const previsao = usePrevisao();
  const mensal = useChuvaMensal();
  const rios = useRios();
  const codigo = estacaoSel ?? rios.data?.[0]?.codigo_estacao ?? null;
  const serieRio = useSerieRio(codigo, horasRio);
  const rioSel = rios.data?.find((r) => r.codigo_estacao === codigo);

  return (
    <>
      <div className="ph">
        <div>
          <h1>Chuva e rios</h1>
          <p>Leituras do Centro de Operações do Recife (COP): chuva média da cidade, previsão por modelo, chuva do ano e
            nível dos rios contra as cotas oficiais.</p>
        </div>
      </div>
      <AvisoDadoAntigo iso={atual.data?.data_hora} limiteHoras={3} oque="Leituras de chuva" />

      <div className="grade">
        <div className="c8">
          <Card titulo="Chuva observada" sub="média da cidade, por hora"
                acoes={<SeletorJanela valor={horasChuva} aoMudar={setHorasChuva} rotulo="Janela da série de chuva" />}>
            {serie.isPending ? <Carregando /> : serie.error ? <ErroCarga erro={serie.error} tentarDeNovo={() => serie.refetch()} /> :
              serie.data.length ? <GraficoSerieChuva dados={serie.data} /> : <Vazio texto="Sem leituras nessa janela." />}
          </Card>
        </div>
        <div className="c4">
          <Card titulo="Agora" sub={atual.data ? dataHora(atual.data.data_hora) : undefined}>
            {atual.isPending ? <Carregando /> : atual.error ? <ErroCarga erro={atual.error} /> : (
              <dl className="kv">
                <dt>Chuva média · 1h</dt><dd>{numero(atual.data.chuva_media_1h_mm, 1)} mm</dd>
                <dt>Chuva média · 24h</dt><dd>{numero(atual.data.chuva_media_24h_mm, 1)} mm</dd>
                <dt>Maior acumulado · 24h</dt><dd>{numero(atual.data.chuva_max_24h_mm, 1)} mm</dd>
                <dt>Maré</dt><dd>{numero(atual.data.mare_m, 1)} m {atual.data.sentido_mare && `(${atual.data.sentido_mare})`}</dd>
                <dt>Estágio do COP</dt><dd>{atual.data.estagio ?? "—"}</dd>
              </dl>
            )}
          </Card>
        </div>

        <div className="c6">
          <Card titulo="Previsão de chuva" sub="hora a hora, por modelo">
            {previsao.isPending ? <Carregando /> : previsao.error ? <ErroCarga erro={previsao.error} /> :
              previsao.data.length ? <GraficoPrevisao dados={previsao.data} /> :
              <Vazio texto="Sem previsão vigente: a coleta diária do COP precisa rodar para trazer as próximas horas." />}
          </Card>
        </div>
        <div className="c6">
          <Card titulo="Chuva por mês" sub="ano atual, ano anterior e média histórica">
            {mensal.isPending ? <Carregando /> : mensal.error ? <ErroCarga erro={mensal.error} /> :
              <GraficoChuvaMensal dados={mensal.data} />}
          </Card>
        </div>

        <div className="c12">
          <Card titulo="Nível dos rios" sub="clique numa estação para ver a série"
                acoes={<SeletorJanela valor={horasRio} aoMudar={setHorasRio} rotulo="Janela da série do rio" />}>
            {rios.isPending ? <Carregando /> : rios.error ? <ErroCarga erro={rios.error} /> : (
              <>
                <ul className="estacoes" aria-label="Estações de rio">
                  {rios.data.map((r) => (
                    <li key={r.codigo_estacao}><button className="estacao"
                            aria-pressed={r.codigo_estacao === codigo} onClick={() => setEstacaoSel(r.codigo_estacao)}>
                      <div className="lr-topo"><b>{r.rio}</b><PillSituacao situacao={r.situacao as SituacaoRio} /></div>
                      <div className="small muted">{r.estacao}</div>
                      <ReguaRio rio={r} />
                      <div className="small muted num">{numero(r.nivel, 1)} · alerta {numero(r.cota_alerta, 0)} · inundação {numero(r.cota_inundacao, 0)}</div>
                    </button></li>
                  ))}
                </ul>
                {rioSel && (
                  <div style={{ marginTop: 18 }}>
                    <h4 className="titulo-serie">{rioSel.rio} — {rioSel.estacao}</h4>
                    {serieRio.isPending ? <Carregando /> : serieRio.error ? <ErroCarga erro={serieRio.error} /> :
                      serieRio.data.length ? <GraficoSerieRio pontos={serieRio.data} rio={rioSel} /> :
                      <Vazio texto="Sem leituras dessa estação na janela escolhida." />}
                  </div>
                )}
                <p className="nota">Cotas e situação informadas pelo COP. A unidade do nível ainda será confirmada com o COP
                  (os valores sugerem centímetros).</p>
              </>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
