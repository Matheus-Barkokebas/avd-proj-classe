# `conf/territorio/`

Referências fixas de território do Recife, usadas na padronização geográfica (issues INT-02 e INT-04).

| Arquivo | Conteúdo | Issue |
|---|---|---|
| `aliases.csv` | grafias alternativas de bairro → nome canônico (`"boa viagem"; Boa Viagem`) | INT-02 |
| `distrito_estacao.yml` | associação distrito sanitário → estações ANA e rio de referência (com cotas) | INT-04 |

A tabela derivada `territorio_ref` (bairro ↔ RPA ↔ Distrito Sanitário ↔ geometria ↔ população)
é **gerada** na camada Silver a partir da Bronze de território (issue ING-05) — não fica aqui.
