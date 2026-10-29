# 0001 · RAW em MongoDB Atlas e camada padronizada no Neon (sem medalhão na primeira release)

- **Status:** Proposta, aguardando revisão do time (CODEOWNERS)
- **Data:** 2026-10-28
- **Escopo:** primeira release do AerVita
- **Substitui parcialmente:** o modelo de camadas RAW → Bronze → Silver → Gold de [`ARQUITETURA.md`](../ARQUITETURA.md) (§3 a §7), apenas para esta release

## Contexto

A arquitetura de referência ([`ARQUITETURA.md`](../ARQUITETURA.md)) organiza o dado em quatro camadas no lago de dados: RAW, Bronze (Parquet tipado), Silver (limpo e integrado) e Gold (indicadores). Esse desenho foi pensado para o caminho completo do projeto.

A primeira release precisa ser entregue rapidamente. Para isso:

- a camada Bronze em Parquet exige armazenamento de arquivos e uma biblioteca (`pyarrow`) que não são necessários para o painel;
- Silver e Gold só entram nas histórias INT-03 e INT-04, que não são pré-requisito para a primeira demonstração.

A equipe também precisa de um banco de consulta simples para o painel e para o boletim, e de uma forma de guardar a resposta original da API sem transformação.

## Decisão

1. **RAW** em **MongoDB Atlas**: um documento por coleta, com o payload original da API, a fonte, a data de coleta e um hash do conteúdo. Nada é transformado nessa etapa.
2. **Camada padronizada** em **Neon (PostgreSQL)**: tabelas tipadas, validadas pelos contratos de [`conf/contracts/`](../../pipeline/conf/contracts/). Linhas rejeitadas vão para a tabela `rejeitados`, com o motivo registrado.
3. **Sem Silver e Gold nesta release.** O painel e o boletim leem a camada padronizada.
4. **Biblioteca de acesso:** `pymongo` para o RAW e `psycopg` (versão 3) para o Neon. O `pyarrow` sai das dependências de execução.

### Modelo da camada padronizada

- **Uma tabela por contrato**, com o nome do contrato: `epidemiologia`, `ocorrencias`, `ana_chuva`, `ana_nivel`.
  As colunas vêm dos campos do contrato; `obrigatorio: true` vira `NOT NULL` e `chave_negocio` vira `UNIQUE`
  (em `epidemiologia`: `agravo, protocolo, data_notificacao`, conforme BUG-07). Colunas de controle: `data_coleta`, `carregado_em`.
- `dim_distrito` e `dim_bairro`: montadas das bases territoriais, cruzando "Bairros e RPAs" com "Distritos
  Sanitários" pelo nome normalizado. `dim_bairro` referencia o distrito por chave estrangeira.
- `rejeitados`: fonte, data de coleta, linha de origem, motivos e o registro original.

A carga usa `INSERT ... ON CONFLICT` na chave de negócio, então rodar duas vezes não duplica dado.

## Alternativas consideradas

| Alternativa | Por que não | 
|---|---|
| Manter Parquet e o medalhão atual | Mais lento para a primeira entrega, e não há consumidor que precise de Parquet nesta release |
| Postgres para RAW e padronizada | O RAW é o dado da API, de estrutura variável; o documento é o formato natural para isso |
| MongoDB para RAW e padronizada | Perde restrições de chave e tipo no banco, e as junções entre bairro, distrito e notificação ficam na aplicação |
| Neo4j | Modelo de grafo sem necessidade para dados tabulares; descartado |

## Consequências

**Positivas**
- Entrega mais rápida, com duas tecnologias conhecidas e serviços gerenciados.
- As restrições de chave e tipo do Postgres reforçam as correções da auditoria da Fase 1.
- O RAW continua guardado, então qualquer camada padronizada pode ser reconstruída (princípio de reprodutibilidade de [`ARQUITETURA.md` §10](../ARQUITETURA.md)).

**Negativas e riscos**
- Dois serviços externos para operar, com credenciais e disponibilidade próprias.
- Sem Silver e Gold, a validação da camada padronizada passa a ser a única barreira de qualidade. Os testes de contrato precisam ser tratados como prioridade.
- Reprocessar depende de o RAW estar retido no Atlas. A política de retenção ainda não foi definida.
- Os limites do plano gratuito do Atlas e do Neon precisam ser verificados antes da demonstração.

## Requisitos de implementação

- Credenciais apenas por variável de ambiente: `MONGODB_URI` e `NEON_DATABASE_URL`, com as chaves em branco no `.env.example` (regra 5.2 de [`ai-rules/REGRAS.md`](../../ai-rules/REGRAS.md)).
- Testes unitários sem rede: adaptador em memória para a camada de armazenamento.
- Testes com Atlas e Neon ficam atrás do marcador `integracao`, fora do `pytest` padrão.
- Nenhum dado pessoal é gravado nos dois bancos. Os dados são públicos e agregados (LGPD, [`ARQUITETURA.md` §10](../ARQUITETURA.md)).
- Região: confirmar disponibilidade de São Paulo no Neon e no Atlas. Se não houver, registrar a região escolhida e o impacto na residência do dado.

## Documentos afetados

Não alterados nesta etapa; a atualização entra depois da aprovação deste registro:

- [`ARQUITETURA.md`](../ARQUITETURA.md) §3 a §7, §10 e §12
- [`HISTORIAS.md`](../HISTORIAS.md): INT-01 a INT-04 e PNL-01, que citam Silver e Gold
- [`PADROES.md`](../PADROES.md)
- [`ai-rules/REGRAS.md`](../../ai-rules/REGRAS.md) §4.2, que cita as camadas
- READMEs de `src/ingestao/`, `data/` e `conf/`

## Plano de migração

| Etapa | Entrega | Critério de pronto |
|---|---|---|
| A | Este registro aprovado e documentação ajustada | Aprovação do time |
| B | Camada de armazenamento e adaptador em memória | Os testes atuais continuam passando |
| C | Adaptador MongoDB para o RAW | Epidemiologia grava o RAW no Atlas, sem duplicar ao reprocessar |
| D | Camada padronizada no Neon e tabela `rejeitados` | 11.931 registros aceitos e 19 rejeitados, como hoje |
| E | Territorio, ANA e ocorrências | Cada fonte roda de forma independente |
| F | Exportação para o painel | O console lê a camada padronizada |

## Estado da implementação

| Etapa | Situação |
|---|---|
| A · documentação | Feita: ARQUITETURA §4.1, §10 e §12, PADROES §4 e §5, HISTORIAS (épicos Integração e Painel), REGRAS 4.2 e READMEs |
| B · interface de armazenamento | Feita: `src/ingestao/armazenamento.py`, com adaptador de arquivo como padrão |
| C · RAW no Atlas | Feita e validada no Atlas: epidemiologia (11.950 registros, 39,6 MB) sem duplicar ao reprocessar |
| D · padronizada no Neon | Feita e validada no Neon: `epidemiologia` com 11.931 linhas e 19 em `rejeitados` (todas sem bairro), `dim_bairro` 94, `dim_distrito` 8; recarga não duplica |
| E · demais fontes | Feita: território validado no Atlas (4 bases, 94 bairros); ocorrências e ANA seguem o mesmo caminho, mas não rodam contra a fonte real hoje (feed parado em 2023; ANA sem credenciais) |
| F · exportação para o painel | Feita: `exporta_painel.py` gera `prototipo/dados/recife-real.js` a partir do Neon e da RAW do território (94 bairros, 11.931 notificações, 21 sem bairro reconhecido) |

### Fonte nova: COP Recife (2026-10-28)

A ANA continua sem credenciais e o portal de Dados Abertos não tem dados de chuva. O Centro de
Operações do Recife publica chuva, rios (com cotas oficiais), previsão e áreas alagáveis no ArcGIS
público da prefeitura. Entraram 7 camadas (`conf/sources/cop_recife.yml`), no mesmo caminho RAW no
Atlas → contrato → Neon. Primeira carga: 27 leituras de indicadores, 25 de rios, 72 horas de previsão,
12 meses de chuva, 7.808 pulsos de pluviômetro, 267 áreas alagáveis e 181 pontos de alagamento — sem
rejeições. Para acumular histórico, a coleta horária precisa ser agendada.

## Pendências antes da aprovação

1. Região: o Neon foi criado em `us-east-2` (AWS, Ohio, EUA), fora do Brasil. Os dados são públicos, mas a residência fora do país precisa ser aceita pelo time ou o projeto migrado para `sa-east-1`. Confirmar também a região do cluster no Atlas.
2. Definir a retenção do RAW (por quanto tempo guardar cada coleta).
3. Definir quem é responsável pelas credenciais de cada serviço.
4. Revisão do time, pela regra de CODEOWNERS.
5. Agendar a coleta horária do COP (`--frequencia horaria`); sem isso, não há série histórica de chuva e rios.
6. Confirmar com o COP o uso dos dados e as dúvidas listadas em `conf/sources/README.md`.
