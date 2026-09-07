# `data/` — lago de dados (não versionado)

Arquitetura **medallion**. Todo o conteúdo é **regenerável** pelos pipelines em [`src/`](../src/)
e está no `.gitignore` — só a estrutura de pastas (`.gitkeep`) e este README são versionados.

| Camada | Pasta | Conteúdo | Formato |
|---|---|---|---|
| **RAW** | `raw/` | resposta original das APIs, intacta | JSON / CSV, como veio |
| **BRONZE** | `bronze/` | dados tipados, 1 linha por registro | Parquet |
| **SILVER** | `silver/` | limpo, deduplicado, tempo e território padronizados | Parquet |
| **GOLD** | `gold/` | tabelas integradas e indicadores (grão distrito/bairro × dia) | Parquet |

## Particionamento

```
data/<camada>/<fonte>/AAAA/MM/DD/<arquivo>
```

Exemplo: `data/raw/epidemiologia/2026/09/06/datastore_search.json`.
Detalhes e demais convenções em [`docs/PADROES.md`](../docs/PADROES.md).

## Como (re)gerar

Cada história `ING-*` / `INT-*` produz uma camada. Ponto de partida legado:
`python extract_dados_recife.py` (será substituído pelo `runner` da issue FND-03).
