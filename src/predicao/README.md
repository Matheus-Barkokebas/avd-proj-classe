# `src/predicao/`

Modelos preditivos e o motor de alertas. Ver
[`ARQUITETURA §6.3`](../../docs/ARQUITETURA.md#63-modelos-preditivos) e
[`§7`](../../docs/ARQUITETURA.md#7-camada-de-entrega-serving).

## O que vive aqui

- **`chuva_nivel.py`** (issue PRD-01) — previsão de chuva acumulada e nível de rio 24–48h por distrito.
- **`arboviroses.py`** (issue PRD-02) — previsão de notificações por bairro × semana epidemiológica.
- **`alertas.py`** (issue PRD-03) — motor de alertas: regras em `conf/alertas/regras.yml`, ciclo `aberto → atualizado → encerrado`, deduplicação.

## Regras

- Fonte única: camada Gold. Não recoletar nem refazer limpeza.
- Sempre começar por um **baseline sazonal ingênuo** e documentá-lo como referência a superar.
- Sem *data leakage*: features usam apenas informação disponível no instante da previsão (teste específico exigido).
- Modelos treinados vão para `models/` (fora de `data/`, ignorado pelo Git); métricas de backtesting em `docs/AVALIACAO_MODELOS.md`.

## Saída

```
models/                     # artefatos serializados (nao versionados)
data/gold/alertas/
```
