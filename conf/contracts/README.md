# `conf/contracts/`

Um arquivo YAML por fonte com o **schema esperado** dos dados. Usado pela ingestão para
validar cada lote na entrada e **falhar cedo** se a fonte mudar (issue FND-02).

Arquivos previstos: `epidemiologia.yml`, `ocorrencias.yml`, `ana_nivel.yml`, `ana_chuva.yml`, `territorio.yml`.

## Estrutura sugerida

```yaml
tabela: epidemiologia
chave_negocio: [protocolo]        # identifica 1 registro (para dedupe)
campo_data_referencia: data_notificacao
campos:
  - nome: data_notificacao
    tipo: datetime
    obrigatorio: true
  - nome: agravo
    tipo: string
    obrigatorio: true
    valores_permitidos: [dengue, zika, chikungunya]
  - nome: contagem
    tipo: int
    obrigatorio: true
```
