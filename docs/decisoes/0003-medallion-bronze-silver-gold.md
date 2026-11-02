# 0003 · Medallion: Bronze no Atlas, Silver e Gold no Neon

- **Status:** Aceita pelo responsável do projeto em 2026-11-02; aguardando revisão do time (CODEOWNERS)
- **Data:** 2026-11-02
- **Substitui:** o item 3 ("sem Silver e Gold") da [decisão 0001](0001-raw-mongodb-padronizada-neon.md) e o modelo RAW → Bronze → Silver → Gold de [`ARQUITETURA.md`](../ARQUITETURA.md)

## Contexto

O projeto recebeu o pedido de aplicar o medallion na prática, com três camadas, e de treinar um modelo preditivo
alimentado pela última delas. A entrega precisa ser rápida e o painel publicado não pode quebrar durante a mudança.

## Decisão

| Camada | Onde | Conteúdo |
|---|---|---|
| **Bronze** | MongoDB Atlas | A RAW de sempre: resposta original de cada fonte, sem transformação |
| **Silver** | Neon, schema `public` | As tabelas atuais, sem mudança: tipos, chaves e `rejeitados`, validados pelos contratos |
| **Gold** | Neon, schema `gold` | Dados finais do painel e do modelo, mais as previsões |

- A Silver **não** muda de schema: mover as tabelas exigiria migrar pipeline e API ao mesmo tempo, sem ganho.
- A Gold é montada por [`pipeline/src/processamento/gold.py`](../../pipeline/src/processamento/gold.py):
  **views** sobre a Silver para o que só precisa de limpeza (sempre atuais) e **tabelas** para o que exige cálculo.
- A **API lê apenas a Gold**; há teste que falha se o repositório consultar outro schema.
- O usuário `aervita_api` recebe `SELECT` na Gold. O acesso dele à Silver pode ser removido depois que a API
  publicada migrar para a Gold.

### O que a Gold acrescenta

- `arbo_bairro_semana`: notificações por ano, semana, bairro e agravo, com bairro padronizado e classificação decodificada.
  O que não tem bairro reconhecido continua contado, com a grafia da fonte.
- `de_para_bairro`: cada grafia da fonte e a chave de `dim_bairro` correspondente.
- `classificacao`: significado dos códigos, vindo dos metadados do portal ([`conf/gold.yml`](../../pipeline/conf/gold.yml)).
- Views de chuva, rios, território e cargas, sem colunas de controle e sem o texto "Não Informado" do COP.

### Previsão de alagamento

O foco do sistema é chuva e risco de alagamento, e o modelo começa por aí. Só entram fontes públicas de governo:
chuva do INMET (estação A301), tábua de maré do COP e o campo `alaga` do COP como registro de alagamento. O campo parece vir de
alertas do Waze, a confirmar com o COP; ele foi aceito como alvo pelo responsável do projeto em 2026-11-02, com a origem declarada.

`gold.ml_alagamento_hora` tem uma linha por hora, e `gold.previsao_alagamento` guarda as previsões. O modelo segue o formato de
[`etl-vacinacao-recife`](https://github.com/MatmJr/etl-vacinacao-recife), e os resultados estão em [`RESULTADOS.md`](../../pipeline/src/predicao/resultados/RESULTADOS.md).

### Histórico de arboviroses

O portal publica de 2013 a 2025, e até aqui só usávamos 2025. O histórico entra numa tabela própria da Silver,
`epidemiologia_historico`, para não mudar o que a API publicada lê. Duas regras vêm da análise da fonte:

- **O agravo vem do CID de cada linha, não do título do recurso:** "Casos confirmados de Zika 2021" contém linhas de chikungunya (A92.0).
- **Códigos sem documentação não são interpretados:** os metadados só explicam a classificação da dengue.
  Códigos como o `2` da zika e o `13` da chikungunya não contam como confirmados nem como descartados até a Prefeitura confirmar.

O painel continua mostrando o ano mais recente; os anteriores servem ao histórico e ao modelo.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Mover a Silver para um schema `silver` | Mais trabalho e risco de quebrar o painel, sem ganho funcional agora |
| Gold só com views | Agregar cerca de 180 mil notificações a cada pedido deixaria a API lenta |
| Histórico na tabela `epidemiologia` | O painel publicado passaria a somar todos os anos antes de a API migrar |

## Consequências

- Depois de carregar arboviroses, a Gold precisa ser recalculada; as cargas já fazem isso ao terminar.
- Chuva e rios continuam dependendo da coleta do COP, que precisa rodar de uma máquina no Brasil ([deploy de teste](../deploy-teste.md)).
- A Bronze guarda o histórico comprimido com gzip para caber no plano gratuito do Atlas.

## Estado da implementação

| Item | Situação |
|---|---|
| Camada Gold no Neon | Feita |
| API lendo da Gold | Feita na branch; o painel publicado migra quando ela chegar à `main` |
| Histórico de arboviroses | Carregado: 128.233 notificações de 2013 a 2024 e 22.360 linhas em `rejeitados`, com o motivo. Sem uso no modelo por enquanto |
| Modelo de alagamento | Feito: 82,5% de acurácia no teste contra 69,7% do chute ([resultados](../../pipeline/src/predicao/resultados/RESULTADOS.md)) |
| Previsão em tempo real no painel | A fazer: depende da coleta do COP numa máquina no Brasil e de validar a chuva do COP contra a do INMET |
