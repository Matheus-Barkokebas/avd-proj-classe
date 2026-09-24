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

Fontes que só devolvem o **estado atual** (epidemiologia, ocorrências, território —
`suporta_historico=False` no `Coletor`) não coletam para outra data: com `--data` de
um dia que não é hoje e sem RAW gravada, a execução termina em `erro` com mensagem
clara, em vez de gravar o retrato de hoje com a data errada (BUG-09). A releitura
de uma RAW existente continua funcionando. A ANA consulta por data e segue coletando.

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

## Coleta de Epidemiologia — Arboviroses (ING-02)

O módulo `src/ingestao/epidemiologia.py` implementa a coleta das notificações de arboviroses
(dengue, zika e chikungunya) do portal Dados Abertos Recife via API CKAN.

### Funcionamento

1. **Coleta RAW (via `runner.py` ou CLI):**
   - Para cada agravo configurado em `conf/sources/epidemiologia.yml`, consulta a API via `recife_ckan.coletar_todos`.
   - Gera um payload JSON combinado contendo os blocos `dengue`, `zika` e `chikungunya`.
   - Grava a resposta intacta de forma atômica em `data/raw/epidemiologia/AAAA/MM/DD/datastore_search.json`.
   - Registra a execução em `data/_runs/<id>.json`.

2. **Materialização Bronze (`materializar_bronze`):**
   - Lê o arquivo RAW particionado da data.
   - Aplica o mapeamento de campos (`NU_NOTIFIC` -> `protocolo`, etc.) e conversão de tipos.
   - Atribui o `agravo` correspondente a cada bloco e `contagem = 1` por linha.
   - Valida o lote contra `conf/contracts/epidemiologia.yml`; linhas inválidas vão para a quarentena (ver "Quarentena de linhas rejeitadas" abaixo) e o restante segue para a Bronze.
   - Chave de negócio: `[agravo, protocolo, data_notificacao]` — o número de notificação sozinho se repete (BUG-07).
   - ⚠️ ~600 das 11.950 notificações de 2025 têm município de notificação (`ID_MUNICIP`) fora do Recife; o bairro delas pode não ser do Recife. A filtragem por município é pendência da INT-02/INT-03.
   - Grava a tabela Parquet via PyArrow de forma atômica em `data/bronze/epidemiologia/AAAA/MM/DD/epidemiologia.parquet`.
   - **Idempotência:** reexecuções para a mesma data substituem a partição sem duplicar registros.

### Como rodar

**Fluxo completo (RAW + Bronze):**
```bash
python src/ingestao/epidemiologia.py
python src/ingestao/epidemiologia.py --data 2026-09-22
```

**Apenas coleta RAW (via orquestrador genérico do runner):**
```bash
python src/ingestao/runner.py epidemiologia
python src/ingestao/runner.py epidemiologia --data 2026-09-22
```

## Coleta de Ocorrências — Defesa Civil (ING-03)

O módulo `src/ingestao/ocorrencias.py` implementa a coleta de chamados e ocorrências da
Defesa Civil do Recife (SEDEC), via o recurso CKAN "Sedec Solicitações Tempo Real"
(`conf/sources/ocorrencias.yml`). Segue a mesma estrutura da ING-02 (coleta RAW ↔
materialização Bronze separadas, ambas reaproveitando `runner.executar` e
`runner.gravar_atomico`).

### Particularidades desta fonte (confirmadas contra a API real)

> ⚠️ **Fonte congelada (BUG-11):** apesar do nome, o recurso "Sedec Solicitações Tempo
> Real" tem 173 registros, todos de **29/03/2023**, e não há hoje fonte pública atualizada
> de ocorrências da Defesa Civil no portal. Com `max_defasagem_dias: 7`
> (`conf/sources/ocorrencias.yml`), a coleta **termina em erro** quando o registro mais
> recente é mais velho que o limite, em vez de gravar o retrato de 2023 como se fosse de
> hoje. A escolha de outra fonte (ex.: base histórica "Atendimentos 2024", ~80 mil
> registros, esquema diferente) está pendente de decisão do time.

- **Fonte "tempo real":** a API sempre reflete o dia da consulta — não há histórico
  navegável por data. `--data <passado>` só relê a RAW já gravada; se a partição
  não existir, a execução termina em erro (não grava o retrato de hoje com data antiga).
- **Sem latitude/longitude:** a fonte só tem localização textual (bairro, endereço,
  RPA). Todo registro grava coordenadas nulas — aceitável (campos opcionais no
  contrato) e o registro **não é descartado** por isso.
- **Tradução de status:** `processo_situacao` (bruto) é traduzido para o domínio
  fechado do contrato via `mapa_status` em `conf/sources/ocorrencias.yml`. Só o
  valor `execucao` foi observado em amostra real; valor sem entrada no mapa passa
  intacto e falha a validação do contrato de propósito (fail cedo).
- **Data + hora combinadas:** `data_ocorrencia` é montada a partir de
  `solicitacao_data` + `solicitacao_hora` (campos separados na fonte).

### Como rodar

**Fluxo completo (RAW + Bronze):**
```bash
python src/ingestao/ocorrencias.py
python src/ingestao/ocorrencias.py --data 2026-09-24
```

**Apenas coleta RAW (via orquestrador genérico do runner):**
```bash
python src/ingestao/runner.py ocorrencias
python src/ingestao/runner.py ocorrencias --data 2026-09-24
```

## Coleta ANA HidroWebService — Chuva e Nível/Vazão (ING-04)

O módulo `src/ingestao/ana_hidroweb.py` implementa a coleta de chuva e nível/vazão das
estações da ANA configuradas em `conf/sources/ana_estacoes.yml`. Duas fontes separadas
(`ana_chuva`, `ana_nivel`), cada uma com sua própria RAW, contrato e Bronze — mas
compartilhando o mesmo cliente/autenticação.

### Funcionamento

1. **Autenticação:** `autenticar()` faz login OAuth (Identificador/Senha por variável de
   ambiente) e devolve um token Bearer. Sem as variáveis definidas, falha com erro claro
   — nunca segue sem autenticar.
2. **Coleta RAW (via `runner.py` ou CLI):** para cada estação em `ana_estacoes.yml`,
   consulta a série (chuva ou cotas) daquela estação. **Falha em uma estação não impede
   as demais** — o erro fica registrado no bloco daquela estação dentro do próprio
   payload (`{"<codigo>": {"erro": "..."}}`), e a coleta segue para as outras.
   Grava o payload combinado (todas as estações) atomicamente em
   `data/raw/ana_chuva/AAAA/MM/DD/hidroweb.json` (ou `ana_nivel/...`).
3. **Materialização Bronze (`materializar_bronze`):** lê a RAW, ignora blocos de estação
   com erro, mapeia colunas e tipa valores, valida contra o contrato
   (`conf/contracts/ana_chuva.yml` / `ana_nivel.yml`) e grava Parquet atomicamente em
   `data/bronze/ana_chuva/AAAA/MM/DD/ana_chuva.parquet` (ou `ana_nivel/...`).

### ⚠️ Limitação conhecida desta entrega

A API `hidrowebservice` da ANA **não ficou acessível para verificação ao vivo** durante
o desenvolvimento desta issue (respostas 503/504) — diferente do CKAN do Recife
(ING-02/03), que pôde ser consultado e verificado de ponta a ponta. A implementação
segue a documentação pública do serviço (endpoints, envelope de token, nomes de campo),
mas **isso ainda precisa ser confirmado contra uma resposta real** assim que o time
tiver credenciais. Os nomes de campo ficam em `mapeamento_colunas_chuva` /
`mapeamento_colunas_nivel` em `conf/sources/ana_estacoes.yml` — ajustar lá, sem tocar
no código, se algo não bater.

Os códigos de estação e as cotas de atenção/alerta em `ana_estacoes.yml` são
**placeholder** — não foram inventados (ai-rules 5.3); o time preenche com o inventário
real da ANA e as cotas oficiais da Defesa Civil.

### Como rodar

```bash
export ANA_HIDROWEB_IDENTIFICADOR=...   # cadastro em ana.gov.br/hidrowebservice
export ANA_HIDROWEB_SENHA=...

python src/ingestao/ana_hidroweb.py                       # chuva + nível, RAW + Bronze
python src/ingestao/ana_hidroweb.py --serie chuva
python src/ingestao/ana_hidroweb.py --serie nivel --data 2026-09-24

# Apenas coleta RAW (via orquestrador genérico do runner):
python src/ingestao/runner.py ana_chuva
python src/ingestao/runner.py ana_nivel --data 2026-09-24
```

## Coleta de Território — Bases Cadastrais (ING-05)

O módulo `src/ingestao/territorio.py` coleta as bases cadastrais territoriais do Recife
configuradas em `conf/sources/territorio.yml`: duas tabulares (bairros+RPA, distritos
sanitários, via `recife_ckan`) e duas geométricas (bairros e RPA em GeoJSON, via
download direto — **sem** passar pelo `datastore_search`, que só serve dado tabular).

### Funcionamento

1. **Coleta RAW:** para cada base tabular, usa `recife_ckan.coletar_todos`; para cada
   base geométrica, baixa o arquivo e embute em base64 dentro do payload combinado.
   Tudo isso é a fonte única `territorio` (uma RAW por execução, particionada por data
   de coleta — `data/raw/territorio/AAAA/MM/DD/territorio.json`), igual definido em
   `conf/schedule.yml`.
2. **Materialização Bronze (`materializar_bronze`):** gera **uma saída por base** —
   nenhuma é cruzada com outra:
   - bases tabulares → Parquet (`data/bronze/territorio_<base>/AAAA/MM/DD/`);
   - bases geométricas → arquivo preservado no formato de origem, ex. GeoJSON
     (mesmo caminho, sem conversão — "geometrias preservadas e legíveis").
   - **Idempotência:** substituição atômica de cada partição.

### Diferença importante em relação à ING-02/03/04

Este módulo **não chama `contratos.validar()`**. O contrato
`conf/contracts/territorio.yml` descreve a tabela já *resolvida* (bairro + RPA +
Distrito Sanitário numa linha só) — isso só existe depois do cruzamento que a **INT-02**
faz a partir destas tabelas Bronze. Validar aqui contra esse contrato falharia sempre
(nenhuma base publica RPA e Distrito Sanitário juntos) e contradiria o "Fora de escopo"
da própria ING-05 ("montar a tabela de correspondência bairro↔RPA↔DS é INT-02").

### Bases coletadas (verificadas ao vivo, 2026-09)

| Base | Tipo | Fonte |
|---|---|---|
| `bairros_rpa` | tabular | "Bairros e RPAs do Recife" (CSV, CKAN) |
| `distritos_sanitarios` | tabular | "Distritos Sanitários - descrição dos bairros" (CSV, CKAN) |
| `bairros_geo` | geométrica | "Bairros do Recife" (GeoJSON) |
| `rpa_geo` | geométrica | "Região Política Administrativa do Recife" (GeoJSON) |

**Pendências não inventadas:** não encontramos um dataset cadastral de **áreas de
risco** (só dados operacionais de atendimento, já cobertos pela ING-03) nem
**população por bairro** — documentado em `conf/sources/territorio.yml` como próximo
passo, sem bloquear esta entrega (população é campo opcional no contrato).

### Como rodar

```bash
python src/ingestao/territorio.py
python src/ingestao/territorio.py --data 2026-09-24

# Apenas coleta RAW (via orquestrador genérico do runner):
python src/ingestao/runner.py territorio
```


## Quarentena de linhas rejeitadas (BUG-06)

As fontes validadas por contrato (epidemiologia, ocorrências, ANA) gravam a Bronze por
`src/ingestao/bronze.py::gravar_validado`:

| Situação | Resultado |
|---|---|
| Linha com violação (ex.: bairro vazio em campo obrigatório) | vai para a quarentena com o motivo; o resto do dia segue para a Bronze |
| Violação de lote (coluna obrigatória ausente em todas as linhas) | aborta — a fonte mudou; nada é gravado |
| Todas as linhas rejeitadas | aborta — provável mudança de formato, não dado ruim pontual |

Quarentena: `data/bronze/<fonte>_rejeitados/AAAA/MM/DD/<fonte>_rejeitados.json`, uma entrada
por linha rejeitada (`linha`, `motivos`, `registro`). É JSON, não Parquet, porque as linhas
rejeitadas podem ter tipos mistos na mesma coluna. O total aparece em `rejeitados` no
resultado da CLI. Reexecução sem rejeições remove a quarentena antiga da partição.
