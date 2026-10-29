# `conf/contracts/`

Um arquivo YAML por fonte com o **schema esperado** dos dados. Usado pela ingestão para
validar cada lote na entrada e **falhar cedo** se a fonte mudar (issue FND-02).

## Contratos entregues

| Arquivo | Tabela lógica | Chave de negócio | Campo data ref. | Domínio / Fonte |
|---|---|---|---|---|
| `epidemiologia.yml` | `epidemiologia` | `[agravo, protocolo, data_notificacao]` | `data_notificacao` | Arboviroses (dengue, zika, chikungunya) - Dados Abertos Recife |
| `ocorrencias.yml` | `ocorrencias` | `[protocolo]` | `data_ocorrencia` | Chamados e ocorrências da Defesa Civil - SEDEC / Recife |
| `ana_nivel.yml` | `ana_nivel` | `[codigo_estacao, data_hora_medicao]` | `data_hora_medicao` | Cota e nível de rios / canais - API ANA / HidroWeb |
| `ana_chuva.yml` | `ana_chuva` | `[codigo_estacao, data_hora_medicao]` | `data_hora_medicao` | Pluviometria e chuva acumulada - API ANA / HidroWeb |
| `territorio.yml` | `territorio` | `[codigo_bairro]` | `data_atualizacao` | Cadastro de bairros, RPA e Distritos Sanitários - Recife |
| `cop_indicadores.yml` | `cop_indicadores` | `[data_hora]` | `data_hora` | Chuva média 1h/24h, maré, estágio - COP Recife |
| `cop_rios.yml` | `cop_rios` | `[codigo_estacao, data_hora]` | `data_hora` | Nível dos rios com cotas oficiais - COP Recife |
| `cop_previsao_chuva.yml` | `cop_previsao_chuva` | `[data_hora_prevista]` | `data_hora_prevista` | Previsão de chuva por modelo - COP Recife |
| `cop_chuva_mensal.yml` | `cop_chuva_mensal` | `[ano_referencia, mes]` | — | Chuva mensal vs. média histórica - COP Recife |
| `cop_pluviometros.yml` | `cop_pluviometros` | `[id_leitura]` | `data_hora` | Histórico por pulso dos pluviômetros municipais - COP Recife |
| `cop_areas_alagaveis.yml` | `cop_areas_alagaveis` | `[id_area]` | — | Polígonos de áreas alagáveis por distrito - COP Recife |
| `cop_pontos_alagamento.yml` | `cop_pontos_alagamento` | `[id_ponto]` | — | Pontos de alagamento com obra de drenagem (EMLURB) - COP Recife |

Na [decisão 0001](../../../docs/decisoes/0001-raw-mongodb-padronizada-neon.md), cada contrato também gera a tabela
correspondente no Neon: colunas tipadas, `NOT NULL` nos obrigatórios e `UNIQUE` na chave de negócio.

## Estrutura do Contrato

Cada contrato define:
- `tabela`: nome lógico da tabela de destino.
- `chave_negocio`: lista de campos que compõem a chave primária/natural para deduplicação.
- `campo_data_referencia`: campo temporal utilizado para particionamento e ordenação analítica.
- `campos`: lista de atributos contendo:
  - `nome`: identificador da coluna em snake_case padronizado.
  - `tipo`: tipo esperado (`string`, `int`, `float`, `bool`, `datetime`, `date`).
  - `obrigatorio`: booleano (`true` para colunas que devem estar presentes e sem nulos; `false` para atributos opcionais/anuláveis).
  - `descricao`: finalidade semântica da coluna.
  - `valores_permitidos`: lista opcional com o domínio categórico válido (validação restrita).

## Uso pela Ingestão

Os contratos são carregados e validados pelo módulo `src/ingestao/contratos.py`:

```python
from src.ingestao.contratos import carregar_contrato, validar

contrato = carregar_contrato("epidemiologia")
violacoes = validar(lote, contrato)
if violacoes:
    for v in violacoes:
        print(f"[{v.tipo}] Campo '{v.campo}': {v.mensagem}")
```

