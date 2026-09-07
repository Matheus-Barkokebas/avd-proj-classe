# `src/ingestao/`

Coleta os dados nas APIs / fontes públicas e grava **sem transformação** na camada RAW,
depois materializa a camada Bronze (tipada). Ver [`ARQUITETURA §3`](../../docs/ARQUITETURA.md#3-camada-de-ingestão-coleta).

## O que vive aqui

- **Conectores** reutilizáveis por API — ex.: `recife_ckan.py` (issue ING-01), `ana_hidroweb.py` (ING-04).
- **Coletores por fonte** — um módulo por conjunto de dados: `epidemiologia.py`, `ocorrencias.py`, `territorio.py`…
- **`runner.py`** (issue FND-03) — orquestra um coletor, grava RAW particionada por data de coleta e registra a execução.
- **`contratos.py`** (issue FND-02) — valida um lote contra o contrato da fonte em [`conf/contracts/`](../../conf/contracts/).

## Regras

- Não fazer transformação semântica aqui (limpeza/normalização é `processamento/`).
- Idempotência: recoletar a mesma janela não duplica linhas na Bronze.
- RAW guarda o payload original; Bronze é Parquet com 1 linha por registro.
- Segredos (tokens de API) só via variável de ambiente — nunca no código nem em `conf/`.
- Configuração de cada fonte em [`conf/sources/`](../../conf/sources/).

## Saída

```
data/raw/<fonte>/AAAA/MM/DD/…      # original
data/bronze/<fonte>/               # Parquet tipado
```
