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

### `ocorrencias.yml` (ING-03)

Chamados e ocorrências da Defesa Civil do Recife (SEDEC), via o recurso CKAN
"Sedec Solicitações Tempo Real":

```yaml
nome: ocorrencias
descricao: Chamados e ocorrências da Defesa Civil do Recife (SEDEC) - feed em tempo real
api: recife_ckan
frequencia: diaria

resource_id: "fa135ecc-101d-40d7-88df-f38aa709a7d1"

mapeamento_colunas:
  processo_numero: protocolo
  solicitacao_bairro: bairro
  processo_solicitacao: tipo_ocorrencia
  processo_situacao: status
  solicitacao_descricao: descricao

mapa_status:
  execucao: em_atendimento
```

> **Nota operacional — fonte "tempo real":** este recurso reflete sempre o dia da
> consulta, sem histórico navegável por data. `--data <passado>` só relê a RAW já
> gravada; se a partição não existir, uma nova coleta traria os dados do dia da
> consulta, não os dados reais daquela data.
>
> **Sem coordenadas:** a fonte não tem campos de latitude/longitude — só
> localização textual (bairro, endereço, RPA). Todo registro grava
> `latitude`/`longitude` nulos; é aceitável porque são opcionais no contrato, e
> o registro **não é descartado** por isso (critério de aceitação da ING-03).
>
> **`mapa_status`:** traduz o valor bruto de `processo_situacao` para o domínio
> fechado do contrato (`aberta`/`em_atendimento`/`concluida`/`cancelada`). Só
> `execucao` foi observado em amostra real até agora — valor sem entrada no
> mapa passa intacto e **falha a validação do contrato de propósito** (fail
> cedo). Estender o mapa quando outros valores aparecerem em produção.

### `ana_estacoes.yml` (ING-04)

Estações telemétricas da ANA (HidroWebService) — séries de chuva e nível/vazão:

```yaml
nome: ana_hidroweb
api: ana_hidroweb
frequencia: horaria
base_url: "https://www.ana.gov.br/hidrowebservice"

autenticacao:
  identificador_env: ANA_HIDROWEB_IDENTIFICADOR
  senha_env: ANA_HIDROWEB_SENHA

estacoes:
  - codigo: "SUBSTITUIR-COM-CODIGO-REAL"
    nome: "SUBSTITUIR — ex. Recife / Rio Capibaribe"
    tipo: fluviometrica
    rio: "SUBSTITUIR"
    bacia: "SUBSTITUIR"
    cota_atencao_cm: null
    cota_alerta_cm: null

mapeamento_colunas_chuva: {...}
mapeamento_colunas_nivel: {...}
mapa_consistencia: {"1": bruto, "2": consistido}
```

> ⚠️ **Pendente de dados reais do time (ai-rules 5.3 — não inventamos):**
> - `estacoes` está com **placeholder**. Preencher com os códigos reais do
>   inventário da ANA (https://www.snirh.gov.br/hidroweb/) e as **cotas de
>   atenção/alerta oficiais** usadas pela Defesa Civil antes de rodar em
>   produção.
> - `identificador_env`/`senha_env` apontam para variáveis de ambiente —
>   cadastro em https://www.ana.gov.br/hidrowebservice/. Sem essas variáveis
>   definidas, a coleta falha com erro claro (não tenta seguir sem autenticar).
>
> ⚠️ **API não verificada ao vivo nesta issue:** as tentativas de consulta ao
> `hidrowebservice` retornaram `503`/`504` durante o desenvolvimento (ao
> contrário do CKAN do Recife, usado nas ING-02/03, que respondeu normalmente).
> Os caminhos de endpoint, o envelope do token OAuth e os nomes de campo em
> `mapeamento_colunas_chuva`/`mapeamento_colunas_nivel` seguem a documentação
> pública do serviço, **mas precisam ser confirmados** contra uma resposta
> real assim que o time tiver credenciais — ajustar só este YAML, sem tocar
> em `src/ingestao/ana_hidroweb.py`.

