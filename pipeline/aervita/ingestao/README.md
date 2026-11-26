# `aervita/ingestao/` — coleta e validação

Coleta as fontes públicas, grava a resposta original (RAW) sem transformação e carrega as linhas
validadas pelo contrato na camada padronizada. Ver [`ARQUITETURA`](../../../docs/ARQUITETURA.md).

| Pasta | Conteúdo |
|---|---|
| `nucleo/` | peças comuns a todas as fontes |
| `clientes/` | clientes HTTP genéricos, sem regra de fonte |
| `fontes/` | uma fonte por módulo, cada uma com a sua configuração em `conf/sources/` |

| Módulo | Papel |
|---|---|
| `nucleo/runner.py` | registro de coletores (`Coletor`), grava a RAW particionada por data e registra cada execução |
| `nucleo/armazenamento.py` | onde fica a RAW: arquivo local ou MongoDB Atlas (GridFS), com a mesma interface |
| `nucleo/contratos.py` | carrega o contrato de `conf/contracts/` e valida o lote |
| `nucleo/bronze.py` | grava as linhas válidas e manda as rejeitadas para a quarentena, com o motivo |
| `nucleo/padronizada.py` | tabelas no Neon geradas pelos contratos; carga idempotente pela chave de negócio |
| `nucleo/comum.py` | conversão de datas, números e texto usada por todas as fontes |
| `nucleo/geometria.py` | simplificação das malhas de bairro e distrito para o mapa |
| `clientes/recife_ckan.py` | Dados Abertos Recife: paginação, novas tentativas com espera e `resource_show` |
| `clientes/arcgis.py` | consultas paginadas ao ArcGIS (COP Recife) |
| `fontes/territorio.py` | bairros, RPAs e distritos sanitários, mais as malhas em GeoJSON |
| `fontes/epidemiologia.py` | dengue, zika e chikungunya do ano corrente |
| `fontes/epidemiologia_historico.py` | arboviroses de 2013 a 2024 (carga única) |
| `fontes/cop_recife.py` | camadas do COP; a conversão de cada campo está declarada em `cop_recife.yml` |
| `fontes/inmet.py` | chuva horária da estação A301 a partir dos arquivos anuais do INMET |

## Fluxo de uma fonte

```text
coletar_dados ──► runner.executar (RAW) ──► transformar ──► contratos.validar ──► bronze.gravar_validado
                                                                                     ├─ válidas ──► Silver (Neon) ou Parquet
                                                                                     └─ rejeitadas ──► quarentena, com o motivo
```

## Onde grava

| Opção | Valores | O que muda |
|---|---|---|
| `--armazenamento` (ou `AERVITA_ARMAZENAMENTO`) | `arquivo` · `mongo` | onde a RAW é gravada e relida |
| `--padronizada` (ou `AERVITA_PADRONIZADA`) | `arquivo` · `neon` | onde vão as linhas validadas e a quarentena |

O padrão é arquivo local em `data/`, que é o que os testes usam, sem rede. Em produção:
`python -m aervita arboviroses --armazenamento mongo --padronizada neon`.

## Quarentena

| Situação | Resultado |
|---|---|
| Linha com violação (ex.: bairro vazio em campo obrigatório) | vai para a quarentena com o motivo; o resto segue |
| Coluna obrigatória ausente em todas as linhas | aborta: a fonte mudou, nada é gravado |
| Todas as linhas rejeitadas | aborta: provável mudança de formato |

Tipos de violação: `coluna_faltante`, `nulo_obrigatorio`, `tipo_errado` e `valor_invalido`.

## Regras

- Ingestão não faz limpeza semântica: isso é da camada Gold (`aervita/processamento/`).
- Recoletar a mesma data não duplica nada: a RAW guarda o `sha256` e a carga usa a chave de negócio.
- Fonte que só devolve o estado atual (sem histórico por data) só relê uma RAW já gravada quando recebe `--data`.
