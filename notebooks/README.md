# `notebooks/`

Exploração de dados — etapa *Data Understanding* do [CRISP-DM](../docs/CRISP-DM.md).
Análises exploratórias, verificação de qualidade das fontes, protótipos de gráfico e de modelo.

## Regras

- Notebook é **rascunho**, não pipeline. Código que vira produção migra para [`src/`](../src/) com teste.
- Nome no formato `NN-descricao-curta.ipynb` (ex.: `01-exploracao-epidemiologia.ipynb`).
- Não commitar saída pesada nem dados: `jupyter nbconvert --clear-output` antes do commit
  (o `.gitignore` já ignora `.ipynb_checkpoints/`).
- Ler dados sempre de [`data/`](../data/); nunca versionar dados aqui.
