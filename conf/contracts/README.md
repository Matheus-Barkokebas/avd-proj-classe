# `conf/contracts/`

Um arquivo YAML por fonte com o **schema esperado** dos dados. Usado pela ingestão para
validar cada lote na entrada e **falhar cedo** se a fonte mudar (issue FND-02).

## Contratos entregues

| Arquivo | Tabela lógica | Chave de negócio | Campo data ref. | Domínio / Fonte |
|---|---|---|---|---|
| `epidemiologia.yml` | `epidemiologia` | `[protocolo]` | `data_notificacao` | Arboviroses (dengue, zika, chikungunya) - Dados Abertos Recife |
| `ocorrencias.yml` | `ocorrencias` | `[protocolo]` | `data_ocorrencia` | Chamados e ocorrências da Defesa Civil - SEDEC / Recife |
| `ana_nivel.yml` | `ana_nivel` | `[codigo_estacao, data_hora_medicao]` | `data_hora_medicao` | Cota e nível de rios / canais - API ANA / HidroWeb |
| `ana_chuva.yml` | `ana_chuva` | `[codigo_estacao, data_hora_medicao]` | `data_hora_medicao` | Pluviometria e chuva acumulada - API ANA / HidroWeb |
| `territorio.yml` | `territorio` | `[codigo_bairro]` | `data_atualizacao` | Cadastro de bairros, RPA e Distritos Sanitários - Recife |

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

