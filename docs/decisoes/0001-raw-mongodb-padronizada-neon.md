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
2. **Camada padronizada** em **Neon (PostgreSQL)**: tabelas tipadas, validadas pelos contratos de [`conf/contracts/`](../../conf/contracts/). Linhas rejeitadas vão para a tabela `rejeitados`, com o motivo registrado.
3. **Sem Silver e Gold nesta release.** O painel e o boletim leem a camada padronizada.
4. **Biblioteca de acesso:** `pymongo` para o RAW e `psycopg` (versão 3) para o Neon. O `pyarrow` sai das dependências de execução.

### Modelo mínimo da camada padronizada

- `dim_distrito` e `dim_bairro`: carregadas a partir das bases territoriais. `dim_bairro` referencia o distrito por chave estrangeira.
- `notificacao` (arboviroses): chave de negócio `(agravo, protocolo, data_notificacao)` como restrição `UNIQUE`, conforme BUG-07.
- `ocorrencia` (Defesa Civil): chave de negócio `protocolo`, quando a fonte tiver uma.
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

## Pendências antes da aprovação

1. Confirmar a região do Neon e do Atlas.
2. Definir a retenção do RAW (por quanto tempo guardar cada coleta).
3. Definir quem é responsável pelas credenciais de cada serviço.
4. Revisão do time, pela regra de CODEOWNERS.
