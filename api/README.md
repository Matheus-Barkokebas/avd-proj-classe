# `api/` — API do painel (em construção)

API em **FastAPI (Python)** entre o banco e o front-end. Lê a camada padronizada no Neon e entrega JSON.

- **Por que existe:** o navegador nunca pode falar direto com o Neon — a senha do banco ficaria exposta.
- **Fronteira:** não importa código de [`pipeline/`](../pipeline/README.md). O contrato entre os dois é o
  esquema das tabelas no Neon (geradas a partir de `pipeline/conf/contracts/`).
- **Primeiros endpoints previstos:** chuva (`cop_indicadores`, `cop_chuva_mensal`), rios com cotas
  (`cop_rios`), arboviroses por semana e bairro (`epidemiologia`), bairros e distritos (`dim_bairro`, `dim_distrito`).
- Terá `requirements.txt`, testes e job de CI próprios quando o código entrar.
