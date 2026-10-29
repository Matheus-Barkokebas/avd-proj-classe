# `tests/fixtures/`

## `amostras/` — amostras reais reduzidas (QA-01)

Poucos registros reais de cada fonte CKAN, com o **formato original de cada campo
preservado** (datas, texto vs. número). Existem porque os fixtures escritos à mão
seguiam as suposições do código e não pegaram diferenças reais entre recursos
(ex.: zika/chikungunya mandam data DD/MM/AAAA; dengue manda ISO — BUG-03).

Privacidade: só os campos que o pipeline usa são mantidos (sem data de nascimento,
logradouro, CEP etc.) e os números de notificação/processo são sintéticos (mesmo tipo
do original). Incluem de propósito casos-limite reais: bairro vazio e número de
notificação repetido entre agravos.

Regenerar (acessa a rede):

```bash
python tests/fixtures/atualizar_amostras.py
```

Usadas por `tests/ingestao/test_amostras_reais.py`.
