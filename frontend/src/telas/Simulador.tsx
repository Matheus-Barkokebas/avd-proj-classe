import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useSimulacao } from "../api/consultas";
import { Carregando, ErroCarga } from "../componentes/Estados";
import { Card } from "../componentes/Pecas";
import { NOME_VARIAVEL, numero, percentual } from "../formato";

export const JANELAS = [
  ["chuva_1h_mm", 80], ["chuva_3h_mm", 120], ["chuva_6h_mm", 150], ["chuva_12h_mm", 200],
  ["chuva_24h_mm", 250], ["chuva_72h_mm", 350], ["chuva_168h_mm", 500],
] as const;
type Janela = (typeof JANELAS)[number][0];
export type Cenario = Record<Janela, number> & { mare_m: number; mare_max_futura_m: number; mare_subindo: number };

const MARE_MEDIA = { mare_m: 1.2, mare_max_futura_m: 1.9, mare_subindo: 1 };
// Exemplos para começar: não são classes oficiais de chuva.
const EXEMPLOS: { nome: string; cenario: Cenario }[] = [
  { nome: "Sem chuva", cenario: { chuva_1h_mm: 0, chuva_3h_mm: 0, chuva_6h_mm: 0, chuva_12h_mm: 0, chuva_24h_mm: 0, chuva_72h_mm: 2, chuva_168h_mm: 5, ...MARE_MEDIA } },
  { nome: "Chuva fraca", cenario: { chuva_1h_mm: 0.5, chuva_3h_mm: 1, chuva_6h_mm: 1.5, chuva_12h_mm: 2, chuva_24h_mm: 4, chuva_72h_mm: 10, chuva_168h_mm: 20, ...MARE_MEDIA } },
  { nome: "Chuva moderada", cenario: { chuva_1h_mm: 2, chuva_3h_mm: 5, chuva_6h_mm: 8, chuva_12h_mm: 12, chuva_24h_mm: 18, chuva_72h_mm: 30, chuva_168h_mm: 50, ...MARE_MEDIA } },
  { nome: "Chuva forte", cenario: { chuva_1h_mm: 10, chuva_3h_mm: 25, chuva_6h_mm: 40, chuva_12h_mm: 60, chuva_24h_mm: 70, chuva_72h_mm: 90, chuva_168h_mm: 120, ...MARE_MEDIA } },
];

/** Um acumulado maior nunca é menor que o de uma janela contida nele: mexer numa barra arrasta as outras. */
export function ajustarChuva(cenario: Cenario, janela: Janela, valor: number): Cenario {
  const novo = { ...cenario, [janela]: valor };
  const posicao = JANELAS.findIndex(([j]) => j === janela);
  JANELAS.forEach(([j], i) => {
    if (i < posicao && novo[j] > valor) novo[j] = valor;
    if (i > posicao && novo[j] < valor) novo[j] = valor;
  });
  return novo;
}

export function Simulador() {
  const [cenario, setCenario] = useState<Cenario>(EXEMPLOS[2].cenario);
  const [consultado, setConsultado] = useState(cenario);
  useEffect(() => {
    const espera = setTimeout(() => setConsultado(cenario), 250);
    return () => clearTimeout(espera);
  }, [cenario]);
  const simulacao = useSimulacao(consultado);
  const r = simulacao.data;

  const mudarMare = (campo: "mare_m" | "mare_max_futura_m", valor: number) =>
    setCenario((c) => {
      const novo = { ...c, [campo]: valor };
      if (campo === "mare_m" && novo.mare_max_futura_m < valor) novo.mare_max_futura_m = valor;
      if (campo === "mare_max_futura_m" && novo.mare_m > valor) novo.mare_m = valor;
      return novo;
    });

  return (
    <>
      <div className="ph">
        <div>
          <h1>Simulador</h1>
          <p>Aplica o modelo de alagamento a um cenário hipotético de chuva e maré, para a cidade inteira.</p>
        </div>
      </div>

      <div className="aviso" role="note">
        <span><b>Isto é um exercício, não uma previsão.</b> O modelo aprendeu com cerca de 4 meses de 2026 e erra. Por ser uma árvore
          de decisão, a resposta muda em degraus e pode não subir sempre que a chuva sobe. Não use para tomar decisão operacional.</span>
      </div>

      <div className="grade">
        <div className="c8">
          <Card titulo="Cenário" sub="chuva acumulada até agora e maré" selo="Hipotético" acoes={
            <div className="chips" style={{ marginBottom: 0 }} role="group" aria-label="Exemplos de cenário">
              {EXEMPLOS.map((e) => <button key={e.nome} className="btn" onClick={() => setCenario(e.cenario)}>{e.nome}</button>)}
            </div>}>
            <div className="barras">
              {JANELAS.map(([janela, maximo]) => (
                <label key={janela} className="barra">
                  <span>{NOME_VARIAVEL[janela]}</span>
                  <input type="range" min={0} max={maximo} step={janela === "chuva_1h_mm" ? 0.5 : 1} value={cenario[janela]}
                         onChange={(e) => setCenario((c) => ajustarChuva(c, janela, Number(e.target.value)))} />
                  <b className="num">{numero(cenario[janela], 1)} mm</b>
                </label>
              ))}
              {(["mare_m", "mare_max_futura_m"] as const).map((campo) => (
                <label key={campo} className="barra">
                  <span>{NOME_VARIAVEL[campo]}</span>
                  <input type="range" min={0} max={3} step={0.05} value={cenario[campo]} onChange={(e) => mudarMare(campo, Number(e.target.value))} />
                  <b className="num">{numero(cenario[campo], 2)} m</b>
                </label>
              ))}
              <label className="check">
                <input type="checkbox" checked={cenario.mare_subindo === 1}
                       onChange={(e) => setCenario((c) => ({ ...c, mare_subindo: e.target.checked ? 1 : 0 }))} />
                Maré subindo
              </label>
            </div>
          </Card>
        </div>

        <div className="c4">
          <Card titulo="Resultado" selo="Modelo experimental">
            {simulacao.isPending ? <Carregando /> : simulacao.error ? <ErroCarga erro={simulacao.error} tentarDeNovo={() => simulacao.refetch()} /> : r && (
              <>
                <div className="m-val" style={{ marginTop: 0 }}>{percentual(r.probabilidade, 0)}</div>
                <p className="small" style={{ margin: "6px 0 12px" }}>
                  {r.previsto ? "O modelo preveria" : "O modelo não preveria"} alagamento reportado em alguma rota daqui a {r.horizonte_horas} horas.
                  Das {numero(r.horas_parecidas)} horas de treino parecidas com este cenário, {percentual(r.probabilidade, 0)} tiveram alagamento.
                </p>
                {r.fora_da_faixa.length > 0 && (
                  <div className="aviso" role="alert" style={{ marginBottom: 12 }}>
                    <span><b>Cenário fora do que o modelo viu.</b> {r.fora_da_faixa.map((f) => NOME_VARIAVEL[f.variavel] ?? f.variavel).join(", ")}:
                      {" "}não confie nesta resposta.</span>
                  </div>
                )}
                <h5 className="secao-painel">Regras aplicadas</h5>
                <ol className="lista-pontos" style={{ listStyle: "decimal", paddingLeft: 18, display: "block" }}>
                  {r.caminho.map((p) => (
                    <li key={p.variavel + p.limiar} style={{ display: "list-item", marginBottom: 4 }}>
                      {NOME_VARIAVEL[p.variavel] ?? p.variavel}: {numero(p.valor, 1)} {p.menor_ou_igual ? "até" : "acima de"} {numero(p.limiar, 1)}
                    </li>
                  ))}
                </ol>
                <p className="muted small" style={{ marginTop: 12 }}>
                  <Link to="/risco-alagamento">Ver como o modelo se saiu</Link>. Não há resultado por distrito nem por rota: o modelo responde para a cidade.
                </p>
              </>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
