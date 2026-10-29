# `api/` — API do painel

API em **FastAPI (Python 3.12)** entre o banco e o front-end: lê a camada padronizada no Neon e entrega JSON.
Só leitura. Ver [decisão 0002](../docs/decisoes/0002-api-fastapi-e-front-react.md).

```text
Front (React) ──► API (FastAPI) ──► Neon (camada padronizada, usuário só de leitura)
```

## Como rodar

Todos os comandos partem **desta pasta**:

```bash
cd api
python -m venv .venv && .venv\Scripts\activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                                  # NEON_DATABASE_URL do usuário aervita_api, só aqui
uvicorn app.main:app --reload                         # http://localhost:8000/docs
```

```bash
pytest                    # sem rede (repositório falso)
pytest -m integracao      # contra o Neon real, com o usuário só de leitura do .env
```

## Rotas (v1)

| Rota | Fonte no Neon | O que devolve |
|---|---|---|
| `GET /saude` | — | API e conexão com o banco (`503` se o banco cair) |
| `GET /v1/atualizacao` | todas | Quando cada tabela foi carregada pela última vez |
| `GET /v1/chuva/atual` | `cop_indicadores`, `cop_chuva_mensal` | Chuva 1h/24h, maior acumulado e estação, maré, estágio e o mês contra a média histórica |
| `GET /v1/chuva/serie?horas=72` | `cop_indicadores` | Série horária de chuva e maré |
| `GET /v1/chuva/previsao` | `cop_previsao_chuva` | Previsão hora a hora por modelo e a média dos modelos |
| `GET /v1/chuva/mensal?ano=` | `cop_chuva_mensal` | Chuva por mês vs. média histórica |
| `GET /v1/rios` | `cop_rios` | Última leitura por estação, com situação calculada contra as cotas (mais grave primeiro) |
| `GET /v1/rios/{codigo}/serie?horas=72` | `cop_rios` | Série do nível de uma estação |
| `GET /v1/arboviroses/semanas?agravo=` | `epidemiologia` | Notificações por semana epidemiológica e agravo |
| `GET /v1/arboviroses/bairros` | `epidemiologia`, `dim_bairro` | Notificações por bairro e distrito + o que não casou com a tabela oficial |
| `GET /v1/territorio/bairros` | `dim_bairro`, `dim_distrito` | Bairros com RPA e distrito |
| `GET /v1/territorio/distritos` | `dim_distrito` | Distritos sanitários |
| `GET /v1/territorio/bairros-geo` | `geo_bairro`, `dim_bairro` | Malha dos 94 bairros em GeoJSON, com distrito e RPA |
| `GET /v1/territorio/areas-alagaveis?distrito=` | `cop_areas_alagaveis` | Polígonos em GeoJSON |
| `GET /v1/territorio/pontos-alagamento` | `cop_pontos_alagamento` | Pontos em GeoJSON |

A documentação interativa (com o formato de cada resposta) fica em `/docs`; o esquema em `/openapi.json` é a
fonte dos tipos TypeScript do front.

## Convenções

- **Camadas:** `app/rotas/` → `app/servicos/regras.py` (regras puras) → `app/repositorios/neon.py` (único lugar com
  SQL) → Neon. Os testes trocam o repositório por um falso.
- **Datas** sempre com o fuso do Recife (`-03:00`). **Erros** sempre como `{"erro": "...", "detalhe": "..."}`:
  `nao_encontrado` (404), `parametro_invalido` (422), `banco_indisponivel` (503), `erro_interno` (500, sem detalhe).
- **Cache:** rotas `/v1` com `Cache-Control: public, max-age=API_CACHE_SEGUNDOS` (padrão 300).
- **CORS:** só as origens de `API_ORIGENS_CORS`.
- **Fronteira:** não importa código de [`pipeline/`](../pipeline/README.md). A normalização de nome de bairro é a
  mesma regra do pipeline, repetida aqui, com teste que compara as duas.
- **Segurança:** usuário `aervita_api` no Neon com `SELECT` apenas, e sessão aberta como `read_only`.
