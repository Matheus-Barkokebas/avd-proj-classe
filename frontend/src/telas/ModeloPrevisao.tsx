import { Link } from "react-router-dom";

import { useModeloAlagamento } from "../api/consultas";
import { Carregando, ErroCarga } from "../componentes/Estados";
import { Card, Metrica } from "../componentes/Pecas";
import { NOME_VARIAVEL, dataHora, numero, percentual } from "../formato";

const SELO_MODELO = "Modelo experimental";

/** Escala laranja da matriz de confusão do treino (clara para poucas horas, escura para muitas). */
const CLARO = [255, 245, 235];
const ESCURO = [127, 39, 4];

export function corDaCelula(valor: number, maximo: number) {
  const t = maximo > 0 ? valor / maximo : 0;
  const [r, g, b] = CLARO.map((c, i) => Math.round(c + (ESCURO[i] - c) * t));
  return { fundo: `rgb(${r}, ${g}, ${b})`, texto: t > 0.5 ? "#ffffff" : "#7f2704" };
}

// Tentativas registradas em pipeline/aervita/predicao/resultados/RESULTADOS.md (mesmas 2.100 horas, linha de base 69,3%).
const EXPERIMENTOS = [
  ["Só chuva de 24 h", 0.794, 0.799, 0.824],
  ["Todas as janelas de chuva", 0.832, 0.854, 0.862],
  ["Só maré", 0.685, 0.716, 0.69],
  ["Árvore sem limite de profundidade", 0.786, 1, 0.821],
  ["Chuva e maré, parâmetros por validação cruzada (escolhida)", 0.839, 0.861, 0.857],
] as const;

const FONTES = [
  ["Chuva por hora", "INMET, estação automática A301 (Recife)", "Instituto Nacional de Meteorologia, governo federal",
   "Publicada em arquivo anual, com atraso de semanas."],
  ["Tábua de maré", "COP Recife", "Centro de Operações da Prefeitura do Recife",
   "Publicada com antecedência; o banco tem a tábua até o fim de 2026."],
  ["Alagamento por rota", "COP Recife, campo alaga", "Centro de Operações da Prefeitura do Recife",
   "É alagamento reportado nas 35 rotas monitoradas, não medido. Parece vir de alertas do Waze (a confirmar com o COP)."],
] as const;

export function ModeloPrevisao() {
  const modelo = useModeloAlagamento();
  const m = modelo.data;

  return (
    <>
      <div className="ph">
        <div>
          <h1>Modelo de previsão</h1>
          <p>O que o modelo de alagamento faz, como foi treinado, de onde vêm os dados e quanto se pode confiar nele.</p>
        </div>
      </div>

      {modelo.isPending ? <Carregando /> : modelo.error ? <ErroCarga erro={modelo.error} tentarDeNovo={() => modelo.refetch()} /> : (
        <>
          <div className="metricas">
            <Metrica rotulo={`Acurácia no teste · ${m!.horizonte_horas} h à frente`} valor={percentual(m!.acuracia)}
                     rodape={`contra ${percentual(m!.linha_de_base)} do chute na classe mais comum`} />
            <Metrica rotulo="Quando prevê alagamento, acerta" valor={percentual(m!.precisao)}
                     rodape={`${numero(m!.falsos_positivos)} alarmes falsos no teste`} />
            <Metrica rotulo="Alagamentos que encontra" valor={percentual(m!.recall)}
                     rodape={`${numero(m!.verdadeiros_positivos)} de ${numero(m!.verdadeiros_positivos + m!.falsos_negativos)} nas horas de teste`} />
            <Metrica rotulo="Treinado em" valor={dataHora(m!.treinado_em).slice(0, 10)}
                     rodape={`${numero(m!.horas)} horas de ${dataHora(m!.inicio).slice(0, 10)} a ${dataHora(m!.fim).slice(0, 10)}`} />
          </div>

          <div className="grade">
            <div className="c6">
              <Card titulo="O que o modelo faz" selo={SELO_MODELO}>
                <p className="small" style={{ marginTop: 0 }}>
                  Responde a uma pergunta: <b>daqui a {m!.horizonte_horas} horas, alguma rota monitorada pelo COP terá alagamento
                  reportado?</b> A resposta é sim ou não, para a cidade inteira, junto com a parte das horas de treino parecidas que
                  tiveram alagamento.
                </p>
                <ul className="lista-pontos">
                  <li>Olha a chuva acumulada em 1, 3, 6, 12 e 24 horas, 3 dias e 7 dias.</li>
                  <li>Olha a maré na hora, se ela está subindo e a máxima das próximas 6 horas.</li>
                  <li>É uma árvore de decisão: uma sequência de regras do tipo "chuva em 12 h acima de 2,7 mm".</li>
                  <li>Não prevê por bairro nem por rota, e não mede o tamanho do alagamento.</li>
                </ul>
                <p className="muted small" style={{ marginTop: 12 }}>
                  Veja a <Link to="/risco-alagamento">última previsão com dados reais</Link> ou teste cenários no <Link to="/simulador">simulador</Link>.
                </p>
              </Card>
            </div>

            <div className="c6">
              <Card titulo="Como foi treinado" sub="pipeline/aervita/predicao/train.py">
                <ol className="lista-pontos" style={{ listStyle: "decimal", paddingLeft: 18, display: "block" }}>
                  {[
                    `Base com uma linha por hora: ${numero(m!.horas)} horas com resposta conhecida, de ${dataHora(m!.inicio).slice(0, 10)} a ${dataHora(m!.fim).slice(0, 10)}.`,
                    "Regra contra vazamento: cada hora usa só o que se sabia naquela hora. Testes automáticos garantem isso.",
                    `Divisão fixa: 80% para treino e 20% para teste (${numero(m!.horas_teste)} horas), sorteio com semente 42 e mesma proporção de alagamentos.`,
                    `Escolha dos parâmetros por validação cruzada em 5 partes, só no treino: ${percentual(m!.validacao_cruzada)} de acerto.`,
                    "Avaliação final nas horas de teste, que o modelo nunca viu.",
                    "As regras da árvore vão para o banco (camada Gold) e a API aplica as mesmas regras no painel.",
                  ].map((passo) => <li key={passo} style={{ display: "list-item", marginBottom: 6 }}>{passo}</li>)}
                </ol>
              </Card>
            </div>

            <div className="c6">
              <Card titulo="Matriz de confusão" sub={`${numero(m!.horas_teste)} horas de teste`} selo={SELO_MODELO}>
                <MatrizConfusao vp={m!.verdadeiros_positivos} fp={m!.falsos_positivos} fn={m!.falsos_negativos} vn={m!.verdadeiros_negativos} />
                <p className="muted small" style={{ marginTop: 12 }}>
                  Quanto mais escuro, mais horas. A diagonal são os acertos. O número a acompanhar é o de alagamentos perdidos:
                  o modelo deixa passar cerca de 1 em cada 3.
                </p>
              </Card>
            </div>

            <div className="c6">
              <Card titulo="Contra o chute" sub="o chute é sempre responder a classe mais comum">
                <BarraComparacao rotulo="Divisão aleatória (exigida no exercício)" modelo={m!.acuracia} chute={m!.linha_de_base} />
                <BarraComparacao rotulo="Treino no passado, teste no futuro" modelo={m!.tempo_acuracia} chute={m!.tempo_linha_de_base} />
                <p className="muted small" style={{ marginTop: 12 }}>
                  Na divisão aleatória, horas vizinhas caem no treino e no teste, o que deixa o resultado otimista. Testando no futuro,
                  o ganho sobre o chute é menor, e a acurácia balanceada fica em {percentual(m!.tempo_balanceada)}.
                </p>
                <h5 className="secao-painel">O que mais pesa na previsão</h5>
                <dl className="kv">
                  {m!.importancia.map((v) => [
                    <dt key={`${v.variavel}-nome`}>{NOME_VARIAVEL[v.variavel] ?? v.variavel}</dt>,
                    <dd key={`${v.variavel}-valor`}>{percentual(v.importancia)}</dd>,
                  ])}
                </dl>
              </Card>
            </div>

            <div className="c12">
              <Card titulo="Experimentos antes da versão final" sub="mesmas 2.100 horas · a escolha olha só a validação cruzada" corpo={false}>
                <div className="tabela-rolagem">
                  <table className="tabela">
                    <thead><tr><th>Tentativa</th><th className="r">Validação cruzada</th><th className="r">Treino</th><th className="r">Teste</th></tr></thead>
                    <tbody>
                      {EXPERIMENTOS.map(([nome, validacao, treino, teste]) => (
                        <tr key={nome}>
                          <td>{nome.includes("escolhida") ? <b>{nome}</b> : nome}</td>
                          <td className="r num">{percentual(validacao)}</td><td className="r num">{percentual(treino)}</td>
                          <td className="r num">{percentual(teste)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>

            <div className="c12">
              <Card titulo="De onde vêm os dados" sub="só fontes públicas de governo" corpo={false}>
                <div className="tabela-rolagem">
                  <table className="tabela">
                    <thead><tr><th>Dado</th><th>Fonte</th><th>Órgão</th><th>Limite</th></tr></thead>
                    <tbody>
                      {FONTES.map(([dado, fonte, orgao, limite]) => (
                        <tr key={dado}><td><b>{dado}</b></td><td>{fonte}</td><td>{orgao}</td><td className="muted">{limite}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>

            <div className="c12">
              <Card titulo="Quanto confiar">
                <ul className="lista-pontos">
                  <li>Todo dado passa por um contrato antes de entrar no banco: o que não está no formato esperado é rejeitado e registrado.</li>
                  <li>O resultado vale para um período de cerca de 4 meses de um único ano, sem o pico de chuvas de abril e maio.</li>
                  <li>Nestes dados, a maré não melhorou a previsão de forma mensurável. Isso não prova que ela não importe: faltam meses com maré alta e chuva forte.</li>
                  <li>O painel avisa quando um valor está fora do que o modelo viu no treino. Nesses casos, a resposta não merece confiança.</li>
                </ul>
                <p className="muted small" style={{ marginTop: 12 }}>
                  Horário da última carga de cada fonte em <Link to="/fontes">Fontes de dados</Link>.
                </p>
              </Card>
            </div>
          </div>
        </>
      )}
    </>
  );
}

function MatrizConfusao({ vp, fp, fn, vn }: { vp: number; fp: number; fn: number; vn: number }) {
  const maximo = Math.max(vp, fp, fn, vn);
  const celulas = [
    ["Sem alagamento", [[vn, "acertou"], [fp, "alarme falso"]]],
    ["Com alagamento", [[fn, "alagamento perdido"], [vp, "acertou"]]],
  ] as const;
  return (
    <div role="table" aria-label="Matriz de confusão" style={{ display: "grid", gridTemplateColumns: "auto 1fr 1fr", gap: 4, fontSize: 12.5 }}>
      <div role="row" style={{ display: "contents" }}>
        <span className="muted small" role="columnheader">Real \ Previsto</span>
        <span className="muted small" role="columnheader" style={{ textAlign: "center" }}>Sem alagamento</span>
        <span className="muted small" role="columnheader" style={{ textAlign: "center" }}>Com alagamento</span>
      </div>
      {celulas.map(([real, linha]) => (
        <div role="row" key={real} style={{ display: "contents" }}>
          <span className="muted small" role="rowheader" style={{ alignSelf: "center", paddingRight: 8 }}>{real}</span>
          {linha.map(([valor, rotulo]) => {
            const cor = corDaCelula(valor, maximo);
            return (
              <div role="cell" key={rotulo + valor} style={{ background: cor.fundo, color: cor.texto, borderRadius: 6, padding: "18px 8px", textAlign: "center" }}>
                <div style={{ fontSize: 24, fontWeight: 600 }}>{numero(valor)}</div>
                <div>{rotulo}</div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

function BarraComparacao({ rotulo, modelo, chute }: { rotulo: string; modelo: number; chute: number }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div className="small" style={{ marginBottom: 6 }}><b>{rotulo}</b></div>
      {[["Modelo", modelo, "#ea6a0c"], ["Chute", chute, "var(--faint)"]].map(([nome, valor, cor]) => (
        <div key={nome as string} style={{ display: "grid", gridTemplateColumns: "56px 1fr 52px", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span className="muted small">{nome}</span>
          <div style={{ background: "var(--surface-3)", borderRadius: 4, height: 10 }}>
            <div style={{ width: `${(valor as number) * 100}%`, background: cor as string, borderRadius: 4, height: 10 }} />
          </div>
          <span className="small num" style={{ textAlign: "right" }}>{percentual(valor as number)}</span>
        </div>
      ))}
    </div>
  );
}
