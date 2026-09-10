# `conf/` — configuração declarativa

Configuração do pipeline em arquivos **YAML/CSV**, separada do código. Regra de negócio fica em
[`src/`](../src/); aqui só há *o quê* coletar e *como* interpretar cada fonte.

| Pasta | Conteúdo | Preenchida por |
|---|---|---|
| [`sources/`](sources/) | 1 arquivo por fonte: endpoint / `resource_id`, mapa de colunas, frequência | issues `ING-*` |
| [`contracts/`](contracts/) | schema esperado por fonte (campos, tipos, obrigatoriedade, chave de negócio) | issue FND-02 |
| [`territorio/`](territorio/) | referências territoriais: `aliases.csv` (bairros), `distrito_estacao.yml` | issues INT-02 / INT-04 |

Outros arquivos de configuração previstos (criados pelas issues correspondentes):
`risco/regras.yml` (IND-03), `alertas/regras.yml` (PRD-03), `boletim/template.md` (PNL-03).
O arquivo `schedule.yml` foi implementado pela FND-03 (ver abaixo).

## Frequências de coleta

[`schedule.yml`](schedule.yml) declara o fuso America/Recife e o mapa das fontes
da fase 1: epidemiologia diária, ocorrências diárias (horárias em contingência),
território mensal e ANA chuva/nível horários. Os nomes seguem `PADROES.md`;
saúde/arboviroses estão representadas por epidemiologia, conforme as histórias ING.
Fontes do roadmap e o dummy de teste não participam do agendamento.

O arquivo registra periodicidades, sem definir horários arbitrários. O futuro
agendador deverá interpretá-lo e chamar `src/ingestao/runner.py <fonte>` após a
integração dos coletores reais; FND-03 não instala nem inicia um agendador.

## Regras

- **Nunca** commitar segredos (tokens, senhas). Referenciar variável de ambiente pelo nome; manter um `.env.example` com as chaves em branco.
- Nomes de arquivo e chaves em `snake_case`, sem acento.
