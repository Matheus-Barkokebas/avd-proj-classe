# `tests/`

Testes automatizados. **Espelha a estrutura de [`src/`](../src/)**:
`tests/ingestao/` e `tests/serving/`, mais `tests/integracao/` (rede, opcional). As pastas das próximas
fases entram junto com o código que testam.

## Regras

- Todo teste roda **sem rede**: respostas de API e amostras de dados ficam em `tests/fixtures/`
  (mocks / fixtures por fonte).
- Nome dos arquivos: `test_<modulo>.py` (ex.: `tests/ingestao/test_recife_ckan.py`).
- Executar da raiz do projeto:

```bash
python -m pip install -r requirements-dev.txt
pytest
```

`pytest.ini` configura os imports a partir da raiz e mantém dados temporários em
`tests/.pytest_cache`, dentro do repositório e ignorados pelo Git. Essa pasta é
exclusiva dos testes e recriada pelo pytest a cada execução. Nenhum teste da
FND-03 escreve em `data/` ou acessa a rede.

`ingestao/test_runner.py` cobre sucesso, exceção de coleta, RAW intacta JSON/CSV,
releitura/recoleta por data, falha de publicação atômica, entradas inválidas,
contagem vazia, códigos de saída da CLI e as frequências de `conf/schedule.yml`.
PyYAML é usado apenas nos testes para validar a configuração YAML; o runner usa
somente a biblioteca padrão. Não há notebooks envolvidos nesta entrega.

- Cobertura mínima esperada por história: os casos listados em **Critérios de aceitação**
  da issue correspondente em [`docs/HISTORIAS.md`](../../docs/HISTORIAS.md).

## Amostras reais, integração e CI (QA-01)

- `tests/ingestao/test_amostras_reais.py` — roda o pipeline sobre **amostras reais
  reduzidas** das APIs (`tests/fixtures/amostras/`), com os YAMLs reais de `conf/sources/`.
- `tests/integracao/` — testes contra as **APIs reais** (rede). Ficam fora do `pytest`
  padrão e do CI; rodar explicitamente com `pytest -m integracao`. Falha pontual pode ser
  instabilidade da API pública — reexecutar antes de investigar.
  Inclui `test_cop_real.py` (ArcGIS do COP Recife: confere que as camadas ainda passam no contrato),
  `test_mongo_real.py` e `test_neon_real.py` (Atlas e Neon, em banco/schema descartável `aervita_teste`;
  pulam sozinhos sem `MONGODB_URI` / `NEON_DATABASE_URL`).
- CI: `.github/workflows/testes.yml` roda `pytest` (sem rede) a cada push/PR em
  `develop` e `main`.
