# Planejamento do Projeto — Metodologia CRISP-DM

> **Projeto:** Análise das Solicitações de Atendimento do Recife
> **Fonte central:** Portal de Dados Abertos da Prefeitura do Recife (CKAN) — recurso `solicitacoes-de-atendimento-2026`
> **Objetivo em uma frase:** consolidar e analisar as solicitações de atendimento registradas pelos cidadãos para identificar padrões temporais, geográficos e tipológicos que apoiem a alocação preventiva de equipes e a priorização de serviços públicos.

---

## 1. Entendimento do Negócio (Business Understanding)

Hoje as demandas dos cidadãos chegam por diversos canais e ficam **dispersas**, sem uma visão consolidada que permita cruzar tipo de serviço, localização e tempo de resposta. Isso torna a atuação das equipes reativa e dificulta o planejamento.

A solução busca reduzir os seguintes problemas:

- Visão fragmentada das demandas, sem consolidação por bairro, serviço e período;
- Alocação reativa de equipes, sem antecipação de picos sazonais (ex.: chuvas, poda de árvores, limpeza urbana);
- Dificuldade de identificar rapidamente bairros e serviços prioritários para intervenção;
- Baixa previsibilidade de volume de chamados por região;
- Pouca base quantitativa para boletins de gestão, notas técnicas e relatórios;
- Ausência de indicadores padronizados de tempo de resposta e de disparidade regional.

### Perguntas de negócio

- Quais serviços são mais solicitados e como esse volume varia ao longo do ano?
- Quais bairros / RPAs concentram o maior volume de chamados e o maior tempo de resolução?
- Existe sazonalidade clara (ex.: alagamentos e quedas de árvore no período chuvoso)?
- Há disparidade regional no tempo médio de resposta entre secretarias / tipos de serviço?
- É possível antecipar picos de demanda por região e categoria de serviço?

### Critérios de sucesso

- **De negócio:** mapear padrões que permitam antecipar demanda e realocar equipes preventivamente; evidenciar e reduzir o tempo médio de resposta em serviços críticos.
- **Técnico:** pipeline reprodutível (RAW → Gold), dashboard analítico e um modelo de previsão de volume validado contra o histórico com erro aceitável (ex.: MAPE dentro de faixa acordada).

### Premissas e restrições

- Uso exclusivo de dados públicos, sem dados pessoais identificáveis;
- Completude e periodicidade dependem do que a Prefeitura publica no portal;
- Granularidade e disponibilidade de datas de conclusão podem limitar a análise de tempo de resposta.

---

## 2. Entendimento dos Dados (Data Understanding)

A base central é o recurso de **Solicitações de Atendimento**, complementado por fontes auxiliares para contextualizar território e sazonalidade.

| Domínio | Fonte de dados | Uso na análise |
|---|---|---|
| **Solicitações / Ouvidoria** | Dados Abertos Recife (`solicitacoes-de-atendimento-2026`, CSV com delimitador `;`) | Base principal: grupo/serviço, status, datas de abertura e conclusão, bairro, RPA, coordenadas |
| **Territorial** | Dados Abertos Recife / IBGE | Malha de bairros e RPAs, população por bairro para normalizar o volume per capita |
| **Climático** (complementar) | APAC / INMET | Explicar sazonalidade de serviços sensíveis a chuva (alagamento, deslizamento, queda de árvore) |
| **Calendário** (derivado) | Gerado no pipeline | Ano, mês, semana, dia da semana, feriados, marcação de período chuvoso |

### Atributos esperados no recurso principal

- **Temporais:** data/hora de abertura, data de conclusão/resposta, status atual;
- **Espaciais:** bairro, RPA / microrregião, latitude e longitude;
- **Tipológicos:** grupo de serviço, serviço, canal de entrada, órgão responsável.

### Exploração inicial (o que verificar)

- Disponibilidade da API e periodicidade de atualização do recurso;
- Volume total de registros e intervalo de datas coberto;
- Completude de coordenadas, bairro e data de conclusão;
- Cardinalidade e padronização de `grupo`, `serviço` e `bairro`;
- Duplicidades (mesmo protocolo repetido);
- Consistência do fluxo de status (aberto → em andamento → concluído);
- Outliers no tempo de resolução (valores negativos, prazos de anos).

---

## 3. Preparação dos Dados (Data Preparation)

A extração é feita a partir da **API / fontes públicas** e o armazenamento segue uma **arquitetura em camadas (medallion)**, preservando o dado original e evoluindo a qualidade a cada etapa.

| Camada | Conteúdo | Objetivo |
|---|---|---|
| **RAW** | Cópia fiel do CSV/JSON baixado, sem transformação | Rastreabilidade e reprocessamento |
| **BRONZE** | Dados tipados e materializados (Parquet / Delta Tables), 1 linha = 1 solicitação | Padronizar formato e esquema |
| **SILVER** | Dados limpos, normalizados e enriquecidos | Garantir qualidade e consistência |
| **GOLD** | Tabelas agregadas e prontas para análise, modelagem e dashboard | Consumo analítico |

### Tratamentos na camada Silver

- Padronização de datas/horas para o formato `YYYY-MM-DD HH:MM:SS`;
- Normalização de nomes de bairros (acentuação, caixa, espaços) e vínculo com a RPA correspondente;
- Tratamento de valores nulos em localização/serviço (imputação por regra ou exclusão sinalizada);
- Remoção de duplicidades por protocolo;
- Padronização das categorias de `grupo`, `serviço` e `status`;
- Tratamento de inconsistências temporais (conclusão anterior à abertura);
- Validação de coordenadas dentro do polígono do município;
- Padronização das informações territoriais (bairro ↔ RPA ↔ microrregião).

### Engenharia de atributos (Silver → Gold)

- `tempo_resolucao = data_conclusao - data_abertura` (em horas e dias);
- Recortes temporais: ano, mês, semana, dia da semana, período chuvoso (sim/não);
- Agregações de volume por bairro, RPA, serviço e mês;
- Volume normalizado pela população do bairro;
- Indicadores de prazo estourado por tipo de serviço (quando houver referência de SLA).

### Fluxo de preparação

```text
API / Dados Abertos Recife (CSV ";")
              ↓
             RAW  (cópia original preservada)
              ↓
      Tipagem + Parquet / Delta Tables
              ↓
           BRONZE  (1 linha = 1 solicitação)
              ↓
   Limpeza · normalização · enriquecimento
              ↓
           SILVER  (dados confiáveis)
              ↓
   Agregações · features · cruzamentos
              ↓
            GOLD  (pronto para análise e modelo)
```

---

## 4. Modelagem (Modeling)

### Etapa 1 — Análise diagnóstica

Compreender o comportamento das solicitações ao longo do tempo e do território, analisando:

- Sazonalidade (mensal e por período chuvoso);
- Tendências de crescimento ou queda por serviço;
- Variações e picos associados a eventos (chuvas fortes, grandes eventos na cidade);
- Ranking de serviços e bairros por volume e por tempo de resolução;
- Relação entre chuva e volume de serviços sensíveis ao clima.

### Etapa 2 — Padrões e cruzamentos

- Cruzamento entre solicitações × território × clima × calendário;
- Segmentação / clustering de bairros por perfil de demanda;
- Análise espacial para identificação de *hotspots* (concentração geográfica de chamados).

### Etapa 3 — Modelos preditivos

- Previsão de volume de solicitações por região e tipo de serviço (séries temporais — SARIMA / Prophet — ou modelos de *gradient boosting*);
- (Opcional) Classificação do risco de estouro de prazo por solicitação;
- Estimativa antecipada de picos de demanda para janelas críticas.

### Fluxo da modelagem

```text
GOLD (dados históricos)
        ↓
Análise Diagnóstica
        ↓
Sazonalidade · Tendências · Picos
        ↓
Cruzamento (território · clima · calendário)
        ↓
Identificação de Padrões / Hotspots
        ↓
Modelos Preditivos (volume por região e serviço)
        ↓
Estimativa de Demanda Futura
```

---

## 5. Avaliação (Evaluation)

### Validação frente aos objetivos de negócio

- Os padrões identificados refletem os gargalos reais dos serviços municipais?
- As métricas de tempo de resposta evidenciam disparidade entre regiões?
- A previsão de demanda é confiável o suficiente para orientar a realocação de equipes?

### Aspectos avaliados

- Qualidade e completude dos dados nas camadas Silver e Gold;
- Consistência dos padrões diagnósticos (robustez a diferentes recortes temporais);
- Desempenho dos modelos preditivos (MAE / MAPE para volume; precisão e *recall* para risco de prazo);
- Comparação entre demanda prevista e observada (*backtesting*);
- Utilidade prática dos resultados para as equipes técnicas e para a gestão;
- Limitações e possíveis vieses dos dados publicados.

### Revisão

Avaliar as limitações antes de publicar resultados ou embasar decisões, documentando as premissas assumidas.

---

## 6. Implantação (Deployment)

### Entregáveis

- **Pipeline reprodutível** de ingestão e transformação (scripts Python em `src/`, camadas RAW → Gold), regenerável a partir do `extract_dados_recife.py` e das etapas subsequentes;
- **Dashboard de monitoramento** com volume por bairro/RPA/serviço, sazonalidade e tempo de resposta;
- **Relatórios / boletins analíticos** periódicos;
- (Opcional) **Alertas preditivos** de pico de demanda por região e tipo de serviço;
- Documentação e versionamento no repositório Git.

### A solução permitirá

- Monitorar indicadores de demanda e de tempo de resposta;
- Visualizar bairros e serviços prioritários;
- Antecipar picos sazonais e realocar equipes preventivamente;
- Agilizar a produção de boletins e notas técnicas;
- Apoiar a decisão gestora com base quantitativa.

### Fluxo de implantação

```text
                  GOLD
                    ↓
           Modelos Preditivos
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
    Dashboard           Alertas Preditivos
        ↓                       ↓
   Visualização            Notificação
        └───────────┬───────────┘
                    ↓
     Priorização e Alocação de Equipes
```
