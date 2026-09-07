# `src/indicadores/`

Calcula, sobre a camada Gold, os indicadores situacionais e o nível de risco por distrito.
Ver [`ARQUITETURA §6.2`](../../docs/ARQUITETURA.md#62-indicadores-situacionais-gold) e
[`§6.4`](../../docs/ARQUITETURA.md#64-classificação-de-risco).

## O que vive aqui

- **`meteo_hidro.py`** (issue IND-01) — chuva acumulada 24h vs. média histórica, nível vs. cota de alerta, tendência, série de 7 dias.
- **`populacao_exposta.py`** (issue IND-02) — população estimada em áreas de risco por distrito.
- **`risco.py`** (issue IND-03) — `classificar_risco(linha_gold)` → nível (`baixo`/`moderado`/`alto`/`critico`) + justificativa, a partir de regras em [`conf/risco/regras.yml`](../../conf/).

## Regras

- Funções puras sobre o Gold — sem coleta, sem I/O de rede.
- O motor de risco é **determinístico e parametrizável por YAML** — sem ML.
- Sem dados suficientes → indicador `indisponível` / risco `indeterminado`, nunca erro.

## Saída

```
data/gold/indicadores_meteo_hidro/
data/gold/risco_distrito_dia/
```
