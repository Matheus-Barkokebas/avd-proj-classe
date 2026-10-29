# Arquitetura do Projeto — Vigidesastres

> **Projeto:** Vigidesastres — Painel Situacional para Preparação e Resposta a Emergências Climáticas (Recife/PE)
> **Escopo:** consolidar fontes meteorológicas, hidrológicas, epidemiológicas, ambientais, assistenciais e territoriais em um único fluxo de dados, permitindo cruzamentos, indicadores situacionais, boletins automáticos e alertas preditivos.
> **Estado atual:** existe um protótipo do painel ([`prototipo/v3-aervita-console.html`](../frontend/prototipo/v3-aervita-console.html)) com arboviroses e território reais e o restante simulado. Este documento descreve a arquitetura-alvo para alimentá-lo com dados reais.

---

## 1. Visão Geral

O fluxo do projeto vai da **coleta nas APIs públicas** até a **entrega de indicadores e alertas** para as equipes de resposta, passando por um **lago de dados em camadas (arquitetura medallion)**.

```text
   FONTES        API Recife (CKAN)    COP Recife (ArcGIS)    API ANA (HidroWeb)    Complementares (roadmap)
                         │                    │                      │                      │
                         └────────────────────┴───────────┬──────────┴──────────────────────┘
                                              ▼
   INGESTÃO                    Conectores por fonte + agendador (coleta periódica)
                                              ▼
   RAW                         Resposta original das APIs (JSON/CSV), particionada por data de coleta
                                              ▼
   BRONZE                      Dados tipados e materializados (Parquet/Delta) — 1 registro por evento
                                              ▼
   SILVER                      Limpeza, padronização temporal e territorial, deduplicação
                                              ▼
   GOLD                        Tabelas integradas e indicadores por distrito / bairro / dia
                                              ▼
   ANÁLISE & MODELOS           Análise diagnóstica · séries temporais · classificação de risco
                                              ▼
   ENTREGA              ┌───────────────┬───────────────────┬────────────────────┐
                        ▼               ▼                   ▼                    ▼
                 Painel Situacional  Boletim automático  Alertas preditivos   Exportações / API interna
                        └───────────────┴─────────┬───────┴────────────────────┘
                                                  ▼
                                    Decisão e resposta das equipes
```

---

## 2. Camada de Fontes de Dados

### 2.1 Domínios de dados

| Categoria | Onde encontrar | O que se obtém |
|---|---|---|
| 🌧️ Meteorológicos | **COP Recife** / APAC / INMET | chuva média 1h/24h, previsão por modelo, chuva mensal vs. média histórica, pluviômetros, temperatura, vento |
| 🌊 Hidrológicos | **COP Recife** / APAC / ANA | nível de rios com cotas oficiais, maré, áreas alagáveis, pontos de alagamento, estações fluviométricas |
| 🦠 Epidemiológicos | Dados Abertos Recife / Secretaria de Saúde | dengue, zika, chikungunya, casos por bairro e outros indicadores |
| 🌱 Ambientais | CPRH / MonitorAr | qualidade do ar, poluentes, qualidade da água, balneabilidade |
| 🏥 Assistenciais | Dados Abertos Recife / DATASUS | atendimentos, solicitações, serviços, vacinação, unidades de saúde |
| 🗺️ Territoriais | COP Recife / Dados Abertos Recife | bairros, RPA, ocorrências georreferenciadas, áreas de risco, eventos urbanos |

### 2.2 API 1 — Dados Abertos Recife (CKAN)

- **Endpoint:** `https://dados.recife.pe.gov.br/pt_BR/api/action/datastore_search`
- **Tipo:** API DataStore do CKAN (REST, resposta JSON).
- **Parâmetros principais:** `resource_id` (identificador do conjunto), `limit`, `offset`, `q` (busca textual), `filters` (filtros por coluna).
- **Autenticação:** não exigida (dados abertos).
- **Paginação:** por `limit` / `offset`; coleta completa iterando as páginas até esgotar os registros.
- **Uso no projeto:**
  - epidemiologia (arboviroses por bairro / semana epidemiológica);
  - saúde e dados assistenciais (atendimentos, serviços, unidades);
  - Defesa Civil e ocorrências georreferenciadas;
  - dados territoriais (bairros, RPA, áreas de risco);
  - mobilidade e serviços municipais.
- **Observação:** cada conjunto é um `resource_id` distinto; o catálogo lista os recursos disponíveis. Também existem o endpoint `datastore_search_sql` e o download direto do CSV de cada recurso.

### 2.3 API 2 — ANA (HidroWeb Service)

- **Endpoint base:** `https://www.ana.gov.br/hidrowebservice/`
- **Tipo:** web service da Agência Nacional de Águas (rede HidroWeb).
- **Autenticação:** pode exigir cadastro/identificação para uso do serviço.
- **Formato:** respostas em XML/JSON conforme a operação.
- **Uso no projeto:**
  - chuva acumulada por bacia / estação pluviométrica;
  - nível (cota) e vazão de rios e canais — comparação com a **cota de atenção/alerta**;
  - inventário de estações (fluviométricas e pluviométricas);
  - séries históricas hidrológicas para modelagem.

### 2.3.1 COP Recife — Centro de Operações (ArcGIS público)

Fonte de **chuva e rios** em uso enquanto a ANA não tem credenciais. A prefeitura publica no ArcGIS os
dados que alimentam o painel do COP, sem login.

- **Endpoint base:** `https://esigportal2.recife.pe.gov.br/arcgis/rest/services/COP` (`MapServer/<camada>/query`).
- **Autenticação:** não exigida. **Paginação:** `resultOffset` / `resultRecordCount` (máximo 2.000 por página).
- **Camadas coletadas** (`conf/sources/cop_recife.yml`, uma fonte por camada no runner):

| Fonte | Conteúdo | Frequência |
|---|---|---|
| `cop_indicadores` | chuva média 1h/24h, maior acumulado e estação, maré, estágio operacional, ocorrências, abrigos | horária |
| `cop_rios` | nível de 5 estações (Capibaribe em Limoeiro, Paudalho e São Lourenço da Mata; Jaboatão; Duas Unas) com cotas de pré-alerta, alerta e inundação | horária |
| `cop_previsao_chuva` | previsão hora a hora (GFS, ECMWF, ICON, WRF) | diária |
| `cop_chuva_mensal` | chuva por mês: ano atual, ano anterior, média histórica | diária |
| `cop_pluviometros` | histórico por pulso dos pluviômetros municipais (jul/2023 a fev/2026) | mensal |
| `cop_areas_alagaveis` | polígonos de áreas alagáveis por distrito sanitário | mensal |
| `cop_pontos_alagamento` | pontos de alagamento com obra de drenagem (EMLURB) | mensal |

- **Limitações:** as tabelas atuais guardam só ~24h — o histórico depende de coleta horária agendada.
  Não há chuva atual por estação (os pluviômetros pararam em fev/2026). Unidade do nível dos rios e alguns
  campos da previsão a confirmar com o COP.

### 2.4 Fontes complementares (roadmap)

APAC, INMET, CPRH, MonitorAr e DATASUS entram em fases posteriores para reforçar previsão meteorológica, qualidade ambiental e dados assistenciais federais. A arquitetura já prevê um **conector por fonte**, então a inclusão é incremental.

### 2.5 Frequência de atualização

| Fonte | Domínio | Atualização típica | Coleta no projeto |
|---|---|---|---|
| API Recife — arboviroses / saúde | Epidemiológico / Assistencial | semanal (semana epidemiológica) | diária (captura incremental) |
| API Recife — ocorrências / Defesa Civil | Territorial / Assistencial | diária / sob demanda | diária (horária em contingência) |
| API Recife — territorial (bairros, RPA, áreas de risco) | Territorial | eventual (cadastral) | mensal |
| COP Recife — chuva e rios (indicadores, rios) | Meteorológico / Hidrológico | horária (janela de ~24h) | horária |
| COP Recife — previsão e chuva mensal | Meteorológico | diária | diária |
| COP Recife — pluviômetros, áreas alagáveis, pontos de alagamento | Meteorológico / Territorial | eventual | mensal |
| API ANA — nível de rios / chuva *(aguardando credenciais)* | Hidrológico / Meteorológico | horária / sub-diária | horária |
| APAC / INMET *(roadmap)* | Meteorológico / Hidrológico | horária | horária |
| CPRH / MonitorAr *(roadmap)* | Ambiental | diária | diária |

---

## 3. Camada de Ingestão (Coleta)

Responsável por buscar os dados nas APIs e gravá-los **sem transformação** na camada RAW.

- **Um conector por fonte:** encapsula endpoint, parâmetros, paginação e formato de resposta.
- **Agendador / orquestrador:** dispara cada conector na frequência definida na seção 2.5.
- **Gravação particionada por data de coleta** (`fonte/ano/mês/dia/`), preservando o payload original.
- **Idempotência:** recoletar a mesma janela não duplica dados na Bronze (chave de negócio + data de referência).
- **Controle de execução:** registro de início/fim, contagem de registros, status e erros de cada coleta.
- **Reprocessamento:** como a RAW guarda o original, qualquer camada acima pode ser reconstruída.

```text
Agendador
   │  (dispara na frequência de cada fonte)
   ▼
Conector Recife (CKAN)    Conector COP (ArcGIS)    Conector ANA (HidroWeb)    Conector <fonte futura>
   │                          │                         │                          │
   └──────────────────────────┴────────────┬────────────┴──────────────────────────┘
                   ▼
     RAW  —  payload original + metadados de coleta (fonte, data, parâmetros)
```

---

## 4. Camadas de Armazenamento (Medallion)

| Camada | Conteúdo | Objetivo |
|---|---|---|
| **RAW** | Cópia fiel da resposta das APIs (JSON/CSV), particionada por data de coleta | Rastreabilidade e reprocessamento |
| **BRONZE** | Dados tipados e materializados (Parquet / Delta Tables), 1 linha = 1 evento/registro | Padronizar formato e esquema |
| **SILVER** | Dados limpos, deduplicados, com datas e território padronizados | Garantir qualidade e consistência |
| **GOLD** | Tabelas integradas e indicadores prontos para o painel, os modelos e os boletins | Consumo analítico |

```text
RAW  ──►  BRONZE  ──►  SILVER  ──►  GOLD
(original)  (tipado)   (limpo/     (integrado /
                        padronizado) indicadores)
```

### 4.1 Primeira release: RAW no MongoDB Atlas e camada padronizada no Neon

O medalhão acima é a arquitetura-alvo. Para entregar mais rápido, a primeira release usa duas
camadas apenas ([decisão 0001](decisoes/0001-raw-mongodb-padronizada-neon.md)):

| Camada | Onde | Conteúdo |
|---|---|---|
| **RAW** | MongoDB Atlas | Conteúdo original de cada coleta no GridFS (bytes intactos, sem limite de 16 MB) e metadados em `raw_coletas`, com índice único em fonte + data de coleta + arquivo |
| **Padronizada** | Neon (PostgreSQL) | Uma tabela por contrato de `conf/contracts/` (colunas tipadas, `NOT NULL` nos obrigatórios, `UNIQUE` na chave de negócio), `rejeitados` (quarentena com motivo), `dim_bairro` e `dim_distrito` |

```text
APIs ──► RAW (Atlas) ──► validação por contrato ──► Padronizada (Neon) ──► painel / boletim
                                   └──► rejeitados (Neon), com o motivo
```

- A camada padronizada cumpre nesta release o papel da Bronze e de parte da Silver
  (tipagem, chave de negócio, quarentena, vínculo bairro → distrito). Silver e Gold voltam nas fases seguintes.
- Os dois destinos são opcionais por execução: sem configuração, a ingestão continua gravando em arquivo
  (`data/raw` e Parquet em `data/bronze`), que é o modo usado nos testes.

---

## 5. Camada de Processamento e Integração

Transformações aplicadas entre **Bronze → Silver → Gold**.

### 5.1 Padronização temporal
- Datas/horas no formato `YYYY-MM-DD HH:MM:SS` e fuso único.
- Chaves de calendário: dia, semana, mês, **semana epidemiológica**, marcação de período chuvoso.
- Janelas móveis: chuva acumulada 24h/72h, média histórica por mês.

### 5.2 Padronização territorial
- Tabela de referência única ligando **bairro ↔ RPA ↔ Distrito Sanitário ↔ microrregião ↔ geometria**.
- Normalização de nomes de bairro (acentuação, caixa, grafias alternativas).
- Georreferenciamento de ocorrências e validação dos pontos dentro do município.
- Vínculo com **áreas de risco** e malha populacional para estimar população exposta.

### 5.3 Qualidade
- Remoção de duplicidades por chave de negócio.
- Tratamento de nulos em localização/serviço (imputação por regra ou exclusão sinalizada).
- Correção de inconsistências temporais (ex.: conclusão anterior à abertura).
- Padronização de categorias (`grupo`, `serviço`, `status`, `tipo de ocorrência`).

### 5.4 Cruzamentos (na camada Gold)
- **Chuva/nível de rio × ocorrências × território** → situação de risco por distrito.
- **Arboviroses × bairro × chuva/temperatura** → pressão epidemiológica.
- **Qualidade ambiental × território** → camada de contexto.
- Grão de saída: **distrito / bairro / dia**.

---

## 6. Camada de Análise e Modelagem

### 6.1 Análise diagnóstica
Sazonalidade, tendências, picos associados a eventos, ranking de bairros/serviços por volume e por tempo de resposta, relação chuva × ocorrências × arboviroses.

### 6.2 Indicadores situacionais (Gold)
- Chuva acumulada 24h vs. média histórica;
- Nível de rios/canais vs. cota de atenção/alerta;
- Casos de arboviroses por bairro e variação semanal;
- População estimada em áreas de risco expostas.

### 6.3 Modelos preditivos
- Previsão de chuva acumulada e de nível de rios (séries temporais);
- Previsão de volume de ocorrências por distrito;
- Previsão de notificações de arboviroses por bairro;
- (Opcional) classificação do risco de agravamento por área.

### 6.4 Classificação de risco
Regra que combina os indicadores em quatro níveis (os mesmos exibidos no painel):

| Nível | Critério combinado (ilustrativo — calibrar com histórico e Defesa Civil) |
|---|---|
| **Baixo** | chuva 24h < 30 mm · rios abaixo da cota de atenção · sem ocorrências |
| **Moderado** | chuva 24h 30–70 mm · rio na cota de atenção · ocorrências pontuais |
| **Alto** | chuva 24h 70–100 mm · rio na cota de alerta · solo saturado / deslizamento monitorado |
| **Crítico** | chuva 24h > 100 mm · rio acima da cota de alerta · inundação ativa / remoção em curso |

```text
GOLD (histórico + indicadores do momento)
        ▼
Análise Diagnóstica  ──►  Sazonalidade · Tendências · Picos
        ▼
Cruzamento (chuva/rio · ocorrências · arboviroses · território)
        ▼
Modelos Preditivos (chuva, nível, ocorrências, arboviroses)
        ▼
Classificação de Risco por Distrito (baixo → crítico)
        ▼
Estimativa de cenário para as próximas horas/dias
```

---

## 7. Camada de Entrega (Serving)

| Saída | Descrição |
|---|---|
| **Painel Situacional** | O protótipo `v3-aervita-console.html` evoluído: KPIs, situação por distrito, alertas e gráficos alimentados pela camada Gold |
| **Boletim Situacional Automático** | Texto consolidado (resumo, destaques, recomendação) gerado a partir de um template + indicadores Gold |
| **Alertas Preditivos** | Fila priorizada de alertas disparada quando indicadores/modelos cruzam limiares de risco |
| **Exportações / API interna** | Tabelas Gold disponibilizadas para outros sistemas e para relatórios |

```text
GOLD ─┬─► Painel Situacional ──► equipes acompanham o cenário
      ├─► Boletim automático ──► distribuição (nota técnica / relatório)
      ├─► Alertas preditivos ──► notificação às equipes de resposta
      └─► API interna / export ─► integração e relatórios
                    │
                    ▼
        Priorização e alocação de equipes
```

### 7.1 Release 2: API e front-end

A entrega passa por uma **API em FastAPI** (`api/`) que lê a camada padronizada no Neon com um usuário só de
leitura e serve JSON ao **front-end em React + TypeScript** (`frontend/`). O navegador nunca acessa o banco.
Ver [decisão 0002](decisoes/0002-api-fastapi-e-front-react.md) e as rotas em [`api/README.md`](../api/README.md).

```text
Neon (padronizada) ──► API FastAPI /v1 (só leitura, cache, CORS) ──► Front React + TypeScript
```

---

## 8. Fluxo Fim a Fim

```text
┌──────────────┐   ┌───────────┐   ┌─────────────────────────────────┐   ┌──────────────────┐   ┌───────────────────┐
│   FONTES     │   │ INGESTÃO  │   │        LAGO DE DADOS            │   │ ANÁLISE / MODELOS│   │      ENTREGA      │
│              │   │           │   │  RAW → BRONZE → SILVER → GOLD   │   │                  │   │                  │
│ API Recife   │──►│ Conectores│──►│  original  tipado  limpo  integr│──►│ Diagnóstico      │──►│ Painel Situacional│
│ API ANA      │   │ +         │   │                                 │   │ Séries temporais │   │ Boletim automático│
│ Complementar │   │ agendador │   │  particionado por data de coleta│   │ Classif. de risco│   │ Alertas preditivos│
│ (roadmap)    │   │           │   │                                 │   │                  │   │ API / exportações │
└──────────────┘   └───────────┘   └─────────────────────────────────┘   └──────────────────┘   └─────────┬─────────┘
                                                                                                         ▼
                                                                                        Decisão e resposta das equipes
```

---

## 9. Orquestração e Frequência

| Etapa | Frequência | Gatilho |
|---|---|---|
| Coleta de chuva e rios (COP Recife: `cop_recife.py --frequencia horaria`) | horária | agendador |
| Coleta de previsão e chuva mensal (COP Recife: `--frequencia diaria`) | diária | agendador |
| Coleta hidrológica/meteorológica (ANA, quando houver credenciais) | horária | agendador |
| Coleta de ocorrências / Defesa Civil (Recife) | diária (horária em contingência) | agendador / evento |
| Coleta epidemiológica (Recife) | diária | agendador |
| Coleta territorial cadastral (Recife) | mensal | agendador |
| Transformações Bronze → Silver → Gold | após cada coleta | conclusão da ingestão |
| Recálculo de indicadores e risco | a cada atualização da Gold | conclusão do processamento |
| Execução dos modelos preditivos | horária / diária conforme o modelo | agendador |
| Avaliação de alertas | a cada recálculo de risco | mudança de nível / limiar |
| Geração de boletim | sob demanda + agendado (ex.: 2×/dia) | botão no painel / agendador |

---

## 10. Qualidade, Governança e Observabilidade

- **Contrato de dados por fonte:** esquema esperado, tipos, obrigatoriedade, domínio de valores.
- **Validações automáticas** na entrada da Silver (completude, faixas, integridade referencial de território).
- **Métricas de coleta:** volume por execução, latência, taxa de erro, cobertura temporal.
- **Catálogo e linhagem:** origem de cada tabela e transformações aplicadas (RAW → Gold).
- **Versionamento:** código no Git; dados versionados por partição de data de coleta.
- **LGPD:** uso apenas de dados públicos e agregados; sem dados pessoais identificáveis.
- **Reprodutibilidade:** qualquer camada é reconstruível a partir da RAW (na primeira release, a RAW fica no MongoDB Atlas — [decisão 0001](decisoes/0001-raw-mongodb-padronizada-neon.md)).

---

## 11. Relação com o Protótipo

O protótipo atual usa **dados simulados**. O mapeamento abaixo indica de onde cada elemento passará a ser alimentado.

| Elemento do painel | Indicador | Fonte primária | Camada |
|---|---|---|---|
| KPI *Chuva acumulada · 24h* | soma de precipitação nas últimas 24h | COP Recife (`cop_indicadores`) · ANA / APAC / INMET | Gold (release 1: padronizada) |
| KPI *Distritos em atenção* | contagem de distritos com risco ≥ moderado | regra de classificação de risco | Gold |
| KPI *Alertas ativos* | alertas abertos no período | motor de alertas | Serving |
| KPI *População em áreas de risco* | população estimada nas áreas expostas | territorial Recife (áreas de risco) + malha populacional | Gold |
| Tabela *Situação por Distrito Sanitário* | risco, chuva, população exposta, ocorrência | cruzamento chuva × território × ocorrências | Gold |
| Painel *Alertas Ativos* | fila de alertas priorizados | motor de alertas preditivos | Serving |
| Gráfico *Volume de chuva diário* | série de 7 dias | COP Recife (`cop_indicadores`, coleta horária) · ANA / APAC / INMET | Gold (release 1: padronizada) |
| Réguas de *nível dos rios* | nível vs. cotas de pré-alerta, alerta e inundação | COP Recife (`cop_rios`) | Gold (release 1: padronizada) |
| Previsão de chuva | chuva prevista hora a hora por modelo | COP Recife (`cop_previsao_chuva`) | Gold (release 1: padronizada) |
| Camada de *áreas alagáveis* no mapa | polígonos por distrito sanitário | COP Recife (`cop_areas_alagaveis`) | Gold (release 1: padronizada) |
| Gráfico *Notificações de arboviroses* | casos/dia por semana epidemiológica | API Recife (epidemiologia) | Gold |
| *Boletim Situacional Automático* | texto consolidado | template + indicadores da Gold | Serving |

---

## 12. Stack de Referência

Sugestão de tecnologias por camada (a definir na implementação):

| Camada | Opções de referência |
|---|---|
| Ingestão | Python + biblioteca HTTP + agendador (cron / orquestrador de pipelines) |
| Armazenamento | data lake em arquivos colunares (Parquet / Delta), organizado em RAW/Bronze/Silver/Gold |
| Armazenamento (primeira release) | MongoDB Atlas para a RAW e Neon (PostgreSQL) para a camada padronizada — [decisão 0001](decisoes/0001-raw-mongodb-padronizada-neon.md) |
| Processamento | transformações em lote (SQL analítico ou dataframes) |
| Modelagem | séries temporais e ML (statsmodels / Prophet / gradient boosting) |
| Serving | aplicação web para o painel + serviço de geração de boletim e alertas |
| Orquestração | agendador de pipelines com controle de dependências e reprocessamento |

---

## 13. Roadmap

1. **Fase 1 — Ingestão:** conectores para API Recife (CKAN), COP Recife (ArcGIS) e API ANA (HidroWeb); RAW e camada padronizada ([decisão 0001](decisoes/0001-raw-mongodb-padronizada-neon.md)).
2. **Fase 2 — Integração:** Silver e Gold; tabela de referência territorial; indicadores reais no painel substituindo os dados simulados.
3. **Fase 3 — Predição:** modelos de chuva/nível/ocorrências/arboviroses; motor de classificação de risco e de alertas preditivos; boletim automático a partir da Gold.
4. **Fase 4 — Expansão:** fontes complementares (APAC, INMET, CPRH, MonitorAr, DATASUS) e novos indicadores ambientais e assistenciais.
