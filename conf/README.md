# `conf/` — configuração declarativa

Configuração do pipeline em arquivos **YAML/CSV**, separada do código. Regra de negócio fica em
[`src/`](../src/); aqui só há *o quê* coletar e *como* interpretar cada fonte.

| Pasta | Conteúdo | Preenchida por |
|---|---|---|
| [`sources/`](sources/) | 1 arquivo por fonte: endpoint / `resource_id`, mapa de colunas, frequência | issues `ING-*` |
| [`contracts/`](contracts/) | schema esperado por fonte (campos, tipos, obrigatoriedade, chave de negócio) | issue FND-02 |
| [`territorio/`](territorio/) | referências territoriais: `aliases.csv` (bairros), `distrito_estacao.yml` | issues INT-02 / INT-04 |

Outros arquivos de configuração previstos (criados pelas issues correspondentes):
`risco/regras.yml` (IND-03), `alertas/regras.yml` (PRD-03), `boletim/template.md` (PNL-03),
`schedule.yml` (FND-03).

## Regras

- **Nunca** commitar segredos (tokens, senhas). Referenciar variável de ambiente pelo nome; manter um `.env.example` com as chaves em branco.
- Nomes de arquivo e chaves em `snake_case`, sem acento.
