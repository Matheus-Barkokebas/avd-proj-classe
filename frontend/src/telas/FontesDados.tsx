import { useAtualizacao } from "../api/consultas";
import { Carregando, ErroCarga } from "../componentes/Estados";
import { Card } from "../componentes/Pecas";
import { dataHora, numero } from "../formato";

const COP = "COP Recife, Prefeitura do Recife";
const PORTAL = "Dados Abertos do Recife";
const URL_COP = "https://esigportal2.recife.pe.gov.br/arcgis/rest/services/COP";

type Fonte = { dado: string; orgao: string; tabela?: string; acesso: string; atualizacao: string; ressalva?: string; link: string };

export const FONTES: Fonte[] = [
  { dado: "Chuva, maré medida e estágio", orgao: COP, tabela: "cop_indicadores", acesso: "API ArcGIS", atualizacao: "De hora em hora na fonte; a fonte guarda só cerca de 24 h",
    ressalva: "Só existe histórico do que for coletado. O servidor não responde a IPs de fora do Brasil.", link: URL_COP },
  { dado: "Nível dos rios e cotas", orgao: COP, tabela: "cop_rios", acesso: "API ArcGIS", atualizacao: "De hora em hora na fonte; a fonte guarda só cerca de 24 h",
    ressalva: "A unidade do nível ainda precisa ser confirmada com o COP.", link: URL_COP },
  { dado: "Previsão de chuva por modelo", orgao: COP, tabela: "cop_previsao_chuva", acesso: "API ArcGIS", atualizacao: "Diária", link: URL_COP },
  { dado: "Chuva mensal e média histórica", orgao: COP, tabela: "cop_chuva_mensal", acesso: "API ArcGIS", atualizacao: "Diária", link: URL_COP },
  { dado: "Tábua de maré", orgao: COP, tabela: "cop_mare", acesso: "API ArcGIS", atualizacao: "Tábua publicada até 31/12/2026", link: URL_COP },
  { dado: "Alagamento por rota", orgao: COP, tabela: "cop_alagamento_rotas", acesso: "API ArcGIS", atualizacao: "De hora em hora na fonte",
    ressalva: "Provavelmente vem de alertas de motoristas (Waze), a confirmar com o COP. Registra o que foi reportado, e só nas rotas monitoradas.", link: URL_COP },
  { dado: "Traçado das rotas", orgao: COP, tabela: "cop_rotas", acesso: "API ArcGIS", atualizacao: "Eventual", link: URL_COP },
  { dado: "Pluviômetros", orgao: COP, tabela: "cop_pluviometros", acesso: "API ArcGIS", atualizacao: "A fonte parou em 26/02/2026", ressalva: "Sem uso no modelo.", link: URL_COP },
  { dado: "Áreas alagáveis", orgao: COP, tabela: "cop_areas_alagaveis", acesso: "API ArcGIS", atualizacao: "Eventual", link: URL_COP },
  { dado: "Pontos de alagamento", orgao: "EMLURB, publicado pelo COP", tabela: "cop_pontos_alagamento", acesso: "API ArcGIS", atualizacao: "Eventual",
    ressalva: "Mostram obras de drenagem de 2013 a 2022, não quando alagou.", link: URL_COP },
  { dado: "Chuva horária de Recife (estação A301)", orgao: "INMET, Governo Federal", tabela: "inmet_chuva", acesso: "Arquivo anual (ZIP)", atualizacao: "Publicada com atraso",
    ressalva: "Usada para treinar o modelo. Recife só tem leituras a partir de 21/05/2026.", link: "https://portal.inmet.gov.br/dadoshistoricos" },
  { dado: "Arboviroses de 2025", orgao: PORTAL, tabela: "epidemiologia", acesso: "API CKAN", atualizacao: "Conforme a Prefeitura publica",
    ressalva: "Os metadados só explicam a classificação da dengue.", link: "https://dados.recife.pe.gov.br/dataset/casos-de-dengue-zika-e-chikungunya" },
  { dado: "Histórico de arboviroses, 2013 a 2024", orgao: PORTAL, tabela: "epidemiologia_historico", acesso: "API CKAN e CSV", atualizacao: "Carga única",
    ressalva: "O título de um recurso pode não bater com o agravo: vale o CID de cada linha.", link: "https://dados.recife.pe.gov.br/dataset/casos-de-dengue-zika-e-chikungunya" },
  { dado: "Bairros, RPAs e distritos sanitários", orgao: PORTAL, acesso: "API CKAN", atualizacao: "Eventual", link: "https://dados.recife.pe.gov.br/" },
];

export function FontesDados() {
  const atualizacao = useAtualizacao();
  const cargas = new Map((atualizacao.data?.tabelas ?? []).map((t) => [t.tabela, t]));

  return (
    <>
      <div className="ph">
        <div>
          <h1>Fontes de dados</h1>
          <p>De onde vem cada dado do painel, como é obtido, quando entrou no banco pela última vez e o que é preciso saber antes de usar. Só fontes públicas de governo.</p>
        </div>
      </div>
      <Card titulo="Catálogo" sub="data da carga é de quando coletamos, não de quando o dado foi medido" corpo={false}>
        {atualizacao.error && <ErroCarga erro={atualizacao.error} tentarDeNovo={() => atualizacao.refetch()} />}
        {atualizacao.isPending && <Carregando />}
        <div className="tabela-rolagem">
          <table className="tabela">
            <thead><tr><th>Dado</th><th>Fonte</th><th>Acesso</th><th>Atualização</th><th>Última carga</th><th className="r">Linhas</th><th>O que saber</th></tr></thead>
            <tbody>
              {FONTES.map((f) => {
                const carga = f.tabela ? cargas.get(f.tabela) : undefined;
                return (
                  <tr key={f.dado}>
                    <td><b>{f.dado}</b></td>
                    <td><a href={f.link} target="_blank" rel="noreferrer">{f.orgao}</a></td>
                    <td className="muted">{f.acesso}</td>
                    <td className="muted">{f.atualizacao}</td>
                    <td className="num">{carga ? dataHora(carga.carregado_em) : "—"}</td>
                    <td className="r num">{carga ? numero(carga.linhas) : "—"}</td>
                    <td className="muted small">{f.ressalva ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
