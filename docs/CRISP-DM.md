# Planejamento do Projeto - Metodologia CRISP-DM

## 1. Entendimento do Negócio (Business Understanding)
- **Objetivo Geral:** Analisar as demandas e solicitações de atendimento registradas pelos cidadãos no município do Recife.
- **Perguntas de Negócio:**
  - Quais são os tipos de serviços mais solicitados?
  - Quais bairros concentram o maior volume de chamados?
  - Qual o tempo médio de resolução/resposta por secretaria ou tipo de serviço?
- **Critério de Sucesso:** Mapear padrões sazonais e geográficos para subsidiar a alocação preventiva de equipes públicas.

---

## 2. Entendimento dos Dados (Data Understanding)
- **Fonte de Dados:** Portal de Dados Abertos da Prefeitura do Recife (API CKAN).
- **Recurso Utilizado:** Solicitações de Atendimento (`solicitacoes-de-atendimento-2026`).
- **Volume e Granularidade:** Registros individuais com atributos temporais (data de abertura), espaciais (bairro, RPA, coordenadas) e tipológicos (grupo, serviço, status).
- **Exploração Inicial:** Identificação de valores ausentes em coordenadas geográficas, duplicidades e consistência no status do atendimento.

---

## 3. Preparação dos Dados (Data Preparation)
- **Filtragem e Limpeza:**
  - Tratamento de campos de data/hora para padrão `YYYY-MM-DD HH:MM:SS`.
  - Normalização de nomes de bairros e remoção de espaços em branco/caracteres especiais.
  - Imputação ou exclusão de registros com localização/serviço nulos.
- **Engenharia de Recursos (Feature Engineering):**
  - Criação de variáveis de tempo até resolução (`data_resposta - data_abertura`).
  - Categorização por Região Político-Administrativa (RPA).

---

## 4. Modelagem (Modeling)
- **Técnicas Previstas:**
  - **Análise Descritiva/Diagnóstica:** Agrupamento e agregação para identificar volumetria por bairro e categoria.
  - **Clustering / Análise Espacial:** Identificação de hotspots de solicitações por região.
  - **Séries Temporais / Classificação (se aplicável):** Previsão de demanda para períodos críticos (ex.: período de chuvas).

---

## 5. Avaliação (Evaluation)
- **Validação com os Objetivos de Negócio:**
  - Os agrupamentos refletem os gargalos reais dos serviços municipais?
  - As métricas de tempo de resposta identificam disparidades regionais?
- **Revisão:** Avaliar limitações nos dados reportados antes da tomada de decisão ou publicação.

---

## 6. Implantação (Deployment)
- **Entregáveis:**
  - Pipeline automatizado de ingestão (scripts Python na pasta `src/`).
  - Dashboard interativo / relatórios analíticos para visualização gerencial.
  - Documentação e versionamento no repositório Git.