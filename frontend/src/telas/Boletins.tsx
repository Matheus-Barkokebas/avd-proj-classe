import { useAlagamentoRotas, useAlagamentoSerie, useArboSemanas, useChuvaAtual, useMareProximas, usePrevisao, useRios } from "../api/consultas";
import type { Esquemas } from "../api/cliente";
import { Carregando } from "../componentes/Estados";
import { Icone } from "../componentes/Icone";
import { SITUACOES_RIO, dataHora, haQuanto, horasDesde, mm, numero, semanaEpi, type SituacaoRio } from "../formato";

type Dados = {
  chuva?: Esquemas["ChuvaAtual"]; rios?: Esquemas["Rio"][]; mares?: Esquemas["Mare"][]; rotas?: Esquemas["AlagamentoRota"][];
  serie?: Esquemas["AlagamentoDia"][]; previsao?: Esquemas["PrevisaoHora"][]; arbo?: Esquemas["ArbovirosesSemana"][];
};
export type SecaoBoletim = { titulo: string; linhas: string[]; alerta?: string };
const LIMITE_DADO_ANTIGO_HORAS = 3;
const INDISPONIVEL = "Dado indisponível no momento em que o boletim foi gerado.";

/** Monta o boletim só com fatos dos dados: não há recomendação nem classificação de risco inventada. */
export function montarSecoes({ chuva, rios, mares, rotas, serie, previsao, arbo }: Dados): SecaoBoletim[] {
  const secoes: SecaoBoletim[] = [];

  secoes.push(chuva ? {
    titulo: "Chuva e estágio operacional",
    alerta: horasDesde(chuva.data_hora) > LIMITE_DADO_ANTIGO_HORAS ? `Leitura sem atualização ${haQuanto(chuva.data_hora)}.` : undefined,
    linhas: [
      `Última leitura do COP: ${dataHora(chuva.data_hora)}. Estágio: ${chuva.estagio ?? "não informado"}.`,
      `Chuva média da cidade: ${mm(chuva.chuva_media_1h_mm)} em 1 h e ${mm(chuva.chuva_media_24h_mm)} em 24 h. Maior acumulado em 24 h: ${mm(chuva.chuva_max_24h_mm)}${chuva.estacao_max_24h ? ` (${chuva.estacao_max_24h})` : ""}.`,
      `Ocorrências: ${numero(chuva.ocorrencias)}. Alagamentos: ${numero(chuva.alagamentos)}. Abrigos: ${numero(chuva.abrigos)}.`,
      ...(chuva.mes?.percentual_da_media != null ? [`Chuva no mês: ${mm(chuva.mes.chuva_acumulada_mm)}, ${numero(chuva.mes.percentual_da_media, 0)}% da média histórica do mês.`] : []),
    ],
  } : { titulo: "Chuva e estágio operacional", linhas: [INDISPONIVEL] });

  const proximas24h = previsao?.filter((p) => horasDesde(p.data_hora_prevista) >= -24) ?? [];
  const somaPrevisao = proximas24h.reduce((soma, p) => soma + (p.media_modelos_mm ?? 0), 0);
  secoes.push({ titulo: "Previsão de chuva", linhas: [
    !previsao ? INDISPONIVEL : proximas24h.length
      ? `Média dos modelos publicados pelo COP: ${mm(somaPrevisao)} nas próximas ${proximas24h.length} horas com previsão.`
      : "Sem previsão vigente publicada pelo COP.",
  ] });

  secoes.push({ titulo: "Maré", linhas: !mares ? [INDISPONIVEL] : mares.length
    ? mares.slice(0, 4).map((m) => `${m.tipo === "alta" ? "Alta" : "Baixa"}: ${dataHora(m.data_hora)}, ${numero(m.mare_m, 2)} m.`)
    : ["Sem marés na tábua para os próximos dias."] });

  secoes.push({ titulo: "Rios", linhas: !rios ? [INDISPONIVEL] : rios.map((r) =>
    `${r.rio} em ${r.estacao}: nível ${numero(r.nivel, 1)}, ${SITUACOES_RIO[r.situacao as SituacaoRio]?.nome ?? r.situacao} (alerta em ${numero(r.cota_alerta, 0)}).`) });

  const horas = serie?.reduce((soma, d) => soma + d.horas_com_alagamento, 0) ?? 0;
  secoes.push({ titulo: "Alagamentos reportados nos últimos 7 dias", linhas: !serie || !rotas ? [INDISPONIVEL] : rotas.length
    ? [`${numero(horas)} horas com alagamento reportado em ${numero(rotas.length)} rotas monitoradas.`,
       ...rotas.slice(0, 3).map((r) => `${r.rota}: ${numero(r.leituras_com_alagamento)} horas, última em ${dataHora(r.ultimo)}.`),
       "Alagamento reportado por rota, publicado pelo COP. Não é medição e não cobre a cidade inteira."]
    : ["Nenhum alagamento reportado nas rotas monitoradas."] });

  if (arbo?.length) {
    const ultima = Math.max(...arbo.map((l) => l.semana));
    const total = arbo.filter((l) => l.semana === ultima).reduce((soma, l) => soma + l.notificacoes, 0);
    secoes.push({ titulo: "Arboviroses", linhas: [`Dado mais recente: ${semanaEpi(ultima)}, com ${numero(total)} notificações de dengue, chikungunya e zika.`] });
  }
  return secoes;
}

export function boletimEmMarkdown(secoes: SecaoBoletim[], geradoEm: string) {
  const corpo = secoes.flatMap((s) => [`## ${s.titulo}`, ...(s.alerta ? [`> ${s.alerta}`] : []), ...s.linhas.map((l) => `- ${l}`), ""]);
  return [`# Boletim situacional AerVita`, `Gerado em ${geradoEm}, a partir dos dados públicos do painel.`, "", ...corpo].join("\n");
}

export function Boletins() {
  const chuva = useChuvaAtual();
  const rios = useRios();
  const mares = useMareProximas();
  const rotas = useAlagamentoRotas(7);
  const serie = useAlagamentoSerie(7);
  const previsao = usePrevisao();
  const arbo = useArboSemanas();

  const consultas = [chuva, rios, mares, rotas, serie, previsao, arbo];
  const carregando = consultas.some((c) => c.isPending);
  const geradoEm = dataHora(new Date().toISOString());
  const secoes = montarSecoes({ chuva: chuva.data, rios: rios.data, mares: mares.data, rotas: rotas.data, serie: serie.data, previsao: previsao.data, arbo: arbo.data });

  const baixar = () => {
    const url = URL.createObjectURL(new Blob([boletimEmMarkdown(secoes, geradoEm)], { type: "text/markdown;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `boletim-aervita-${new Date().toISOString().slice(0, 10)}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <div className="ph nao-imprimir">
        <div>
          <h1>Boletins</h1>
          <p>Resumo montado na hora com os dados do painel, para imprimir, salvar em PDF ou baixar.</p>
        </div>
        <div className="chips" style={{ marginBottom: 0 }}>
          <button className="btn" onClick={() => window.print()} disabled={carregando}><Icone nome="doc" />Imprimir ou salvar em PDF</button>
          <button className="btn" onClick={baixar} disabled={carregando}>Baixar em Markdown</button>
        </div>
      </div>
      <p className="muted small nao-imprimir" style={{ marginBottom: 14 }}>
        O boletim não fica salvo nem tem número, autor ou aprovação, e traz só fatos dos dados: recomendações dependem da avaliação da Defesa Civil.
      </p>

      {carregando ? <Carregando texto="Montando o boletim…" /> : (
        <article className="card boletim" aria-label="Boletim situacional">
          <header>
            <h2>Boletim situacional AerVita</h2>
            <p className="muted small">Recife · gerado em {geradoEm}, a partir dos dados públicos do COP Recife e do portal de Dados Abertos do Recife</p>
          </header>
          {secoes.map((s) => (
            <section key={s.titulo} aria-label={s.titulo}>
              <h3>{s.titulo}</h3>
              {s.alerta && <p className="boletim-alerta">{s.alerta}</p>}
              <ul>{s.linhas.map((l) => <li key={l}>{l}</li>)}</ul>
            </section>
          ))}
        </article>
      )}
    </>
  );
}
