# Padrões do Projeto — AerVita

Convenções que valem para todo o repositório. Estabelecidas na issue **FND-01**; alterações
passam por PR e alinhamento do time.

Complementa: [`ARQUITETURA.md`](ARQUITETURA.md) (o *como* técnico) e
[`PLANO-DE-ACAO.md`](PLANO-DE-ACAO.md) (ordem do trabalho).

---

## 1. Estrutura de pastas

```text
src/            código do pipeline (um subdir por etapa do fluxo de dados)
  ingestao/       conectores + coleta por fonte           → RAW, Bronze
  processamento/  limpeza, padronização, integração       → Silver, Gold
  indicadores/    indicadores situacionais e risco        → Gold
  predicao/       modelos preditivos e motor de alertas    → Gold
  serving/        boletim, exportações, API interna        → entrega
conf/           configuração declarativa (YAML/CSV), sem lógica
  sources/        1 arquivo por fonte (endpoint, colunas, frequência)
  contracts/      schema esperado por fonte (validação de entrada)
  territorio/     referências fixas de território
data/           lago de dados — IGNORADO pelo Git (regenerável)
  raw/ bronze/ silver/ gold/
notebooks/      exploração de dados (rascunho, não produção)
tests/          testes automatizados — espelha src/
docs/           planejamento, arquitetura, histórias, padrões
prototipo/      protótipo visual do painel
```

Regras:

- Código de produção vive em `src/`, com teste correspondente em `tests/`.
- `conf/` não contém regra de negócio — apenas *o quê* e *como interpretar* cada fonte.
- Nada em `data/` é versionado (ver §4).

---

## 2. Nomenclatura

| Item | Regra | Exemplo |
|---|---|---|
| Pastas e arquivos `.py` | `snake_case`, sem acento | `silver_ocorrencias.py` |
| Módulo por fonte/etapa | nome da fonte ou da etapa | `ingestao/epidemiologia.py` |
| Funções e variáveis | `snake_case`, **português sem acento** | `resolver_territorio`, `chuva_acumulada_24h` |
| Tabelas e colunas (Bronze+) | `snake_case`, sem acento, sem espaço | coluna `data_notificacao`, tabela `situacao_distrito_dia` |
| Arquivos de config | `snake_case.yml` | `conf/sources/ana_estacoes.yml` |
| Notebooks | `NN-descricao-curta.ipynb` | `01-exploracao-epidemiologia.ipynb` |
| Testes | `test_<modulo>.py` | `tests/ingestao/test_recife_ckan.py` |

- **Idioma:** identificadores e nomes de coluna em português sem acento. Comentários e docstrings em português.
- Categorias vindas das fontes (ex.: `agravo`, `tipo_ocorrencia`, `status`) são padronizadas para minúsculas sem acento na camada Silver.
- Nomes de bairro: forma canônica definida em `conf/territorio/aliases.csv`.

---

## 3. Datas e tempo

- **Formato padrão:** `YYYY-MM-DD HH:MM:SS` (sem fração de segundo).
- **Fuso:** todos os timestamps normalizados para **America/Recife (UTC−03, sem horário de verão)**.
  Se a fonte entregar em UTC, converter na camada Silver e registrar a origem.
- **Data só (sem hora):** `YYYY-MM-DD`.
- **Chaves de calendário** (geradas em `processamento/calendario.py`, issue INT-01):
  `ano`, `mes`, `semana_iso`, `semana_epidemiologica`, `dia_semana`, `periodo_chuvoso` (bool).
- **Semana epidemiológica:** definição oficial (SE 01 = semana que contém o primeiro sábado do ano);
  atenção às viradas de ano (31/12 e 01/01 podem cair em SE do outro ano).
- **Período chuvoso do Recife:** meses de **março a agosto** (parâmetro; ajustável em INT-01 com base no histórico).
- **Janelas móveis** (ex.: chuva acumulada 24h/72h) são calculadas na camada Gold / indicadores, não na ingestão.

---

## 4. Camadas de dados e particionamento

Arquitetura medallion — ver [`ARQUITETURA §4`](ARQUITETURA.md#4-camadas-de-armazenamento-medallion).

| Camada | Papel | Formato |
|---|---|---|
| RAW | resposta original das APIs, intacta | JSON / CSV, como veio |
| Bronze | tipada, 1 linha por registro | Parquet |
| Silver | limpa, deduplicada, tempo e território padronizados | Parquet |
| Gold | integrada, indicadores (grão distrito/bairro × dia) | Parquet |

**Particionamento no disco:**

```text
data/<camada>/<fonte>/AAAA/MM/DD/<arquivo>
```

- `<camada>` ∈ `raw | bronze | silver | gold`; `<fonte>` = nome em `conf/sources/` (ex.: `epidemiologia`, `ocorrencias`, `ana_chuva`, `ana_nivel`, `territorio`).
- `AAAA/MM/DD` = **data da coleta** (para RAW/Bronze) ou **data de referência do dado** (para Gold), documentado por tabela.
- Ex.: `data/raw/epidemiologia/2026/09/06/datastore_search.json`.

> Nota: a issue FND-01 citou a forma abreviada `<fonte>/<camada>/…`; a ordem **`<camada>/<fonte>/…`**
> adotada aqui segue a estrutura de pastas de `data/` e os critérios de aceitação de `ING-02`/`ING-03`.

**Versionamento:** `data/` inteira está no `.gitignore`. Só são versionados os `.gitkeep` e os `README.md`.
Nunca commitar dado real. Qualquer camada é reconstruível a partir da RAW.

---

## 5. Configuração e segredos

- Uma fonte = um arquivo em `conf/sources/`. Um contrato = um arquivo em `conf/contracts/`.
- **Segredos (tokens, senhas) nunca no repositório.** A config referencia o *nome* de uma variável
  de ambiente (`segredo_env: ANA_TOKEN`); o valor vem do ambiente / de um `.env` local.
- Manter `.env.example` com as chaves em branco. `.env` está no `.gitignore`.
- Parâmetros de modelo/regra (limiares de risco, janelas) ficam em YAML (`conf/risco/`, `conf/alertas/`),
  não *hard-coded* no `.py`.

---

## 6. Testes

- Framework: **pytest**. Rodar da raiz: `pytest`.
- `tests/` espelha `src/`. Arquivo `test_<modulo>.py`.
- **Sem rede:** toda resposta de API é mockada; amostras de dados em `tests/fixtures/`.
- Cada história entrega, no mínimo, os casos listados nos **Critérios de aceitação** da sua issue.
- PR só entra em revisão com a suíte passando.

---

## 7. Git

### Branches

- Trabalho a partir de `develop`. `main` = versão estável.
- Uma issue = uma branch = um PR.
- Nome: **`feature/<id-issue-minusculo>-AAAA.MM.DD`**
  - ex.: `feature/fnd-01-2026.09.06`, `feature/ing-02-2026.09.10`.
- Outros prefixos quando não houver issue: `fix/`, `docs/`, `chore/` + `-AAAA.MM.DD`.

### Commits

- Mensagem em português, imperativo/curto no assunto; corpo explica o *porquê* quando útil.
- Encerrar com o trailer:

  ```text
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  ```

  (quando houver co-autoria de IA).

### Pull Requests

- Alvo: `develop`. Descrição referencia a issue com `Closes #<n>`.
- Checklist da **Definição de Feito** (ver [`HISTORIAS.md`](HISTORIAS.md)) marcada.
- Pelo menos 1 revisão de outra pessoa do time antes do merge.
- Mover o card no [Project AerVita](https://github.com/users/Matheus-Barkokebas/projects/1): `Doing → Review → Done`.

---

## 8. Ambiente e dependências

- **Python 3.12+.** Ambiente virtual em `.venv/` (ignorado).
- Dependências mínimas e justificadas no PR que as introduz. Bibliotecas geoespaciais
  (`shapely`/`geopandas`) e de série temporal (`statsmodels`/`prophet`) são aceitáveis nas
  histórias que as exigem — registrar no PR.
- Quando existir `requirements.txt` (ou `pyproject.toml`), mantê-lo atualizado no mesmo PR.
