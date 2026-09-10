# `src/processamento/`

Transforma a camada Bronze em Silver (limpa/padronizada) e depois em Gold (integrada).
Ver [`ARQUITETURA §4`](../../docs/ARQUITETURA.md#4-camadas-de-armazenamento-medallion) e
[`§5`](../../docs/ARQUITETURA.md#5-camada-de-processamento-e-integração).

## O que vive aqui

- **`calendario.py`** (issue INT-01) — dimensão de calendário, semana epidemiológica, `para_timestamp_padrao`, `periodo_chuvoso`.
- **`territorio.py`** (issue INT-02) — tabela `territorio_ref` e `resolver_territorio(nome | lat, lon)`.
- **`silver_<fonte>.py`** (issue INT-03) — uma função de limpeza por fonte: dedupe, datas, território, categorias, coluna `flags`.
- **`gold_situacao.py`** (issue INT-04) — tabela integrada `situacao_distrito_dia` (cruzamento chuva × ocorrências × arboviroses × território).

## Regras

- Reutilizar `calendario.py` e `territorio.py` — não reimplementar padronização de tempo/território em cada módulo.
- Nunca descartar linha em silêncio: registrar o motivo em `flags` e num log de reconciliação (contagem Bronze → Silver).
- Gold é a única camada que outras etapas (`indicadores/`, `predicao/`, `serving/`) devem consumir.

## Saída

```
data/silver/<fonte>/
data/gold/situacao_distrito_dia/   data/gold/situacao_bairro_dia/
```
