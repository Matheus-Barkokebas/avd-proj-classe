# `src/serving/`

Camada de entrega: leva a camada Gold para o usuário final. Ver
[`ARQUITETURA §7`](../../docs/ARQUITETURA.md#7-camada-de-entrega-serving) e
[`§11`](../../docs/ARQUITETURA.md#11-relação-com-o-protótipo).

## O que vive aqui

- **`exporta_painel.py`** (issue PNL-01/PNL-02) — gera o JSON que o painel consome a partir do Gold (KPIs, situação por distrito, séries de 7 dias, alertas ativos). Contrato do JSON documentado aqui neste README quando a issue for feita.
- **`boletim.py`** (issue PNL-03) — Gold → texto/Markdown via template em `conf/boletim/template.md`. Determinístico: mesmo Gold ⇒ mesmo boletim.

## Regras

- Só consome a camada Gold; nenhuma regra de negócio nova aqui.
- Sem serviço externo e sem modelo de linguagem na geração do boletim.
- O protótipo em [`prototipo/v1-prototipo-aervita.html`](../../prototipo/v1-prototipo-aervita.html) é o alvo visual; trocar apenas a origem dos dados (simulados → JSON real).

## Saída

Arquivo(s) JSON para o painel e texto/Markdown do boletim (caminho definido na issue PNL-01).
