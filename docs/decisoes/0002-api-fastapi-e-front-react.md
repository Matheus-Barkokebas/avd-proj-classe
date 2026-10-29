# 0002 · API em FastAPI e front-end em React + TypeScript (release 2)

- **Status:** Aceita pelo responsável do projeto em 2026-10-29; aguardando revisão do time (CODEOWNERS)
- **Data:** 2026-10-29
- **Escopo:** release 2 — entrega dos dados da camada padronizada para o painel

## Contexto

A release 1 ([decisão 0001](0001-raw-mongodb-padronizada-neon.md)) deixou no Neon, validados, os dados de
arboviroses, território e chuva e rios do COP Recife. O protótipo do painel (`frontend/prototipo/`) é um
HTML único com dados embutidos; para ligar as telas aos dados reais é preciso:

- um serviço entre o banco e o navegador (o navegador nunca pode ter a senha do banco);
- um front-end que comporte as telas do protótipo (menu lateral, painel de detalhe, tabelas, mapa, gráficos)
  com mais de uma pessoa mexendo.

O repositório já é um monorepo com `pipeline/`, `api/` e `frontend/`.

## Decisão

### API — Python 3.12 + FastAPI (`api/`)

- **Só leitura**, com um usuário do Neon só de leitura (`aervita_api`): `SELECT` liberado, `INSERT`, `DELETE` e
  `CREATE` negados (conferido em 2026-10-29). A sessão também é aberta como `read_only`.
- **Camadas:** `rotas` → `servicos` (regras puras) → `repositorios` (único lugar com SQL) → Neon.
- **SQL puro com psycopg 3 e pool de conexões**, sem ORM: as consultas são agregações de leitura.
- **Contrato com o front:** modelos Pydantic, publicados em OpenAPI (`/docs`, `/openapi.json`), de onde o front
  gera os tipos TypeScript.
- **Fronteira com o pipeline:** a API não importa código do pipeline; o contrato entre os dois é o esquema das
  tabelas no Neon. A única regra repetida (normalização do nome de bairro) tem teste que compara as duas.
- Rotas versionadas (`/v1/...`), erros num formato único (`{"erro", "detalhe"}`), `Cache-Control` nas rotas de
  dados, CORS só para as origens do front, datas sempre com o fuso do Recife (`-03:00`).

### Front-end — React + TypeScript (Vite) (`frontend/`)

- Componentes para as peças do protótipo; tipos gerados do OpenAPI da API.
- Bibliotecas previstas: MapLibre GL ou Leaflet (mapa), TanStack Query (atualização periódica), Recharts ou
  ECharts (séries).

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Front falando direto com o Neon | Exporia a senha do banco no navegador |
| API em Node (Express/Nest) ou Next.js | Segunda linguagem no back-end; o time e o pipeline já são Python |
| ORM (SQLAlchemy) | Só leitura e agregações: SQL puro é mais claro e não acrescenta dependência |
| Angular | Válido, mas curva de aprendizado maior e menos integrações prontas de mapa e gráfico para este escopo |
| Streamlit / Dash | Não reproduz o console (menu lateral, painel de detalhe, paleta de comandos, fluxo de despacho) |

**Revisão prevista:** se a equipe técnica da Vigidesastres padronizar outra tecnologia, esta decisão é revista.

## Consequências

- Mais um serviço para hospedar e manter (a API), com deploy ainda a definir — de preferência perto do Neon
  (`us-east-2`).
- A API fica sem autenticação enquanto só servir dados públicos; ocorrências e equipes, se entrarem, exigem login.
- Cada módulo tem dependências, testes e job de CI próprios.

## Estado da implementação

| Item | Situação |
|---|---|
| API: `/saude`, `/v1/atualizacao`, chuva (atual, série, previsão, mensal), rios (+ série por estação), arboviroses (semanas, bairros), território (bairros, distritos, áreas alagáveis, pontos de alagamento) | Feita: 34 testes sem rede e 15 de integração contra o Neon real |
| Job de CI da API | Feito (`.github/workflows/api.yml`, roda só quando `api/` muda) |
| Front-end React | A fazer |
| Deploy da API | A definir |
