# `src/serving/`

Camada de entrega: leva a camada Gold para o usuário final. Ver
[`ARQUITETURA §7`](../../../docs/ARQUITETURA.md#7-camada-de-entrega-serving) e
[`§11`](../../../docs/ARQUITETURA.md#11-relação-com-o-protótipo).

## O que vive aqui

- **`exporta_painel.py`** — na primeira release ([decisão 0001](../../../docs/decisoes/0001-raw-mongodb-padronizada-neon.md)) lê a camada padronizada no
  Neon (arboviroses, `dim_bairro`, `dim_distrito`) e a malha de bairros da RAW do território, e grava
  `prototipo/dados/recife-real.js` (`window.AERVITA_DADOS = {bairros, epidemiologia}`), o formato que o console
  v3 já lê. Quando houver Gold (PNL-01/PNL-02), passa a ler de lá e a incluir KPIs, séries e alertas.

  ```bash
  python src/serving/exporta_painel.py --armazenamento mongo --data-territorio 2026-10-28
  ```
- **`boletim.py`** (issue PNL-03) — Gold → texto/Markdown via template em `conf/boletim/template.md`. Determinístico: mesmo Gold ⇒ mesmo boletim.

## Regras

- Só consome a camada Gold; nenhuma regra de negócio nova aqui.
- Sem serviço externo e sem modelo de linguagem na geração do boletim.
- O protótipo em [`prototipo/v3-aervita-console.html`](../../../frontend/prototipo/v3-aervita-console.html) é o alvo visual; trocar apenas a origem dos dados (simulados → JSON real).

## Saída

Arquivo(s) JSON para o painel e texto/Markdown do boletim (caminho definido na issue PNL-01).
