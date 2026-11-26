import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { chamarFerramenta, listarFerramentas, URL_MCP, type Linha, type RespostaPergunta } from "../api/mcp";
import { Carregando, Vazio } from "../componentes/Estados";
import { Icone } from "../componentes/Icone";
import { Card } from "../componentes/Pecas";
import { numero } from "../formato";

const EXEMPLOS = [
  "Qual foi a acurácia do último treino do modelo de alagamento?",
  "Quais as 5 rotas com mais alagamentos reportados?",
  "Quanto choveu em outubro de 2026 na estação do INMET?",
];

function mensagem(erro: unknown): string {
  const texto = erro instanceof Error ? erro.message : String(erro);
  return /fetch|network|ECONNREFUSED/i.test(texto) ? `O servidor MCP não respondeu em ${URL_MCP}.` : texto;
}

function Erro({ erro }: { erro: unknown }) {
  return <div className="aviso" role="alert"><Icone nome="alerta" /><span>{mensagem(erro)}</span></div>;
}

function Tabela({ linhas }: { linhas: Linha[] }) {
  if (!linhas.length) return <Vazio texto="A consulta não trouxe linhas." />;
  const colunas = Object.keys(linhas[0]);
  return (
    <div className="tabela-rolagem">
      <table className="tabela">
        <thead><tr>{colunas.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {linhas.map((linha, i) => (
            <tr key={i}>{colunas.map((c) => {
              const v = linha[c];
              return <td key={c} className={typeof v === "number" ? "r num" : undefined}>
                {v === null ? "—" : typeof v === "number" ? numero(v, Number.isInteger(v) ? 0 : 3) : String(v)}
              </td>;
            })}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Assistente() {
  const ferramentas = useQuery({ queryKey: ["mcp", "ferramentas"], queryFn: listarFerramentas, retry: false });
  const tabelas = useQuery({ queryKey: ["mcp", "tabelas"], queryFn: () => chamarFerramenta<string[]>("listar_tabelas"), retry: false });
  const [pergunta, setPergunta] = useState("");
  const [sql, setSql] = useState("SELECT modelo, acuracia, linha_de_base, treinado_em FROM gold.modelo_execucao");
  const [tabela, setTabela] = useState<string | null>(null);

  const perguntar = useMutation({ mutationFn: (texto: string) => chamarFerramenta<RespostaPergunta>("perguntar_ao_banco", { pergunta: texto }) });
  const executar = useMutation({ mutationFn: (comando: string) => chamarFerramenta<Linha[]>("executar_select", { sql: comando }) });
  const colunas = useQuery({
    queryKey: ["mcp", "colunas", tabela], enabled: tabela !== null, retry: false,
    queryFn: () => chamarFerramenta<{ coluna: string; tipo: string }[]>("descrever_tabela", { tabela }),
  });

  function escolherTabela(nome: string) {
    setTabela(nome);
    setSql(`SELECT * FROM gold.${nome} LIMIT 20`);
  }

  return (
    <>
      <div className="ph">
        <div>
          <h1>Assistente de dados</h1>
          <p>Perguntas em português sobre a camada Gold, respondidas pelo servidor MCP do AerVita. Só leitura.</p>
        </div>
      </div>

      <div className="grade">
        <div className="c8">
          <Card titulo="Pergunte em português" sub="o GPT escreve o SQL, o banco executa e o GPT explica" selo="MCP">
            <div className="chips">
              {EXEMPLOS.map((e) => <button key={e} className="chip" onClick={() => setPergunta(e)}>{e}</button>)}
            </div>
            <form onSubmit={(e) => { e.preventDefault(); if (pergunta.trim()) perguntar.mutate(pergunta.trim()); }}>
              <label className="sr-only" htmlFor="pergunta">Pergunta</label>
              <textarea id="pergunta" className="campo-texto" value={pergunta} onChange={(e) => setPergunta(e.target.value)}
                        placeholder="Ex.: Quantas horas de alagamento houve em setembro?" />
              <button className="btn btn-primario" style={{ marginTop: 10 }} disabled={!pergunta.trim() || perguntar.isPending}>
                {perguntar.isPending ? "Consultando…" : "Perguntar"}
              </button>
            </form>
            {perguntar.error && <div style={{ marginTop: 14 }}><Erro erro={perguntar.error} /></div>}
            {perguntar.data && (
              <div style={{ marginTop: 16 }}>
                <p style={{ margin: "0 0 12px", fontSize: 14 }}>{perguntar.data.resposta}</p>
                <h5 className="secao-painel">SQL gerado</h5>
                <pre className="sql">{perguntar.data.sql}</pre>
                <h5 className="secao-painel">Dados</h5>
                <Tabela linhas={perguntar.data.dados} />
              </div>
            )}
          </Card>
        </div>

        <div className="c4">
          <Card titulo="Ferramentas do servidor" sub={URL_MCP}>
            {ferramentas.isPending ? <Carregando texto="Conectando ao servidor MCP…" /> : ferramentas.error ? <Erro erro={ferramentas.error} /> : (
              <ul className="lista-pontos">
                {ferramentas.data.map((f) => (
                  <li key={f.nome} style={{ display: "block" }}><b><code>{f.nome}</code></b><br /><span className="muted">{f.descricao}</span></li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="c4">
          <Card titulo="Tabelas da Gold" sub="clique para ver as colunas">
            {tabelas.isPending ? <Carregando /> : tabelas.error ? <Erro erro={tabelas.error} /> : (
              <div className="chips">
                {tabelas.data.map((t) => (
                  <button key={t} className="chip" aria-pressed={tabela === t} onClick={() => escolherTabela(t)}>{t}</button>
                ))}
              </div>
            )}
            {tabela && (colunas.isPending ? <Carregando /> : colunas.error ? <Erro erro={colunas.error} /> : (
              <dl className="kv">
                {colunas.data!.map((c) => [<dt key={`${c.coluna}-n`}>{c.coluna}</dt>, <dd key={`${c.coluna}-t`}>{c.tipo}</dd>])}
              </dl>
            ))}
          </Card>
        </div>

        <div className="c8">
          <Card titulo="Consulta SQL" sub="um único SELECT, até 200 linhas" selo="MCP">
            <form onSubmit={(e) => { e.preventDefault(); if (sql.trim()) executar.mutate(sql.trim()); }}>
              <label className="sr-only" htmlFor="sql">Comando SQL</label>
              <textarea id="sql" className="campo-texto codigo" value={sql} onChange={(e) => setSql(e.target.value)} spellCheck={false} />
              <button className="btn btn-primario" style={{ marginTop: 10 }} disabled={!sql.trim() || executar.isPending}>
                {executar.isPending ? "Executando…" : "Executar"}
              </button>
            </form>
            {executar.error && <div style={{ marginTop: 14 }}><Erro erro={executar.error} /></div>}
            {executar.data && <div style={{ marginTop: 14 }}><Tabela linhas={executar.data} /></div>}
          </Card>
        </div>
      </div>
    </>
  );
}
