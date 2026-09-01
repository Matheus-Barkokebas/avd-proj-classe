# Arquitetura do Projeto — Vigidesastres

> **Projeto:** Vigidesastres — Painel Situacional para Preparação e Resposta a Emergências Climáticas (Recife/PE)
> **Escopo:** consolidar fontes meteorológicas, hidrológicas, epidemiológicas, ambientais, assistenciais e territoriais em um único fluxo de dados, permitindo cruzamentos, indicadores situacionais, boletins automáticos e alertas preditivos.
> **Estado atual:** existe um protótipo visual do painel ([`prototipo/v1-prototipo-aervita.html`](../prototipo/v1-prototipo-aervita.html)) com dados simulados. Este documento descreve a arquitetura-alvo para alimentá-lo com dados reais.

---

## 1. Visão Geral

O fluxo do projeto vai da **coleta nas APIs públicas** até a **entrega de indicadores e alertas** para as equipes de resposta, passando por um **lago de dados em camadas (arquitetura medallion)**.

```text
   FONTES              API Recife (CKAN)      API ANA (HidroWeb)      Fontes complementares (roadmap)
                              │                       │                          │
                              └───────────────┬───────┴──────────────────────────┘
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
| 🌧️ Meteorológicos | APAC / INMET | chuva, temperatura, umidade, vento, previsão, estações meteorológicas |
| 🌊 Hidrológicos | APAC / ANA | nível de rios, chuva acumulada, estações fluviométricas, risco de inundação |
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

### 2.4 Fontes complementares (roadmap)

APAC, INMET, CPRH, MonitorAr e DATASUS entram em fases posteriores para reforçar previsão meteorológica, qualidade ambiental e dados assistenciais federais. A arquitetura já prevê um **conector por fonte**, então a inclusão é incremental.

### 2.5 Frequência de atualização

| Fonte | Domínio | Atualização típica | Coleta no projeto |
|---|---|---|---|
| API Recife — arboviroses / saúde | Epidemiológico / Assistencial | semanal (semana epidemiológica) | diária (captura incremental) |
| API Recife — ocorrências / Defesa Civil | Territorial / Assistencial | diária / sob demanda | diária (horária em contingência) |
| API Recife — territorial (bairros, RPA, áreas de risco) | Territorial | eventual (cadastral) | mensal |
| API ANA — nível de rios / chuva | Hidrológico / Meteorológico | horária / sub-diária | horária |
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
Conector Recife (CKAN)      Conector ANA (HidroWeb)      Conector <fonte futura>
   │                            │                            │
   └───────────────┬────────────┴────────────────────────────┘
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
| **Painel Situacional** | O protótipo `v1-prototipo-aervita.html` evoluído: KPIs, situação por distrito, alertas e gráficos alimentados pela camada Gold |
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
| Coleta hidrológica/meteorológica (ANA) | horária | agendador |
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
- **Reprodutibilidade:** qualquer camada é reconstruível a partir da RAW.

---

## 11. Relação com o Protótipo

O protótipo atual usa **dados simulados**. O mapeamento abaixo indica de onde cada elemento passará a ser alimentado.

| Elemento do painel | Indicador | Fonte primária | Camada |
|---|---|---|---|
| KPI *Chuva acumulada · 24h* | soma de precipitação nas últimas 24h | ANA / APAC / INMET | Gold |
| KPI *Distritos em atenção* | contagem de distritos com risco ≥ moderado | regra de classificação de risco | Gold |
| KPI *Alertas ativos* | alertas abertos no período | motor de alertas | Serving |
| KPI *População em áreas de risco* | população estimada nas áreas expostas | territorial Recife (áreas de risco) + malha populacional | Gold |
| Tabela *Situação por Distrito Sanitário* | risco, chuva, população exposta, ocorrência | cruzamento chuva × território × ocorrências | Gold |
| Painel *Alertas Ativos* | fila de alertas priorizados | motor de alertas preditivos | Serving |
| Gráfico *Volume de chuva diário* | série de 7 dias | ANA / APAC / INMET | Gold |
| Gráfico *Notificações de arboviroses* | casos/dia por semana epidemiológica | API Recife (epidemiologia) | Gold |
| *Boletim Situacional Automático* | texto consolidado | template + indicadores da Gold | Serving |

---

## 12. Stack de Referência

Sugestão de tecnologias por camada (a definir na implementação):

| Camada | Opções de referência |
|---|---|
| Ingestão | Python + biblioteca HTTP + agendador (cron / orquestrador de pipelines) |
| Armazenamento | data lake em arquivos colunares (Parquet / Delta), organizado em RAW/Bronze/Silver/Gold |
| Processamento | transformações em lote (SQL analítico ou dataframes) |
| Modelagem | séries temporais e ML (statsmodels / Prophet / gradient boosting) |
| Serving | aplicação web para o painel + serviço de geração de boletim e alertas |
| Orquestração | agendador de pipelines com controle de dependências e reprocessamento |

---

## 13. Roadmap

1. **Fase 1 — Ingestão:** conectores para API Recife (CKAN) e API ANA (HidroWeb); camadas RAW e Bronze.
2. **Fase 2 — Integração:** Silver e Gold; tabela de referência territorial; indicadores reais no painel substituindo os dados simulados.
3. **Fase 3 — Predição:** modelos de chuva/nível/ocorrências/arboviroses; motor de classificação de risco e de alertas preditivos; boletim automático a partir da Gold.
4. **Fase 4 — Expansão:** fontes complementares (APAC, INMET, CPRH, MonitorAr, DATASUS) e novos indicadores ambientais e assistenciais.
