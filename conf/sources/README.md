# `conf/sources/`

Um arquivo YAML por **fonte de dados**. Descreve como coletá-la — sem lógica.

Arquivos previstos (issues `ING-*`): `epidemiologia.yml`, `ocorrencias.yml`, `territorio.yml`,
`ana_estacoes.yml`.

## Fontes configuradas

### `epidemiologia.yml` (ING-02)

Notificações de arboviroses (dengue, zika, chikungunya) do portal Dados Abertos Recife.

O conjunto no CKAN é composto por múltiplos recursos por ano (um para cada agravo). A configuração define um mapa de `recursos` para o ano de interesse e o mapeamento dos campos brutos da API para o contrato `conf/contracts/epidemiologia.yml`:

```yaml
nome: epidemiologia
descricao: Casos e notificações de arboviroses (Dengue, Zika, Chikungunya) - Dados Abertos Recife
api: recife_ckan
frequencia: diaria

recursos:
  dengue: "45a675e2-d387-4019-bb6e-4b915b74b1bf"
  zika: "cf7dc2c4-a050-454f-9404-465458baa988"
  chikungunya: "b300a634-1ab7-49fc-8592-4b45227822a8"

mapeamento_colunas:
  NU_NOTIFIC: protocolo
  DT_NOTIFIC: data_notificacao
  SEM_NOT: semana_epidemiologica
  NU_ANO: ano
  NM_BAIRRO: bairro
  CLASSI_FIN: classificacao_final
```

> **Nota operacional:** em janeiro de cada ano, quando a Prefeitura disponibilizar novos recursos
> para o ano vigente no CKAN, os identificadores em `recursos` devem ser atualizados manualmente
> neste arquivo (não há descoberta dinâmica de recursos).

