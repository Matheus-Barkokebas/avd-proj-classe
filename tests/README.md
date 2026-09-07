# `tests/`

Testes automatizados. **Espelha a estrutura de [`src/`](../src/)**:
`tests/ingestao/`, `tests/processamento/`, `tests/indicadores/`, `tests/predicao/`, `tests/serving/`.

## Regras

- Todo teste roda **sem rede**: respostas de API e amostras de dados ficam em `tests/fixtures/`
  (mocks / fixtures por fonte).
- Nome dos arquivos: `test_<modulo>.py` (ex.: `tests/ingestao/test_recife_ckan.py`).
- Executar da raiz do projeto:

```bash
pytest
```

- Cobertura mínima esperada por história: os casos listados em **Critérios de aceitação**
  da issue correspondente em [`docs/HISTORIAS.md`](../docs/HISTORIAS.md).
