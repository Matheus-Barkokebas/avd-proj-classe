# `tests/`

Testes automatizados. **Espelha a estrutura de [`src/`](../src/)**:
`tests/ingestao/`, `tests/processamento/`, `tests/indicadores/`, `tests/predicao/`, `tests/serving/`.

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
  da issue correspondente em [`docs/HISTORIAS.md`](../docs/HISTORIAS.md).
