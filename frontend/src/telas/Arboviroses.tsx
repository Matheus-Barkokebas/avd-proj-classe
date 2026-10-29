import { useMemo, useState } from "react";

import { useArboBairros, useArboSemanas } from "../api/consultas";
import { Carregando, ErroCarga } from "../componentes/Estados";
import { GraficoArboSemanas, GraficoColunas } from "../componentes/Graficos";
import { Card, Metrica } from "../componentes/Pecas";
import { AGRAVOS, numero, semanaEpi, type Agravo } from "../formato";

type Ordem = "total" | "dengue" | "chikungunya" | "zika" | "nome_bairro";
const POR_PAGINA = 15;

const sem = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function Arboviroses() {
  const semanas = useArboSemanas();
  const bairros = useArboBairros();
  const [ativos, setAtivos] = useState<Agravo[]>(["dengue", "chikungunya", "zika"]);
  const [modo, setModo] = useState<"notificacoes" | "nao_descartadas">("notificacoes");
  const [busca, setBusca] = useState("");
  const [ordem, setOrdem] = useState<Ordem>("total");
  const [limite, setLimite] = useState(POR_PAGINA);

  const resumo = useMemo(() => {
    if (!semanas.data) return null;
    const porAgravo: Record<string, number> = {};
    const porSemana = new Map<number, number>();
    let total = 0, naoDescartadas = 0;
    for (const l of semanas.data) {
      porAgravo[l.agravo] = (porAgravo[l.agravo] ?? 0) + l.notificacoes;
      porSemana.set(l.semana, (porSemana.get(l.semana) ?? 0) + l.notificacoes);
      total += l.notificacoes;
      naoDescartadas += l.nao_descartadas;
    }
    const [pico, noPico] = [...porSemana.entries()].reduce((m, e) => (e[1] > m[1] ? e : m), [0, 0]);
    return { porAgravo, total, descartadas: total - naoDescartadas, pico, noPico };
  }, [semanas.data]);

  const porDistrito = useMemo(() => {
    if (!bairros.data) return [];
    const soma = new Map<string, number>();
    for (const b of bairros.data.bairros) {
      const ds = b.descricao_distrito ?? "Sem distrito";
      soma.set(ds, (soma.get(ds) ?? 0) + ativos.reduce((s, a) => s + b[a], 0));
    }
    return [...soma.entries()].map(([rotulo, valor]) => ({ rotulo, valor })).sort((a, b) => b.valor - a.valor);
  }, [bairros.data, ativos]);

  const linhas = useMemo(() => {
    if (!bairros.data) return [];
    const q = sem(busca.trim());
    return bairros.data.bairros
      .filter((b) => !q || sem(b.nome_bairro).includes(q) || sem(b.descricao_distrito ?? "").includes(q))
      .sort((a, b) => (ordem === "nome_bairro" ? a.nome_bairro.localeCompare(b.nome_bairro, "pt-BR") : b[ordem] - a[ordem]));
  }, [bairros.data, busca, ordem]);

  const alternar = (a: Agravo) =>
    setAtivos((atual) => (atual.includes(a) ? (atual.length > 1 ? atual.filter((x) => x !== a) : atual) : [...atual, a]));

  const cabecalho = (chave: Ordem, texto: string, direita = true) => (
    <th className={direita ? "r" : ""} aria-sort={ordem === chave ? "descending" : "none"}>
      <button className="ord" onClick={() => setOrdem(chave)}>{texto}{ordem === chave && " ▼"}</button>
    </th>
  );

  return (
    <>
      <div className="ph">
        <div>
          <h1>Arboviroses</h1>
          <p>Notificações de dengue, chikungunya e zika em 2025 (Portal de Dados Abertos do Recife), agregadas por semana
            epidemiológica, bairro e distrito. Sem nenhum dado pessoal.</p>
        </div>
      </div>

      {semanas.error ? <ErroCarga erro={semanas.error} tentarDeNovo={() => semanas.refetch()} /> : (
        <div className="metricas">
          {resumo ? (
            <>
              <Metrica rotulo="Notificações" valor={numero(resumo.total)}
                       rodape={Object.entries(AGRAVOS).map(([k, a]) => `${a.nome} ${numero(resumo.porAgravo[k] ?? 0)}`).join(" · ")} />
              <Metrica rotulo="Semana de pico" valor={resumo.pico ? semanaEpi(resumo.pico) : "—"}
                       rodape={`${numero(resumo.noPico)} notificações na semana`} />
              <Metrica rotulo="Descartadas após investigação" valor={numero((resumo.descartadas / resumo.total) * 100, 0)} unidade="%"
                       rodape={`${numero(resumo.descartadas)} notificações`} />
              <Metrica rotulo="Bairros com notificação"
                       valor={bairros.data ? numero(bairros.data.bairros.filter((b) => b.total > 0).length) : "…"}
                       unidade={bairros.data ? `de ${bairros.data.bairros.length}` : undefined}
                       rodape={bairros.data ? `${numero(bairros.data.nao_georreferenciadas)} sem bairro reconhecido` : undefined} />
            </>
          ) : <><Carregando /><Carregando /><Carregando /><Carregando /></>}
        </div>
      )}

      <div className="grade">
        <div className="c8">
          <Card titulo="Notificações por semana epidemiológica" acoes={
            <div className="seg" role="group" aria-label="Quais notificações contar">
              <button aria-pressed={modo === "notificacoes"} onClick={() => setModo("notificacoes")}>Todas</button>
              <button aria-pressed={modo === "nao_descartadas"} onClick={() => setModo("nao_descartadas")}>Sem descartadas</button>
            </div>}>
            <div className="chips" role="group" aria-label="Agravos no gráfico">
              {(Object.keys(AGRAVOS) as Agravo[]).map((a) => (
                <button key={a} className="chip" aria-pressed={ativos.includes(a)} onClick={() => alternar(a)}>
                  <i style={{ background: AGRAVOS[a].cor }} />{AGRAVOS[a].nome}
                </button>
              ))}
            </div>
            {semanas.isPending ? <Carregando /> : semanas.error ? null :
              <GraficoArboSemanas linhas={semanas.data} ativos={ativos} modo={modo} />}
          </Card>
        </div>
        <div className="c4">
          <Card titulo="Por distrito sanitário" sub="agravos selecionados">
            {bairros.isPending ? <Carregando /> : bairros.error ? <ErroCarga erro={bairros.error} /> :
              <GraficoColunas dados={porDistrito} rotulo="Notificações por distrito sanitário" />}
          </Card>
        </div>

        <div className="c12">
          <Card titulo="Bairros" sub="clique no cabeçalho para ordenar" corpo={false} acoes={
            <input className="input" type="search" placeholder="Filtrar bairro ou distrito" value={busca}
                   aria-label="Filtrar bairro ou distrito" onChange={(e) => { setBusca(e.target.value); setLimite(POR_PAGINA); }} />}>
            {bairros.isPending ? <Carregando /> : bairros.error ? <ErroCarga erro={bairros.error} /> : (
              <>
                <div className="tabela-rolagem">
                  <table className="tabela">
                    <thead>
                      <tr>
                        <th>#</th>
                        {cabecalho("nome_bairro", "Bairro", false)}
                        <th>Distrito</th>
                        {cabecalho("dengue", "Dengue")}
                        {cabecalho("chikungunya", "Chikungunya")}
                        {cabecalho("zika", "Zika")}
                        {cabecalho("total", "Total")}
                      </tr>
                    </thead>
                    <tbody>
                      {linhas.slice(0, limite).map((b, i) => (
                        <tr key={b.chave_bairro}>
                          <td className="num muted">{i + 1}</td>
                          <td><b>{b.nome_bairro}</b></td>
                          <td className="muted">{b.descricao_distrito ?? "—"}</td>
                          <td className="num r">{numero(b.dengue)}</td>
                          <td className="num r">{numero(b.chikungunya)}</td>
                          <td className="num r">{numero(b.zika)}</td>
                          <td className="num r"><b>{numero(b.total)}</b></td>
                        </tr>
                      ))}
                      {!linhas.length && <tr><td colSpan={7} className="muted">Nenhum bairro encontrado.</td></tr>}
                    </tbody>
                  </table>
                </div>
                <div className="rodape-tabela">
                  <span>{numero(Math.min(limite, linhas.length))} de {numero(linhas.length)} bairros</span>
                  {limite < linhas.length && (
                    <button className="btn" onClick={() => setLimite((l) => l + POR_PAGINA)}>Mostrar mais</button>
                  )}
                </div>
                {bairros.data.nao_georreferenciadas > 0 && (
                  <p className="nota" style={{ padding: "0 18px 14px" }}>
                    {numero(bairros.data.nao_georreferenciadas)} notificações têm um nome de bairro que não corresponde à
                    tabela oficial e ficam fora desta lista (ex.: {bairros.data.grafias_nao_reconhecidas.slice(0, 4).join(", ")}).
                  </p>
                )}
              </>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
