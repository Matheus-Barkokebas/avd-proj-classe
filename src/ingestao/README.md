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

## Runner (FND-03)

Python 3.12+, sem dependências de execução externas. Da raiz:

```bash
python src/ingestao/runner.py dummy
python src/ingestao/runner.py dummy --data 2026-09-01
```

`dummy` é exclusivamente sintético para teste; nenhuma fonte real está conectada.
Para demonstrações isoladas, acrescente `--diretorio-dados .pytest_cache/demo`.
O caminho padrão é `data/` do repositório, independentemente da pasta de execução.

Cada chamada grava um JSON independente em `data/_runs/<id>.json`, contendo
`fonte`, `inicio`, `fim`, `numero_registros`, `status` (`ok`/`erro`), `mensagem`,
`id` e `data_coleta`. Horários seguem America/Recife, sem frações de segundo.
O processo retorna 0 em sucesso, 1 em falha e 2 para argumentos inválidos.
Se o próprio registro não puder ser persistido, a CLI informa a falha e retorna 1.

Sem `--data`, coleta novamente na partição do dia local. Com `--data AAAA-MM-DD`,
relê o arquivo RAW daquela partição quando existe; caso contrário, chama o coletor
com a data solicitada. A releitura reconta os registros, sem rede nem transformação.
Cada tentativa mantém seu próprio registro; a RAW não é duplicada.

Para integrar uma fonte futura, registre em `COLETORES` um `Coletor` com
`coletar(data_coleta) -> bytes`, `contar_registros(conteudo) -> int` e
`nome_arquivo` JSON/CSV. A contagem interpreta o payload, mas não o modifica.
Nos testes, o mapa pode ser injetado pelo argumento `coletores` de `executar`.
O coletor deve concluir a resposta antes de devolvê-la, sem gravar arquivos.
O runner publica os bytes originais por substituição atômica no mesmo diretório;
falhas de coleta/contagem/escrita não publicam RAW parcial e preservam a anterior.

O registro e a RAW são arquivos independentes, sem transação conjunta: falha do
armazenamento de `_runs` pode ocorrer após a publicação da RAW. Execuções simultâneas
da mesma fonte/data devem ser serializadas pelo futuro agendador (última gravação vence).

As frequências estão em [`conf/schedule.yml`](../../conf/schedule.yml).
A escolha e integração do agendador de produção ficam para uma próxima etapa;
o runner executa uma fonte por chamada. Bronze e conectores reais permanecem nas
issues `ING-*`, conforme o campo “Para IA” da FND-03.

## Contratos de Dados (FND-02)

O módulo `contratos.py` fornece validação declarativa de lotes de dados (`list[dict]`)
contra os schemas definidos em [`conf/contracts/`](../../conf/contracts/).
Permite falhar cedo na ingestão quando a fonte alterar esquema ou enviar tipos/valores incompatíveis.

### Dependências em runtime

Requer `PyYAML>=6,<7` em ambiente de execução (especificado em `requirements.txt`).

### Como usar

```python
from src.ingestao.contratos import carregar_contrato, validar

# Carrega o contrato pelo nome da fonte (conf/contracts/<fonte>.yml) ou caminho
contrato = carregar_contrato("epidemiologia")

# Lote recebido da coleta (1 dict por linha)
lote = [
    {
        "protocolo": "NOT-2026-001",
        "data_notificacao": "2026-09-01 10:00:00",
        "semana_epidemiologica": 202635,
        "ano": 2026,
        "bairro": "Boa Vista",
        "agravo": "dengue",
        "classificacao_final": "confirmado",
        "contagem": 1,
    }
]

# Valida o lote (retorna lista vazia se válido)
violacoes = validar(lote, contrato)
if violacoes:
    for v in violacoes:
        print(f"[{v.tipo}] Campo '{v.campo}' (linha {v.linha}): {v.mensagem}")
```

### Tipos de Violação

- `coluna_faltante`: coluna obrigatória ausente em todas as linhas do lote (`linha` é `None`).
- `nulo_obrigatorio`: campo com `obrigatorio: true` recebendo `None` ou `NaN` em uma linha específica.
- `tipo_errado`: valor com tipo incompatível com o declarado (`string`, `int`, `float`, `bool`, `datetime`, `date`).
- `valor_invalido`: valor fora do domínio categórico estipulado em `valores_permitidos`.

> **Nota de escopo:** `validar()` deve ser chamado após a padronização de nomes de colunas
> (mapeamento de `conf/sources/*.yml`), garantindo que o lote use os identificadores canônicos do contrato.
