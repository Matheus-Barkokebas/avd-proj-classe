# `data/` — lago de dados (não versionado)

Arquitetura **medallion**. Todo o conteúdo é **regenerável** pelos pipelines em [`src/`](../src/)
e está no `.gitignore` — só a estrutura de pastas (`.gitkeep`) e este README são versionados.

| Camada | Pasta | Conteúdo | Formato |
|---|---|---|---|
| **RAW** | `raw/` | resposta original das APIs, intacta | JSON / CSV, como veio |
| **BRONZE** | `bronze/` | dados tipados, 1 linha por registro | Parquet |
| **BRONZE (quarentena)** | `bronze/<fonte>_rejeitados/` | linhas que violaram o contrato, com o motivo (BUG-06) | JSON |

`silver/` e `gold/` voltam quando a integração (Fase 2) começar; nesta release a camada padronizada fica no Neon.

> **Primeira release ([decisão 0001](../../docs/decisoes/0001-raw-mongodb-padronizada-neon.md)):** com `--armazenamento mongo` a RAW vai para o
> MongoDB Atlas, e com `--padronizada neon` os dados validados vão para o Neon. Nesses modos nada é gravado
> aqui; sem as opções, esta pasta continua sendo o destino padrão.

## Particionamento

```
data/<camada>/<fonte>/AAAA/MM/DD/<arquivo>
```

Exemplo: `data/raw/epidemiologia/2026/09/06/datastore_search.json`.
Detalhes e demais convenções em [`docs/PADROES.md`](../../docs/PADROES.md).

## Como (re)gerar

Cada história `ING-*` / `INT-*` produz uma camada. A ingestão (RAW + Bronze) é feita
pelos coletores de `src/ingestao/` — ex.: `python src/ingestao/epidemiologia.py`.
