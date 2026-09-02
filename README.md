<div align="center">

# 🌧️ AerVita

### Vigilância e predição de desastres para o Recife/PE

Consolida dados **meteorológicos, hidrológicos, epidemiológicos, ambientais, assistenciais e territoriais**
num único fluxo — entregando indicadores situacionais, boletins automáticos e alertas preditivos.

<br>

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-f0ad4e?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)
![Metodologia](https://img.shields.io/badge/metodologia-CRISP--DM-1351b4?style=flat-square)
![Fontes](https://img.shields.io/badge/dados-Recife%20CKAN%20%2B%20ANA-0e8a16?style=flat-square)
![CESAR School](https://img.shields.io/badge/CESAR%20School-Projeto%205-071d41?style=flat-square)

<br>

[**Documentação**](#-documentação) ·
[**Arquitetura**](docs/ARQUITETURA.md) ·
[**Plano de ação**](docs/PLANO-DE-ACAO.md) ·
[**Issues**](https://github.com/Matheus-Barkokebas/avd-proj-classe/issues) ·
[**Project**](https://github.com/users/Matheus-Barkokebas/projects/1)

</div>

---

<div align="center">

**▶ Protótipo do painel situacional:** [`prototipo/v1-prototipo-aervita.html`](prototipo/v1-prototipo-aervita.html) — abra no navegador
<br><sub>mockup visual com <b>dados simulados</b> para demonstração</sub>

</div>

---

## Índice

- [O problema](#-o-problema)
- [A solução](#-a-solução)
- [Como funciona](#️-como-funciona)
- [Fontes de dados](#-fontes-de-dados)
- [Documentação](#-documentação)
- [Roadmap](#-roadmap)
- [Estrutura do repositório](#️-estrutura-do-repositório)
- [Desenvolvimento](#-desenvolvimento)
- [Contexto](#-contexto)

---

## 🎯 O problema

As informações que descrevem uma emergência climática no Recife estão **espalhadas** por dezenas de fontes
e sistemas. Consolidar chuva, nível de rios, ocorrências da Defesa Civil, casos de arboviroses e dados de
território é hoje um trabalho **manual, lento e sujeito a retrabalho** — o que atrasa boletins, dificulta
identificar as áreas prioritárias e mantém a resposta reativa.

## 💡 A solução

Um pipeline que coleta essas fontes automaticamente, padroniza tempo e território, cruza os domínios numa
**base única** (situação por distrito e por dia) e entrega três produtos:

| 📊 Painel situacional | 📄 Boletim automático | 🚨 Alertas preditivos |
|---|---|---|
| KPIs, risco por distrito, ocorrências e séries em tempo quase real | Texto consolidado (resumo, destaques, recomendação) pronto para distribuição | Disparados quando o risco **atual ou previsto** cruza um limiar |

---

## 🗺️ Como funciona

```text
   FONTES          API Dados Abertos Recife (CKAN)      API ANA (HidroWeb)      Fontes complementares (roadmap)
                              │                                │                           │
                              └────────────────┬───────────────┴───────────────────────────┘
                                               ▼
   INGESTÃO             Conectores por fonte + agendador (coleta periódica)
                                               ▼
   LAGO DE DADOS        RAW  ─►  BRONZE  ─►  SILVER  ─►  GOLD
                        original   tipado     limpo /     integrado
                                              padronizado  (distrito × dia)
                                               ▼
   ANÁLISE & MODELOS    Indicadores · classificação de risco · previsão de chuva / nível / arboviroses
                                               ▼
   ENTREGA             Painel situacional  ·  Boletim automático  ·  Alertas preditivos
                                               ▼
                                Priorização e alocação de equipes
```

Arquitetura medallion (RAW → Bronze → Silver → Gold): cada camada preserva a anterior e eleva a qualidade
do dado. Detalhe completo em **[`docs/ARQUITETURA.md`](docs/ARQUITETURA.md)**.

---

## 🔌 Fontes de dados

| Domínio | Fonte | Exemplos de dados |
|---|---|---|
| 🌧️ Meteorológico | APAC / INMET | chuva, temperatura, umidade, vento, previsão |
| 🌊 Hidrológico | **API ANA (HidroWeb)** · APAC | nível e vazão de rios, chuva acumulada, cotas de alerta |
| 🦠 Epidemiológico | **API Dados Abertos Recife** · Sec. de Saúde | dengue, zika, chikungunya por bairro e semana epidemiológica |
| 🌱 Ambiental | CPRH / MonitorAr | qualidade do ar e da água, balneabilidade |
| 🏥 Assistencial | **API Dados Abertos Recife** · DATASUS | atendimentos, solicitações, unidades de saúde |
| 🗺️ Territorial | **API Dados Abertos Recife** · COP Recife | bairros, RPA, áreas de risco, ocorrências georreferenciadas |

**APIs da 1ª fase:**
`dados.recife.pe.gov.br/pt_BR/api/action/datastore_search` · `www.ana.gov.br/hidrowebservice/`

---

## 📚 Documentação

| Documento | Conteúdo |
|---|---|
| [`docs/CRISP-DM.md`](docs/CRISP-DM.md) | Planejamento pela metodologia CRISP-DM — negócio, dados, preparação, modelagem, avaliação, implantação |
| [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) | Arquitetura-alvo: fontes, ingestão, camadas medallion, indicadores e entrega |
| [`docs/HISTORIAS.md`](docs/HISTORIAS.md) | 21 histórias de usuário detalhadas — escopo, critérios de aceitação e notas para IA |
| [`docs/PLANO-DE-ACAO.md`](docs/PLANO-DE-ACAO.md) | Porta de entrada: ordem das issues, caminho crítico e significado das siglas dos épicos |

**Gestão do trabalho:** [Issues #5–#31](https://github.com/Matheus-Barkokebas/avd-proj-classe/issues) ·
[Project **AerVita**](https://github.com/users/Matheus-Barkokebas/projects/1)

---

## 🧭 Roadmap

| Fase | Objetivo | Épicos |
|:---:|---|---|
| **1** | Fundação (estrutura, contratos, orquestração) + ingestão dos conectores Recife e ANA (RAW/Bronze) | `FND` · `ING` |
| **2** | Integração Silver/Gold, indicadores base e painel com dados reais | `INT` · `IND` · `PNL` |
| **3** | Classificação de risco, modelos preditivos, alertas e boletim automático | `IND` · `PRD` · `PNL` |
| **4** | Fontes complementares (APAC, INMET, CPRH, MonitorAr, DATASUS) | _roadmap_ |

---

## 🗂️ Estrutura do repositório

```text
docs/                       planejamento, arquitetura e histórias
prototipo/                  protótipo visual do painel situacional
extract_dados_recife.py     script inicial de extração (Dados Abertos Recife)
src/                        código do pipeline            ·  a criar — issue FND-01 (#5)
conf/                       configuração por fonte         ·  a criar — issue FND-01 (#5)
data/                       camadas RAW/Bronze/Silver/Gold ·  ignorada pelo Git
tests/                      testes automatizados           ·  a criar — issue FND-01 (#5)
```

---

## 🚀 Desenvolvimento

**Pré-requisitos:** Python 3.12+

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install requests
python extract_dados_recife.py
```

**Fluxo de contribuição:** 1 issue → 1 branch `feature/<id>-AAAA.MM.DD` → 1 PR contra `develop`.
Consulte **[`docs/PLANO-DE-ACAO.md`](docs/PLANO-DE-ACAO.md)** para saber qual issue pegar primeiro
(começa em **#5 · FND-01**).

---

## 👥 Contexto

Projeto acadêmico da disciplina de **Análise e Visualização de Dados** — **CESAR School** (Projeto 5).
Todos os dados utilizados são **públicos** e provenientes de fontes oficiais.

<div align="center"><sub>Feito com 🌧️ para o Recife</sub></div>
