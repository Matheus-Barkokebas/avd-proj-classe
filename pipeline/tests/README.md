# `tests/`

Espelha [`aervita/`](../aervita/): `ingestao/{nucleo,clientes,fontes}`, `processamento/`, `predicao/`,
mais `test_cli.py` (ponto de entrada) e `integracao/` (serviços reais, opcional).

- Todo teste do `pytest` padrão roda **sem rede**; respostas de API são simuladas e as amostras ficam
  em `fixtures/`.
- `ingestao/test_amostras_reais.py` roda o pipeline sobre amostras reais reduzidas das APIs, com os
  YAMLs reais de `conf/sources/`.
- `predicao/test_ml_model.py` inclui o teste de ausência de vazamento de dados do modelo.
- `integracao/` acessa as APIs, o Atlas e o Neon reais (schema/banco descartável `aervita_teste`) e
  pula sozinho sem as variáveis de ambiente. Rodar com `pytest -m integracao`.

```bash
pip install -r requirements-dev.txt -r requirements-modelo.txt
pytest
```

O CI (`.github/workflows/testes.yml`) roda `ruff check .` e `pytest` a cada push e PR em `develop` e `main`.
