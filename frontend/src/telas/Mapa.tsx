import { Fragment, useMemo, useState } from "react";

import type { Esquemas } from "../api/cliente";
import { useArboBairros, useAreasAlagaveis, useBairrosGeo, usePontosAlagamento } from "../api/consultas";
import { Carregando, ErroCarga } from "../componentes/Estados";
import { MapaRecife } from "../componentes/MapaRecife";
import { Card } from "../componentes/Pecas";
import { AGRAVOS, numero, type Agravo } from "../formato";

type Camada = "distritos" | "arboviroses";
type FC = GeoJSON.FeatureCollection;

export const CORES_DISTRITO: Record<number, string> = {
  1: "#4e79a7", 2: "#f28e2b", 3: "#59a14f", 4: "#b07aa1", 5: "#e15759", 6: "#76b7b2", 7: "#d4a20b", 8: "#9c755f",
};
export const ESCALA_CASOS = ["#fbf0ea", "#f7cdb8", "#f0a07f", "#e06a4b", "#bd3a29", "#7f1d13"];
const COR_STATUS: Record<string, string> = { "CONCLUÍDO": "#16a34a", "EM ANDAMENTO": "#d4a20b", "AGUARDANDO FINANCEIRO": "#dc2626" };

const chave = (texto: unknown) =>
  String(texto ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase().split(/\s+/).filter(Boolean).join(" ");

/** A API declara `features` como objetos genéricos; aqui eles são tratados como feições GeoJSON. */
const feicoes = (fc?: { features: { [k: string]: unknown }[] }) => (fc?.features ?? []) as unknown as GeoJSON.Feature[];

/** Limites das classes por quantis (0,2 · 0,4 · 0,6 · 0,8 · 0,95), como no protótipo. */
export function limitesQuantis(valores: number[]): number[] {
  const ord = [...valores].sort((a, b) => a - b);
  if (!ord.length) return [];
  return [0.2, 0.4, 0.6, 0.8, 0.95].map((q) => ord[Math.floor(q * (ord.length - 1))]);
}

export function classe(valor: number, limites: number[]): number {
  let i = 0;
  while (i < limites.length && valor > limites[i]) i++;
  return i;
}

export function Mapa() {
  const geo = useBairrosGeo();
  const arbo = useArboBairros();
  const areas = useAreasAlagaveis();
  const pontos = usePontosAlagamento();
  const [camada, setCamada] = useState<Camada>("distritos");
  const [agravo, setAgravo] = useState<Agravo | "todas">("todas");
  const [mostrarAreas, setMostrarAreas] = useState(true);
  const [mostrarPontos, setMostrarPontos] = useState(false);
  const [selecionado, setSelecionado] = useState<string | null>(null);

  const arboPorBairro = useMemo(
    () => new Map((arbo.data?.bairros ?? []).map((b) => [b.chave_bairro, b])), [arbo.data]);
  const valor = (b?: Esquemas["ArbovirosesBairro"]) => (!b ? 0 : agravo === "todas" ? b.total : b[agravo]);
  const limites = useMemo(() => limitesQuantis([...arboPorBairro.values()].map(valor)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [arboPorBairro, agravo]);

  const bairrosColoridos = useMemo<FC>(() => ({
    type: "FeatureCollection",
    features: feicoes(geo.data).map((f) => {
      const p = f.properties ?? {};
      const cor = camada === "distritos"
        ? CORES_DISTRITO[p.distrito_sanitario as number] ?? "#cccccc"
        : ESCALA_CASOS[classe(valor(arboPorBairro.get(p.chave_bairro as string)), limites)];
      return { ...f, properties: { ...p, cor } };
    }),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [geo.data, camada, arboPorBairro, limites]);

  const pontosColoridos = useMemo<FC>(() => ({
    type: "FeatureCollection",
    features: feicoes(pontos.data).map((f) => ({
      ...f, properties: { ...f.properties, cor: COR_STATUS[String(f.properties?.status)] ?? "#667085" },
    })),
  }), [pontos.data]);

  const feicaoSel = feicoes(geo.data).find((f) => f.properties?.chave_bairro === selecionado);
  const arboSel = selecionado ? arboPorBairro.get(selecionado) : undefined;
  const ranking = arboSel ? [...arboPorBairro.values()].filter((b) => b.total > arboSel.total).length + 1 : null;
  const pontosSel = selecionado
    ? feicoes(pontos.data).filter((f) => chave(f.properties?.bairro) === selecionado) : [];
  const erro = geo.error ?? arbo.error;

  return (
    <>
      <div className="ph">
        <div>
          <h1>Mapa</h1>
          <p>Malha oficial dos 94 bairros com distritos sanitários, notificações de arboviroses, áreas alagáveis e pontos de
            alagamento. Clique num bairro para ver o detalhe.</p>
        </div>
      </div>

      <div className="grade">
        <div className="c8">
          <Card titulo="Recife" sub="bairros" corpo={false} acoes={
            <div className="seg" role="group" aria-label="Cor dos bairros">
              <button aria-pressed={camada === "distritos"} onClick={() => setCamada("distritos")}>Distritos</button>
              <button aria-pressed={camada === "arboviroses"} onClick={() => setCamada("arboviroses")}>Arboviroses</button>
            </div>}>
            <div className="mapa-barra">
              <label className="check"><input type="checkbox" checked={mostrarAreas} onChange={(e) => setMostrarAreas(e.target.checked)} />
                Áreas alagáveis</label>
              <label className="check"><input type="checkbox" checked={mostrarPontos} onChange={(e) => setMostrarPontos(e.target.checked)} />
                Pontos de alagamento</label>
              {camada === "arboviroses" && (
                <select className="input" value={agravo} aria-label="Agravo" onChange={(e) => setAgravo(e.target.value as Agravo | "todas")}>
                  <option value="todas">Todos os agravos</option>
                  {(Object.keys(AGRAVOS) as Agravo[]).map((a) => <option key={a} value={a}>{AGRAVOS[a].nome}</option>)}
                </select>
              )}
            </div>
            {erro ? <ErroCarga erro={erro} tentarDeNovo={() => { geo.refetch(); arbo.refetch(); }} /> :
             geo.isPending ? <div className="mapa-gl"><Carregando texto="Carregando a malha dos bairros…" /></div> : (
              <MapaRecife bairros={bairrosColoridos} areas={{ type: "FeatureCollection", features: feicoes(areas.data) }}
                          pontos={pontosColoridos} mostrarAreas={mostrarAreas} mostrarPontos={mostrarPontos}
                          selecionado={selecionado} aoSelecionar={setSelecionado} />
            )}
            <div className="leg" style={{ padding: "0 18px 14px" }} aria-label="Legenda">
              {camada === "distritos"
                ? Object.entries(CORES_DISTRITO).map(([ds, cor]) => <span key={ds}><i style={{ background: cor }} />DS {ds}</span>)
                : ESCALA_CASOS.map((cor, i) => (
                    <span key={cor}><i style={{ background: cor }} />
                      {i === 0 ? `até ${numero(limites[0])}` : i === ESCALA_CASOS.length - 1 ? `mais de ${numero(limites[i - 1])}`
                        : `${numero(limites[i - 1] + 1)}–${numero(limites[i])}`}</span>))}
              {mostrarAreas && <span><i style={{ background: "#1d4ed8", opacity: 0.5 }} />área alagável</span>}
              {mostrarPontos && Object.entries(COR_STATUS).map(([s, cor]) => (
                <span key={s}><i style={{ background: cor, borderRadius: "50%" }} />{s.toLowerCase()}</span>))}
            </div>
          </Card>
        </div>

        <div className="c4">
          <Card titulo="Bairro" sub={selecionado ? undefined : "nenhum selecionado"}>
            {!feicaoSel ? <p className="muted small">Clique num bairro no mapa.</p> : (
              <>
                <h4 className="titulo-serie" style={{ fontSize: 18 }}>{String(feicaoSel.properties?.nome_bairro ?? selecionado)}</h4>
                <dl className="kv">
                  <dt>Distrito sanitário</dt><dd>{String(feicaoSel.properties?.descricao_distrito ?? "—")}</dd>
                  <dt>RPA</dt><dd>{String(feicaoSel.properties?.rpa ?? "—")}</dd>
                  <dt>Área</dt><dd>{numero(feicaoSel.properties?.area_km2 as number, 2)} km²</dd>
                </dl>
                <h5 className="secao-painel">Arboviroses em 2025</h5>
                {arboSel ? (
                  <dl className="kv">
                    {(Object.keys(AGRAVOS) as Agravo[]).map((a) => (
                      <Fragment key={a}><dt>{AGRAVOS[a].nome}</dt><dd>{numero(arboSel[a])}</dd></Fragment>))}
                    <dt><b>Total</b></dt><dd><b>{numero(arboSel.total)}</b></dd>
                    <dt>Posição na cidade</dt><dd>{ranking}º de {arboPorBairro.size}</dd>
                  </dl>
                ) : <p className="muted small">Sem notificações registradas para este bairro.</p>}
                <h5 className="secao-painel">Pontos de alagamento</h5>
                {pontosSel.length ? (
                  <ul className="lista-pontos">
                    {pontosSel.map((p) => (
                      <li key={String(p.properties?.id_ponto)}>
                        <i style={{ background: COR_STATUS[String(p.properties?.status)] ?? "#667085" }} />
                        <span>{String(p.properties?.logradouro ?? "—")} <span className="muted">· {String(p.properties?.status ?? "").toLowerCase()}</span></span>
                      </li>
                    ))}
                  </ul>
                ) : <p className="muted small">Nenhum ponto cadastrado neste bairro.</p>}
                <button className="btn" style={{ marginTop: 14 }} onClick={() => setSelecionado(null)}>Limpar seleção</button>
              </>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
