# `conf/sources/`

Um arquivo YAML por **fonte de dados**. Descreve como coletá-la — sem lógica.

Arquivos previstos (issues `ING-*`): `epidemiologia.yml`, `ocorrencias.yml`, `territorio.yml`,
`ana_estacoes.yml`.

## Campos sugeridos

```yaml
nome: epidemiologia
descricao: Notificacoes de arboviroses - Dados Abertos Recife
api: recife_ckan            # conector em src/ingestao/
resource_id: "<uuid-do-recurso>"
frequencia: diaria          # ver conf/schedule.yml (FND-03)
colunas:                    # origem -> nome padronizado (snake_case)
  "Data Notificacao": data_notificacao
  "Bairro": bairro
segredo_env: null           # nome da variavel de ambiente, se a fonte exigir auth
```
