# Histórias de Usuário — Vigidesastres

> **Objetivo deste documento:** transformar a [arquitetura](ARQUITETURA.md) e o [planejamento CRISP-DM](CRISP-DM.md) em unidades de trabalho pequenas, independentes e prontas para virar **issues no GitHub**.
> Cada história é escrita para ser entendida por uma pessoa **ou por um assistente de IA** sem precisar de contexto extra: diz o que entregar, o que **não** entregar, de que outras histórias depende e como validar.

---

## Como usar este documento

### Fluxo geral

```text
docs/ARQUITETURA.md + docs/CRISP-DM.md
            │
            ▼
     docs/HISTORIAS.md   (este arquivo — fonte da verdade)
            │
            ▼
   Issues no GitHub      (1 issue por história, corpo copiado da seção)
            │
            ▼
  Branch por história ──► PR ──► merge em develop
```

### De história para issue

- **Título da issue:** `ID · Título` (ex.: `ING-02 · Coleta de dados epidemiológicos`).
- **Corpo da issue:** copiar as seções da história (História, Contexto, Escopo, Fora de escopo, Abordagem, Critérios de aceitação, Pronto quando, Para IA).
- **Labels:** as listadas na história (`epic:*`, `tipo:historia`, `fase:*`).
- **Milestone:** a fase do roadmap (`Fase 1`…`Fase 4`).
- **Épico:** criar uma issue-épico por área com uma *task list* linkando as issues filhas.
- **Board:** GitHub Projects com colunas `Backlog → Ready → Doing → Review → Done`.

### Branch por história

Seguindo o padrão do projeto: `feature/<id-em-minusculo>-<AAAA.MM.DD>` — ex.: `feature/ing-02-2026.09.10`.

### Como usar com IA

Ao pedir a um assistente para implementar uma história, forneça:

1. O texto completo da história (a seção inteira).
2. Os arquivos `docs/ARQUITETURA.md` e `docs/CRISP-DM.md` como contexto.
3. A instrução: **"implemente somente esta história, respeitando o bloco _Para IA_; não faça trabalho de outras histórias; crie os testes; não faça commit de dados dentro de `data/`."**

O bloco **Para IA** de cada história já resume: escopo mínimo, o que reutilizar, o que não fazer, arquivos a entregar e a saída esperada.

### Definição de Pronto para começar (Ready)

Uma história só entra em `Doing` quando: dependências concluídas (ou mockáveis), `resource_id`/endpoint identificados, contrato de dados definido (quando aplicável) e critérios de aceitação sem ambiguidade.

### Definição de Feito (Done) — vale para todas

- [ ] Todos os critérios de aceitação atendidos.
- [ ] Código na estrutura definida em **FND-01**.
- [ ] Testes automatizados passando (com dados mockados; sem depender de rede).
- [ ] `README` da pasta afetada atualizado (o que faz, como rodar).
- [ ] Nenhum dado real commitado em `data/` (pasta ignorada pelo Git).
- [ ] PR aberto contra `develop`, revisado por outra pessoa do time.

---

## Personas

| Persona | Papel | Usa o quê |
|---|---|---|
| **Eng. de Dados** | constrói ingestão e transformação (RAW → Gold) | conectores, pipelines, contratos de dados |
| **Cientista/Analista de Dados** | indicadores, regras de risco, modelos preditivos | camada Gold, notebooks, motor de risco/alertas |
| **Dev Front/Full-stack** | painel situacional e geração de boletim | camada Gold, `serving/`, protótipo HTML |
| **Analista da Vigilância / Defesa Civil** *(usuário final)* | acompanha o cenário e aciona equipes | painel, alertas |
| **Gestor** *(usuário final)* | decide e comunica | boletim situacional, KPIs |

---

## Épicos

| Épico | Label | Camada da arquitetura | Fase |
|---|---|---|---|
| **Fundação & Padrões** | `epic:fundacao` | estrutura, contratos, orquestração | 1 |
| **Ingestão** | `epic:ingestao` | Fontes → RAW → Bronze | 1 |
| **Integração** | `epic:integracao` | Bronze → Silver → Gold | 2 |
| **Indicadores & Risco** | `epic:indicadores` | Gold (indicadores + classificação de risco) | 2–3 |
| **Predição & Alertas** | `epic:predicao` | modelos + motor de alertas | 3 |
| **Painel & Boletim** | `epic:painel` | camada de entrega (serving) | 2–3 |

---

## Convenções

- **IDs:** `FND-`, `ING-`, `INT-`, `IND-`, `PRD-`, `PNL-`.
- **Tamanho:** `P` (≤1 dia), `M` (2–3 dias), `G` (>3 dias — considerar quebrar).
- **Camadas de dados:** `RAW` (original), `Bronze` (tipado), `Silver` (limpo/padronizado), `Gold` (integrado/indicadores). Ver [ARQUITETURA §4](ARQUITETURA.md#4-camadas-de-armazenamento-medallion).
- **`data/` é ignorada pelo Git.** Dados são sempre regeneráveis pelos pipelines.
- **Estrutura de pastas:** definida em **FND-01** e referenciada por todas as demais.

---

# ÉPICO: Fundação & Padrões

### FND-01 · Estrutura do repositório e convenções de projeto

**Épico:** Fundação · **Depende de:** — · **Tamanho:** P · **Labels:** `epic:fundacao`, `tipo:historia`, `fase:1`

**História**
Como pessoa desenvolvedora do time,
quero uma estrutura de pastas e convenções padronizadas,
para que todas as histórias seguintes tenham um lugar previsível para o código, a configuração e os dados.

**Contexto** — Base para todo o restante. Ver [ARQUITETURA §12](ARQUITETURA.md#12-stack-de-referência).

**Escopo**
- Criar a árvore de pastas abaixo, cada uma com um `README.md` curto explicando seu papel:

```text
src/
  ingestao/        # conectores + coleta por fonte        → RAW, Bronze
  processamento/   # transformações Bronze → Silver → Gold
  indicadores/     # cálculo de indicadores e risco (Gold)
  predicao/        # modelos preditivos e motor de alertas
  serving/         # geração de boletim, exportações, API interna
conf/
  sources/         # 1 arquivo por fonte (endpoint/resource_id, colunas, frequência)
  contracts/       # schema esperado por fonte (ver FND-02)
  territorio/      # tabela de referência bairro ↔ RPA ↔ Distrito Sanitário
data/              # IGNORADA pelo Git — raw/ bronze/ silver/ gold/
notebooks/         # exploração de dados (etapa Data Understanding do CRISP-DM)
tests/             # espelha a estrutura de src/
docs/
prototipo/
```

- Ajustar o `.gitignore` para ignorar `data/` mantendo `data/.gitkeep` e os `README.md` das subpastas.
- Documento `docs/PADROES.md`: convenção de nomes de tabela/coluna (snake_case, sem acento), formato de data (`YYYY-MM-DD HH:MM:SS`), particionamento (`<fonte>/<camada>/AAAA/MM/DD/`), e o padrão de branch/commit.

**Fora de escopo** — qualquer conector ou transformação real.

**Critérios de aceitação**
- [ ] Árvore de pastas criada, cada pasta de `src/` com `README.md`.
- [ ] `data/` presente, ignorada pelo Git, com `raw/ bronze/ silver/ gold/` e `.gitkeep`.
- [ ] `docs/PADROES.md` cobre nomes, datas, particionamento e branches.
- [ ] `README.md` raiz aponta para `docs/` (CRISP-DM, Arquitetura, Histórias, Padrões).

**Pronto quando** — Done global + time alinhado no `docs/PADROES.md`.

**Para IA** — Tarefa puramente estrutural. Não escreva lógica de negócio. Leia `docs/ARQUITETURA.md` (seções 3, 4, 12) para nomear as pastas coerentemente. Entregáveis: árvore de pastas, `README.md` por pasta de `src/`, `docs/PADROES.md`, `.gitignore` atualizado. Não crie dependências novas.

---

### FND-02 · Contratos de dados por fonte

**Épico:** Fundação · **Depende de:** FND-01 · **Tamanho:** M · **Labels:** `epic:fundacao`, `tipo:historia`, `fase:1`

**História**
Como Eng. de Dados,
quero um contrato explícito para cada fonte (colunas, tipos, obrigatoriedade, domínio de valores),
para que a ingestão valide os dados na entrada e falhe cedo quando a fonte mudar.

**Contexto** — [ARQUITETURA §10](ARQUITETURA.md#10-qualidade-governança-e-observabilidade). Usado por todas as histórias `ING-*` e pela camada Silver.

**Escopo**
- Um arquivo por fonte em `conf/contracts/` (ex.: `epidemiologia.yml`, `ocorrencias.yml`, `ana_nivel.yml`, `ana_chuva.yml`, `territorio.yml`).
- Cada contrato define: nome lógico da tabela, lista de campos (`nome`, `tipo`, `obrigatório`, `descrição`, `valores permitidos` quando fizer sentido), chave de negócio, campo de data de referência.
- Função utilitária `src/ingestao/contratos.py` que valida um lote contra um contrato e retorna as violações.

**Fora de escopo** — aplicar o contrato dentro de cada coletor (isso é feito nas histórias `ING-*`).

**Abordagem sugerida** — YAML declarativo + validação simples (checagem de colunas, tipos e nulos). Sem framework pesado.

**Critérios de aceitação**
- [ ] Contrato criado para: epidemiologia, ocorrências/Defesa Civil, ANA nível, ANA chuva, território.
- [ ] `validar(lote, contrato)` retorna lista vazia para um lote válido e lista de violações para um lote com coluna faltante, tipo errado ou nulo em campo obrigatório.
- [ ] Testes cobrindo os três tipos de violação.

**Pronto quando** — Done global + contratos revisados contra amostras reais das APIs.

**Para IA** — Entregue os arquivos YAML em `conf/contracts/` e `src/ingestao/contratos.py` + `tests/ingestao/test_contratos.py`. Baseie os campos nas amostras reais das APIs (peça ao time se não tiver acesso). Não implemente coleta. Mantenha a validação sem dependências externas além das já usadas no projeto.

---

### FND-03 · Esqueleto de orquestração e registro de execução

**Épico:** Fundação · **Depende de:** FND-01 · **Tamanho:** M · **Labels:** `epic:fundacao`, `tipo:historia`, `fase:1`

**História**
Como Eng. de Dados,
quero um esqueleto de orquestração que rode os coletores na frequência certa e registre cada execução,
para que as coletas sejam agendáveis, observáveis e reprocessáveis.

**Contexto** — [ARQUITETURA §3](ARQUITETURA.md#3-camada-de-ingestão-coleta) e [§9](ARQUITETURA.md#9-orquestração-e-frequência).

**Escopo**
- `src/ingestao/runner.py`: recebe o nome de uma fonte, localiza o coletor, executa, grava RAW particionada por data de coleta e registra a execução.
- Registro de execução (`data/_runs/` ou tabela de controle): fonte, início, fim, nº de registros, status (`ok`/`erro`), mensagem.
- Suporte a **reprocessamento**: rodar para uma data passada relê da RAW (se existir) ou recoleta.
- Um mapa `conf/schedule.yml` traduzindo a tabela de frequência da arquitetura (fonte → periodicidade).

**Fora de escopo** — os coletores em si; escolha da ferramenta de agendamento em produção (cron/orquestrador fica como nota).

**Critérios de aceitação**
- [ ] `runner.py <fonte>` executa um coletor "dummy" e grava um registro de execução com status `ok`.
- [ ] Coletor que lança exceção resulta em registro com status `erro` e mensagem, sem RAW parcial.
- [ ] `runner.py <fonte> --data AAAA-MM-DD` reprocessa a partição daquela data.
- [ ] `conf/schedule.yml` cobre todas as fontes da fase 1.

**Pronto quando** — Done global + um coletor real (ING-01) plugado com sucesso.

**Para IA** — Implemente o runner, o registro de execução e o `schedule.yml`. Crie um coletor `dummy` só para teste. Não implemente conectores reais. Padrões de path e nomenclatura vêm de `docs/PADROES.md` (FND-01). Entregáveis: `src/ingestao/runner.py`, `conf/schedule.yml`, `tests/ingestao/test_runner.py`.

---

# ÉPICO: Ingestão

### ING-01 · Conector genérico da API Dados Abertos Recife (CKAN)

**Épico:** Ingestão · **Depende de:** FND-01, FND-03 · **Tamanho:** M · **Labels:** `epic:ingestao`, `tipo:historia`, `fase:1`

**História**
Como Eng. de Dados,
quero um cliente reutilizável para a API DataStore do CKAN do Recife,
para que qualquer conjunto (epidemiologia, ocorrências, território…) seja coletado só informando o `resource_id`.

**Contexto** — [ARQUITETURA §2.2](ARQUITETURA.md#22-api-1--dados-abertos-recife-ckan). Base de ING-02, ING-03, ING-05.

**Escopo**
- `src/ingestao/recife_ckan.py` com função que recebe `resource_id`, `filtros` opcionais e devolve **todos** os registros, tratando a paginação (`limit`/`offset`).
- Tratamento de erro de rede/HTTP com nº de tentativas configurável.
- Retorno em formato tabular padronizado + metadados da coleta (resource_id, total, timestamp).
- Endpoint: `https://dados.recife.pe.gov.br/pt_BR/api/action/datastore_search`.

**Fora de escopo** — mapear colunas ou dar sentido de negócio aos campos (isso é por conjunto, nas histórias seguintes); camada Silver.

**Critérios de aceitação**
- [ ] Dado um `resource_id` com 2.500 registros e página de 1.000, quando coleto, então recebo 2.500 registros (3 requisições).
- [ ] Falha transitória de rede é re-tentada; falha persistente levanta erro claro.
- [ ] Metadados retornados incluem `resource_id`, `total` e `coletado_em`.
- [ ] Testes com API mockada cobrindo paginação e erro.

**Pronto quando** — Done global + validado contra 1 `resource_id` real.

**Para IA** — Implemente **apenas o cliente HTTP + paginação + retry**. Não crie coletores de conjuntos específicos. Reuse a lib HTTP já presente (`requests`). Entregáveis: `src/ingestao/recife_ckan.py`, `tests/ingestao/test_recife_ckan.py` (respostas CKAN mockadas). Saída: lista de dicionários + metadados; **não** grava em disco (quem grava é o runner / o coletor do conjunto).

---

### ING-02 · Coleta de dados epidemiológicos (arboviroses)

**Épico:** Ingestão · **Depende de:** ING-01, FND-02, FND-03 · **Tamanho:** M · **Labels:** `epic:ingestao`, `tipo:historia`, `fase:1`

**História**
Como Eng. de Dados,
quero coletar as notificações de arboviroses (dengue, zika, chikungunya) do portal Dados Abertos Recife,
para que os casos por bairro e semana epidemiológica fiquem disponíveis na camada Bronze.

**Contexto** — [ARQUITETURA §2.1 (epidemiológicos)](ARQUITETURA.md#21-domínios-de-dados), §2.5. Alimenta INT-04 e PNL-02.

**Escopo**
- Identificar o(s) `resource_id` de arboviroses no catálogo (registrar em `conf/sources/epidemiologia.yml`).
- Coletar via ING-01 (paginação completa) e gravar **RAW** (payload cru) + **Bronze** (tabela tipada, 1 linha por notificação) validando contra o contrato FND-02.
- Campos mínimos na Bronze: data de notificação, semana epidemiológica, bairro (texto original), agravo, classificação final, contagem.

**Fora de escopo** — normalização de nome de bairro e vínculo com RPA (Silver — INT-02); deduplicação (INT-03).

**Abordagem sugerida** — `src/ingestao/epidemiologia.py` orquestrado pelo `runner.py`; config isolada em `conf/sources/epidemiologia.yml`.

**Critérios de aceitação**
- [ ] Coleta baixa todos os registros do `resource_id` configurado (log com a contagem).
- [ ] RAW gravada em `data/raw/epidemiologia/AAAA/MM/DD/`.
- [ ] Bronze em `data/bronze/epidemiologia/` com o schema do contrato e tipos corretos.
- [ ] Reexecutar a mesma janela **não** duplica linhas na Bronze.
- [ ] Erro de coleta é registrado e **não** gera Bronze parcial.

**Pronto quando** — Done global + teste com pelo menos 4 semanas de dados reais.

**Para IA** — Implemente **somente RAW + Bronze** desta fonte. Leia `docs/ARQUITETURA.md` §2.2 e §4. **Reuse `src/ingestao/recife_ckan.py` (ING-01)** — não reimplemente HTTP/paginação. Nenhuma transformação semântica. Entregáveis: `src/ingestao/epidemiologia.py`, `conf/sources/epidemiologia.yml`, `tests/ingestao/test_epidemiologia.py` (resposta CKAN mockada). Saída: Parquet em `data/bronze/epidemiologia/`.

---

### ING-03 · Coleta de ocorrências e Defesa Civil

**Épico:** Ingestão · **Depende de:** ING-01, FND-02, FND-03 · **Tamanho:** M · **Labels:** `epic:ingestao`, `tipo:historia`, `fase:1`

**História**
Como Eng. de Dados,
quero coletar as ocorrências urbanas e registros da Defesa Civil (alagamento, deslizamento, queda de árvore…),
para que a situação por distrito possa cruzar chuva com ocorrências reais.

**Contexto** — [ARQUITETURA §2.1 (territoriais/assistenciais)](ARQUITETURA.md#21-domínios-de-dados), §5.4. Alimenta INT-04 e PNL-01.

**Escopo**
- `resource_id` de ocorrências em `conf/sources/ocorrencias.yml`.
- RAW + Bronze via ING-01, validando com o contrato FND-02.
- Campos mínimos: data/hora da ocorrência, tipo, bairro, latitude, longitude, status/desfecho.

**Fora de escopo** — validação geográfica dentro do município e vínculo com áreas de risco (Silver — INT-02).

**Critérios de aceitação**
- [ ] Coleta completa (log com contagem) e RAW particionada por data de coleta.
- [ ] Bronze com o schema do contrato; coordenadas preservadas como vieram.
- [ ] Idempotência garantida na Bronze.
- [ ] Registros sem coordenada são mantidos (não descartar na ingestão) e sinalizados.

**Pronto quando** — Done global + teste com 1 mês de dados reais.

**Para IA** — Igual a ING-02, trocando o conjunto: só RAW + Bronze, reusar ING-01, sem transformação. Entregáveis: `src/ingestao/ocorrencias.py`, `conf/sources/ocorrencias.yml`, teste com mock. Saída: `data/bronze/ocorrencias/`.

---

### ING-04 · Conector API ANA (HidroWeb) — chuva e nível de rios

**Épico:** Ingestão · **Depende de:** FND-01, FND-02, FND-03 · **Tamanho:** G · **Labels:** `epic:ingestao`, `tipo:historia`, `fase:1`

**História**
Como Eng. de Dados,
quero coletar da API da ANA a chuva acumulada e o nível (cota) das estações relevantes para o Recife,
para que os indicadores hidrológicos e a classificação de risco usem dados reais.

**Contexto** — [ARQUITETURA §2.3](ARQUITETURA.md#23-api-2--ana-hidroweb-service), §2.5, §6.2. Alimenta IND-01 e PRD-01.

**Escopo**
- `src/ingestao/ana_hidroweb.py`: cliente do `https://www.ana.gov.br/hidrowebservice/` (autenticação/cadastro se exigido, parsing XML/JSON).
- Lista de estações de interesse em `conf/sources/ana_estacoes.yml` (código, tipo, rio/bacia, cota de atenção, cota de alerta).
- Coleta de séries de **chuva** e de **nível/vazão** para as estações configuradas → RAW + Bronze (validadas por FND-02).
- Campos mínimos: código da estação, timestamp da medição, variável (`chuva_mm` / `nivel_cm` / `vazao`), valor.

**Fora de escopo** — cálculo de acumulados/janelas (IND-01); previsão (PRD-01).

**Abordagem sugerida** — isolar o parsing do web service numa função testável com payloads de exemplo salvos em `tests/fixtures/`.

**Critérios de aceitação**
- [ ] Para cada estação configurada, a série do período pedido é baixada e normalizada para o formato tabular padrão.
- [ ] Autenticação (se exigida) fica em configuração/variável de ambiente, nunca no código.
- [ ] RAW guarda a resposta original (XML/JSON); Bronze guarda a série tipada.
- [ ] Falha em uma estação não impede a coleta das demais (erro registrado por estação).
- [ ] Testes usam fixtures locais, sem chamar a ANA de verdade.

**Pronto quando** — Done global + séries reais de ≥2 estações por ≥30 dias.

**Para IA** — Implemente cliente + parsing + gravação RAW/Bronze desta fonte. **Não** invente as cotas de alerta: leia de `conf/sources/ana_estacoes.yml` (o time preenche). Segredos só via variável de ambiente. Não calcule indicadores. Entregáveis: `src/ingestao/ana_hidroweb.py`, `conf/sources/ana_estacoes.yml`, `tests/ingestao/test_ana_hidroweb.py` + fixtures. Saída: `data/bronze/ana_chuva/` e `data/bronze/ana_nivel/`.

---

### ING-05 · Coleta territorial cadastral (bairros, RPA, áreas de risco)

**Épico:** Ingestão · **Depende de:** ING-01, FND-02 · **Tamanho:** M · **Labels:** `epic:ingestao`, `tipo:historia`, `fase:1`

**História**
Como Eng. de Dados,
quero coletar as bases cadastrais de território do Recife (bairros, RPA, distritos, áreas de risco, malha populacional),
para que exista uma referência única para georreferenciar e agregar todos os outros dados.

**Contexto** — [ARQUITETURA §2.1 (territoriais)](ARQUITETURA.md#21-domínios-de-dados), §5.2. Base de INT-02 e IND-02.

**Escopo**
- `resource_id`(s) das bases territoriais em `conf/sources/territorio.yml`.
- RAW + Bronze via ING-01. Geometrias preservadas no formato de origem.
- Frequência **mensal** (dado cadastral).

**Fora de escopo** — montar a tabela de correspondência bairro ↔ RPA ↔ DS (isso é INT-02, na Silver).

**Critérios de aceitação**
- [ ] Bronze com bairros, RPA, distritos e áreas de risco (uma tabela por base).
- [ ] Geometrias/coordenadas preservadas e legíveis.
- [ ] População por bairro disponível (do Recife ou IBGE — registrar a origem no `conf`).
- [ ] Idempotência garantida.

**Pronto quando** — Done global + bases conferidas contra o mapa oficial de RPAs.

**Para IA** — Só RAW + Bronze das bases cadastrais, reusando ING-01. Não construa a tabela de referência derivada. Entregáveis: `src/ingestao/territorio.py`, `conf/sources/territorio.yml`, teste com mock. Saída: `data/bronze/territorio_*`.

---

# ÉPICO: Integração

### INT-01 · Camada de calendário e padronização temporal

**Épico:** Integração · **Depende de:** FND-01 · **Tamanho:** P · **Labels:** `epic:integracao`, `tipo:historia`, `fase:2`

**História**
Como Cientista de Dados,
quero uma dimensão de calendário e funções de padronização temporal,
para que todas as tabelas Silver/Gold compartilhem as mesmas chaves de tempo (dia, semana epidemiológica, período chuvoso).

**Contexto** — [ARQUITETURA §5.1](ARQUITETURA.md#51-padronização-temporal).

**Escopo**
- Tabela de calendário (dia → semana ISO, **semana epidemiológica**, mês, ano, dia da semana, flag de período chuvoso do Recife).
- Funções: `para_timestamp_padrao(valor)` → `YYYY-MM-DD HH:MM:SS`; `semana_epidemiologica(data)`; `periodo_chuvoso(data)`.
- Documentar a regra de período chuvoso adotada (meses) em `docs/PADROES.md`.

**Fora de escopo** — janelas móveis de chuva (IND-01).

**Critérios de aceitação**
- [ ] Calendário cobre 2019→ano atual+1 sem furos.
- [ ] `semana_epidemiologica` bate com a definição oficial em casos de virada de ano (testar 31/12 e 01/01).
- [ ] `para_timestamp_padrao` lida com os formatos que aparecem nas fontes (data só, data+hora, com/sem timezone).

**Pronto quando** — Done global.

**Para IA** — Módulo utilitário puro, sem I/O de rede. `src/processamento/calendario.py` + `tests/processamento/test_calendario.py` cobrindo viradas de ano e formatos de data variados. Não dependa de libs novas se `pandas` já resolver.

---

### INT-02 · Tabela de referência territorial e georreferenciamento

**Épico:** Integração · **Depende de:** ING-05, INT-01 · **Tamanho:** G · **Labels:** `epic:integracao`, `tipo:historia`, `fase:2`

**História**
Como Cientista de Dados,
quero uma tabela única que relacione bairro ↔ RPA ↔ Distrito Sanitário ↔ geometria ↔ população,
e uma função que atribua o território a qualquer registro (por nome de bairro ou por coordenada),
para que todos os cruzamentos usem o mesmo recorte geográfico.

**Contexto** — [ARQUITETURA §5.2](ARQUITETURA.md#52-padronização-territorial).

**Escopo**
- Silver `territorio_ref`: uma linha por bairro com RPA, DS, microrregião, geometria, população e centróide.
- Normalização de nome de bairro (acentos, caixa, grafias alternativas) com tabela de sinônimos em `conf/territorio/aliases.csv`.
- `resolver_territorio(nome_bairro=None, lat=None, lon=None)` → `{bairro, rpa, ds}`; usa nome quando disponível, senão *point-in-polygon* pela coordenada.
- Flag de qualidade quando não resolve (`territorio_indefinido`).

**Fora de escopo** — aplicar isso nas tabelas de fato (feito em INT-03/INT-04).

**Critérios de aceitação**
- [ ] `territorio_ref` tem todos os bairros oficiais do Recife, cada um com RPA e DS.
- [ ] Nome com acento/caixa diferentes resolve para o mesmo bairro.
- [ ] Coordenada dentro de um bairro resolve para ele; coordenada fora do município retorna `territorio_indefinido`.
- [ ] Cobertura de teste para nome exato, alias, coordenada válida e coordenada inválida.

**Pronto quando** — Done global + conferência visual de 10 bairros no mapa.

**Para IA** — Entregue a tabela Silver + `src/processamento/territorio.py` com `resolver_territorio`. Consuma a Bronze de ING-05; não recolete nada. *Point-in-polygon* pode usar `shapely`/`geopandas` (adicionar como dependência é aceitável aqui — justifique no PR). Testes com um mini-conjunto de polígonos em `tests/fixtures/`. Não altere tabelas de outras camadas.

---

### INT-03 · Silver — limpeza e padronização das tabelas de fato

**Épico:** Integração · **Depende de:** ING-02, ING-03, ING-04, INT-01, INT-02, FND-02 · **Tamanho:** G · **Labels:** `epic:integracao`, `tipo:historia`, `fase:2`

**História**
Como Eng. de Dados,
quero transformar as tabelas Bronze (epidemiologia, ocorrências, chuva, nível) em tabelas Silver limpas,
para que a camada Gold trabalhe com dados sem duplicidade, sem inconsistência e já georreferenciados.

**Contexto** — [ARQUITETURA §5.3](ARQUITETURA.md#53-qualidade).

**Escopo**
- Para cada fonte: deduplicar por chave de negócio; padronizar datas (INT-01); resolver território (INT-02); padronizar categorias (`agravo`, `tipo_ocorrencia`, `status`); tratar nulos conforme regra por campo.
- Corrigir inconsistências temporais (ex.: desfecho anterior à abertura → sinalizar, não apagar).
- Coluna de qualidade por linha (`flags` com os problemas encontrados).
- Silver particionada e documentada (dicionário de dados por tabela).

**Fora de escopo** — agregações e cruzamentos entre fontes (INT-04).

**Critérios de aceitação**
- [ ] Nenhuma duplicata por chave de negócio nas tabelas Silver.
- [ ] 100% das linhas com `bairro`/`rpa`/`ds` preenchidos **ou** marcadas `territorio_indefinido`.
- [ ] Datas todas no formato padrão; inconsistências temporais sinalizadas em `flags`.
- [ ] Contagem de linhas Bronze→Silver reconciliada e registrada (quantas caíram e por quê).
- [ ] Dicionário de dados publicado em `docs/DICIONARIO_DADOS.md`.

**Pronto quando** — Done global + revisão dos `flags` mais frequentes com o time.

**Para IA** — Implemente as transformações Bronze→Silver **reutilizando** `calendario.py` (INT-01) e `territorio.py` (INT-02) — não reimplemente. Uma função de transformação por fonte em `src/processamento/silver_<fonte>.py`. Nunca descarte linha silenciosamente: registre em `flags` e no log de reconciliação. Testes com amostras Bronze em `tests/fixtures/`. Saída: `data/silver/<fonte>/`.

---

### INT-04 · Gold — situação integrada por distrito e por dia

**Épico:** Integração · **Depende de:** INT-03 · **Tamanho:** G · **Labels:** `epic:integracao`, `tipo:historia`, `fase:2`

**História**
Como Cientista/Analista de Dados,
quero uma tabela Gold com uma linha por **distrito × dia** reunindo chuva, nível de rio, ocorrências e casos de arbovirose,
para que o painel, os indicadores e os modelos consumam uma base única e pronta.

**Contexto** — [ARQUITETURA §5.4](ARQUITETURA.md#54-cruzamentos-na-camada-gold) e [§6.2](ARQUITETURA.md#62-indicadores-situacionais-gold).

**Escopo**
- Grão: `distrito_sanitario × data`. Também gerar a versão `bairro × data` quando fizer sentido.
- Colunas: chuva do dia e acumulada 24h/72h (da estação associada ao distrito), nível/cota do rio associado, nº de ocorrências por tipo, nº de notificações de arbovirose, população residente e população em área de risco.
- Mapa `conf/territorio/distrito_estacao.yml` associando cada distrito às estações ANA e rios de referência.
- Tabela também exposta em formato "largo" pronto para o painel (INT-04 → PNL-01).

**Fora de escopo** — classificação de risco (IND-03) e previsão (PRD-*).

**Critérios de aceitação**
- [ ] Uma linha por distrito por dia no período coberto, sem buracos (dias sem evento = zeros, não ausência).
- [ ] Valores reconciliam com as Silver de origem (somatórios batem).
- [ ] Acumulados 24h/72h corretos em casos de borda (início da série, dia sem medição).
- [ ] Documentada em `docs/DICIONARIO_DADOS.md`.

**Pronto quando** — Done global + validação de 1 semana conhecida (ex.: um evento de chuva real) com o time.

**Para IA** — Consuma **somente** as tabelas Silver (INT-03) + `territorio_ref` (INT-02) + `conf/territorio/distrito_estacao.yml`. Não recolete nem recalcule limpeza. Produza `data/gold/situacao_distrito_dia/` e `data/gold/situacao_bairro_dia/`. Testes de reconciliação (soma Silver == soma Gold) e de bordas de janela. Não embuta regra de risco aqui.

---

# ÉPICO: Indicadores & Risco

### IND-01 · Indicadores meteo-hidrológicos

**Épico:** Indicadores · **Depende de:** INT-04 · **Tamanho:** M · **Labels:** `epic:indicadores`, `tipo:historia`, `fase:2`

**História**
Como Analista da Vigilância,
quero ver a chuva acumulada 24h comparada com a média histórica e o nível do rio comparado com a cota de alerta,
para saber rapidamente se o cenário está fora do normal.

**Contexto** — [ARQUITETURA §6.2](ARQUITETURA.md#62-indicadores-situacionais-gold) e [§11](ARQUITETURA.md#11-relação-com-o-protótipo) (KPIs do protótipo).

**Escopo**
- Sobre o Gold (INT-04), calcular por distrito/dia: chuva 24h, desvio % vs. média histórica do mês, nível atual, folga/déficit em relação à cota de atenção e de alerta, tendência (subindo/estável/descendo) nas últimas N horas.
- Série de 7 dias de chuva diária por distrito (para o gráfico do painel).

**Fora de escopo** — juntar tudo num nível de risco único (IND-03).

**Critérios de aceitação**
- [ ] Para um dia com 86 mm e média histórica de 64 mm, o indicador aponta "+34% acima da média" (arredondamento definido).
- [ ] Comparação de nível usa as cotas de `conf/sources/ana_estacoes.yml`.
- [ ] Série de 7 dias disponível por distrito no formato que o painel espera.
- [ ] Bordas: sem histórico suficiente → indicador marcado como "indisponível", não erro.

**Pronto quando** — Done global.

**Para IA** — Funções puras sobre o Gold, saída em nova tabela `data/gold/indicadores_meteo_hidro/`. Sem coleta, sem modelo estatístico (média simples histórica basta). `src/indicadores/meteo_hidro.py` + testes com casos numéricos fixos (incluindo o exemplo dos 86 mm). Reutilize as janelas já calculadas em INT-04 quando existirem.

---

### IND-02 · Indicador de população exposta em áreas de risco

**Épico:** Indicadores · **Depende de:** INT-02, INT-04 · **Tamanho:** M · **Labels:** `epic:indicadores`, `tipo:historia`, `fase:2`

**História**
Como Gestor,
quero saber quantas pessoas vivem nas áreas de risco de cada distrito em situação de atenção,
para dimensionar a resposta.

**Contexto** — [ARQUITETURA §5.2](ARQUITETURA.md#52-padronização-territorial), §11 (KPI "População em áreas de risco").

**Escopo**
- Cruzar polígonos de áreas de risco (ING-05) com a malha populacional para estimar população exposta por bairro/distrito.
- Documentar a premissa de estimativa (densidade uniforme por bairro, ou fonte melhor se houver).

**Fora de escopo** — modelagem de vulnerabilidade social.

**Critérios de aceitação**
- [ ] População exposta por distrito disponível na Gold.
- [ ] Soma das populações expostas ≤ população total do distrito.
- [ ] Premissa de cálculo registrada em `docs/DICIONARIO_DADOS.md`.

**Pronto quando** — Done global + ordem de grandeza validada com o time.

**Para IA** — Cálculo geoespacial sobre dados já ingeridos/derivados; sem coleta. `src/indicadores/populacao_exposta.py` + teste com polígonos sintéticos. Deixe a premissa de estimativa parametrizável.

---

### IND-03 · Motor de classificação de risco por distrito

**Épico:** Indicadores · **Depende de:** IND-01, IND-02, INT-04 · **Tamanho:** M · **Labels:** `epic:indicadores`, `tipo:historia`, `fase:3`

**História**
Como Analista da Vigilância,
quero que cada distrito receba um nível de risco (baixo, moderado, alto, crítico) a partir de regras claras e ajustáveis,
para priorizar o monitoramento sem depender de leitura manual de vários números.

**Contexto** — [ARQUITETURA §6.4](ARQUITETURA.md#64-classificação-de-risco) (tabela de níveis) e §11.

**Escopo**
- Regras parametrizadas em `conf/risco/regras.yml` (limiares de chuva 24h, cota do rio, presença/severidade de ocorrências, tendência).
- `classificar_risco(linha_gold)` → nível + justificativa (quais critérios dispararam).
- Tabela Gold `risco_distrito_dia` com nível, critérios acionados e timestamp.

**Fora de escopo** — previsão de risco futuro (PRD-03).

**Critérios de aceitação**
- [ ] Os 4 exemplos da tabela da arquitetura (§6.4) classificam nos níveis esperados.
- [ ] Mudar um limiar no YAML muda o resultado sem tocar no código.
- [ ] A justificativa lista os critérios que elevaram o nível.
- [ ] Distrito sem dados suficientes → nível "indeterminado".

**Pronto quando** — Done global + calibragem inicial dos limiares revisada com Defesa Civil (ou orientador).

**Para IA** — Motor de regras determinístico e testável, **sem ML**. Leia limiares de `conf/risco/regras.yml`. `src/indicadores/risco.py` + `tests/indicadores/test_risco.py` cobrindo os 4 exemplos da §6.4 e o caso "indeterminado". Saída: `data/gold/risco_distrito_dia/`.

---

# ÉPICO: Predição & Alertas

### PRD-01 · Baseline de previsão de chuva e nível de rio

**Épico:** Predição · **Depende de:** INT-04, IND-01 · **Tamanho:** G · **Labels:** `epic:predicao`, `tipo:historia`, `fase:3`

**História**
Como Cientista de Dados,
quero um modelo-base que preveja a chuva acumulada e o nível do rio para as próximas 24–48h por distrito,
para que os alertas possam ser preditivos e não apenas reativos.

**Contexto** — [ARQUITETURA §6.3](ARQUITETURA.md#63-modelos-preditivos), CRISP-DM seções 4–5.

**Escopo**
- Preparar o dataset de treino a partir do Gold (features: histórico de chuva/nível, sazonalidade, mês, período chuvoso).
- Treinar um baseline (ex.: modelo sazonal ingênuo + um modelo de série temporal) por estação/distrito.
- Avaliar com *backtesting* (MAE/MAPE) e registrar as métricas em `docs/AVALIACAO_MODELOS.md`.
- Função `prever(distrito, horizonte)` a partir do modelo salvo.

**Fora de escopo** — deploy em tempo real; integração com previsão meteorológica externa (fase 4).

**Critérios de aceitação**
- [ ] Dataset de treino/teste reprodutível a partir do Gold (script versionado).
- [ ] Baseline sazonal ingênuo documentado como referência a superar.
- [ ] Métricas de *backtesting* por distrito em `docs/AVALIACAO_MODELOS.md`.
- [ ] `prever()` carrega o modelo salvo e devolve valor + intervalo simples.
- [ ] Sem *data leakage* (features usam só informação disponível no instante da previsão) — teste específico.

**Pronto quando** — Done global + o modelo supera o baseline ingênuo em pelo menos metade dos distritos.

**Para IA** — Trabalhe só sobre o Gold (INT-04); não recolete. Comece pelo baseline ingênuo antes de qualquer modelo complexo. Bibliotecas de série temporal (`statsmodels`/`prophet`) são aceitáveis — registre no PR. Entregáveis: `src/predicao/chuva_nivel.py`, script de dataset, modelo serializado em `models/` (fora de `data/`), `docs/AVALIACAO_MODELOS.md`, testes de ausência de leakage.

---

### PRD-02 · Previsão de notificações de arbovirose por bairro

**Épico:** Predição · **Depende de:** INT-04, INT-01 · **Tamanho:** G · **Labels:** `epic:predicao`, `tipo:historia`, `fase:3`

**História**
Como Analista da Vigilância,
quero uma projeção das notificações de arbovirose por bairro para as próximas semanas epidemiológicas,
para antecipar pressão sobre a rede de saúde.

**Contexto** — [ARQUITETURA §6.3](ARQUITETURA.md#63-modelos-preditivos), §11 (gráfico de arboviroses).

**Escopo**
- Dataset por `bairro × semana epidemiológica` (features: histórico de casos, sazonalidade, chuva/temperatura defasadas).
- Baseline (média móvel sazonal) + um modelo alternativo; *backtesting* com janelas deslizantes.
- Métricas por bairro em `docs/AVALIACAO_MODELOS.md`.

**Fora de escopo** — modelo epidemiológico mecanicista (SIR etc.).

**Critérios de aceitação**
- [ ] Previsão para as próximas 4 semanas por bairro.
- [ ] *Backtesting* documentado; comparação com o baseline.
- [ ] Sem leakage (features com defasagem correta) — teste específico.
- [ ] Bairros com histórico curto tratados explicitamente (previsão marcada como baixa confiança).

**Pronto quando** — Done global + revisão dos resultados com o time.

**Para IA** — Igual em disciplina ao PRD-01: baseline primeiro, só Gold como fonte, sem leakage. Entregáveis: `src/predicao/arboviroses.py`, script de dataset, modelo em `models/`, seção em `docs/AVALIACAO_MODELOS.md`, testes.

---

### PRD-03 · Motor de alertas preditivos

**Épico:** Predição · **Depende de:** IND-03, PRD-01 · **Tamanho:** M · **Labels:** `epic:predicao`, `tipo:historia`, `fase:3`

**História**
Como Analista da Vigilância,
quero receber alertas quando o risco atual **ou previsto** de um distrito cruzar um limiar,
para agir antes do evento se agravar.

**Contexto** — [ARQUITETURA §7](ARQUITETURA.md#7-camada-de-entrega-serving) (Alertas Preditivos), §9.

**Escopo**
- Regras de disparo em `conf/alertas/regras.yml` (nível de risco atingido, risco previsto ≥ X em 24h, nível de rio previsto acima da cota).
- Ciclo de vida do alerta: `aberto → atualizado → encerrado`; deduplicação (não reabrir alerta idêntico ativo).
- Tabela `data/gold/alertas/` com tipo, distrito, severidade, gatilho, criado_em, encerrado_em.
- Cada alerta com texto curto pronto para exibição (feed do painel) e uma explicação do gatilho.

**Fora de escopo** — envio por e-mail/SMS/push (fase posterior); UI (PNL-02).

**Critérios de aceitação**
- [ ] Distrito que entra em risco `alto` gera 1 alerta; enquanto persistir, é atualizado e não duplicado.
- [ ] Quando o risco cede, o alerta é encerrado com timestamp.
- [ ] Previsão de nível acima da cota de alerta gera alerta preditivo mesmo com situação atual normal.
- [ ] Regras editáveis via YAML sem mudança de código.

**Pronto quando** — Done global + simulação com um evento histórico real gera a linha do tempo de alertas esperada.

**Para IA** — Motor determinístico sobre `risco_distrito_dia` (IND-03) e as previsões (PRD-01). Sem novo modelo. Foque no ciclo de vida e na deduplicação. `src/predicao/alertas.py` + testes cobrindo abertura, atualização, encerramento, dedupe e alerta puramente preditivo. Saída: `data/gold/alertas/`.

---

# ÉPICO: Painel & Boletim

### PNL-01 · Ligar o painel aos dados reais (KPIs e situação por distrito)

**Épico:** Painel · **Depende de:** INT-04, IND-01, IND-03 · **Tamanho:** G · **Labels:** `epic:painel`, `tipo:historia`, `fase:2`

**História**
Como Analista da Vigilância,
quero que o painel mostre os KPIs e a tabela de distritos com dados reais da camada Gold em vez dos valores simulados,
para usar a ferramenta na rotina.

**Contexto** — [ARQUITETURA §7](ARQUITETURA.md#7-camada-de-entrega-serving) e [§11](ARQUITETURA.md#11-relação-com-o-protótipo). Protótipo: [`prototipo/v1-prototipo-aervita.html`](../prototipo/v1-prototipo-aervita.html).

**Escopo**
- Endpoint/arquivo de dados que o painel consome (ex.: `serving/` gera um JSON por atualização a partir do Gold).
- Substituir no painel: os 4 KPIs (chuva 24h, distritos em atenção, alertas ativos, população em risco) e a tabela "Situação por Distrito Sanitário".
- Manter o layout do protótipo; trocar apenas a origem dos dados. Exibir data/hora da última atualização real.
- Estado de erro/carregando quando o dado não estiver disponível.

**Fora de escopo** — gráficos de série (PNL-02) e boletim (PNL-03).

**Critérios de aceitação**
- [ ] KPIs e tabela refletem a Gold do momento (conferível contra a tabela `situacao_distrito_dia`).
- [ ] "Atualizado em" mostra o timestamp real do dado, não o horário do navegador.
- [ ] Sem dado → painel mostra estado vazio claro, não números falsos.
- [ ] Nenhum dado sensível/simulado remanescente no HTML.

**Pronto quando** — Done global + validação lado a lado (Gold × painel) com o time.

**Para IA** — Camada de entrega + ajuste do HTML. Defina um contrato JSON simples (documente em `serving/README.md`) e faça `src/serving/exporta_painel.py` gerá-lo a partir do Gold. No HTML, troque os arrays fixos por *fetch* do JSON, preservando classes/estrutura. Não redesenhe o painel. Testes: geração do JSON a partir de um Gold de exemplo.

---

### PNL-02 · Gráficos de série e feed de alertas no painel

**Épico:** Painel · **Depende de:** PNL-01, IND-01, PRD-03 · **Tamanho:** M · **Labels:** `epic:painel`, `tipo:historia`, `fase:3`

**História**
Como Analista da Vigilância,
quero ver no painel a série de 7 dias de chuva e de arboviroses e a lista de alertas ativos reais,
para entender a tendência e o que está aberto agora.

**Contexto** — [ARQUITETURA §11](ARQUITETURA.md#11-relação-com-o-protótipo) (gráficos e painel "Alertas Ativos").

**Escopo**
- Incluir no JSON de PNL-01: série de 7 dias (chuva diária e casos/dia) e a lista de alertas ativos (de PRD-03) com severidade, título, horário e descrição do gatilho.
- Ligar os dois gráficos de barras e o painel "Alertas Ativos" do protótipo a esses dados.
- Ordenar alertas por severidade e recência.

**Fora de escopo** — filtros/interação avançada; notificações externas.

**Critérios de aceitação**
- [ ] Gráficos refletem os últimos 7 dias da Gold para o distrito/visão selecionada.
- [ ] Feed lista exatamente os alertas com status `aberto`/`atualizado`.
- [ ] Sem alertas → mensagem "nenhum alerta ativo", não lista vazia sem contexto.

**Pronto quando** — Done global.

**Para IA** — Estender o contrato JSON e o `exporta_painel.py`; ligar os elementos já existentes no HTML. Reutilize o `buildBars` do protótipo. Não crie biblioteca de gráficos nova. Testes: JSON com série e alertas a partir de fixtures.

---

### PNL-03 · Geração do boletim situacional automático

**Épico:** Painel · **Depende de:** INT-04, IND-03, PRD-03 · **Tamanho:** M · **Labels:** `epic:painel`, `tipo:historia`, `fase:3`

**História**
Como Gestor,
quero gerar um boletim situacional em texto, consolidando automaticamente chuva, risco por distrito, ocorrências e arboviroses do momento,
para distribuir como nota técnica sem montar à mão.

**Contexto** — [ARQUITETURA §7](ARQUITETURA.md#7-camada-de-entrega-serving) e §11 ("Boletim Situacional Automático"). Protótipo já tem o botão e o formato-alvo do texto.

**Escopo**
- `src/serving/boletim.py`: lê a Gold (situação, risco, alertas) e preenche um template de texto (resumo, destaques, recomendação, rodapé com data/hora e fontes).
- Regras de redação: nível geral = pior nível entre os distritos; destaques = distritos em `alto`/`crítico` + variações epidemiológicas relevantes + previsão de chuva quando houver.
- Saída em texto e em Markdown; disponível para o botão "Gerar boletim agora" do painel.

**Fora de escopo** — geração de PDF; envio automático.

**Critérios de aceitação**
- [ ] Para um Gold com 1 distrito `crítico` e 1 `alto`, o boletim abre com "risco geral CRÍTICO" e lista os dois distritos nos destaques.
- [ ] Sempre traz data/hora de geração e a lista de fontes usadas.
- [ ] Texto reproduzível: mesmo Gold → mesmo boletim.
- [ ] Deixa claro quando algum dado não estava disponível (não inventa número).

**Pronto quando** — Done global + 3 boletins de datas reais revisados pelo time.

**Para IA** — Função determinística Gold → texto, com template em `conf/boletim/template.md`. Sem chamada a serviço externo, sem modelo de linguagem. Espelhe o formato do texto que já aparece no protótipo. `src/serving/boletim.py` + `tests/serving/test_boletim.py` com o cenário "1 crítico + 1 alto" e o cenário "dado indisponível".

---

## Ordem sugerida de execução

```text
Fase 1  FND-01 ─► FND-02 ─► FND-03 ─► ING-01 ─┬─► ING-02
                                              ├─► ING-03
                                              └─► ING-05
                            ING-04 (paralelo, depende só de FND-*)

Fase 2  INT-01 ─► INT-02 ─► INT-03 ─► INT-04 ─┬─► IND-01 ─► IND-03
                                              ├─► IND-02
                                              └─► PNL-01

Fase 3  IND-03 ─► PRD-03            PRD-01 ─► PRD-03 ─► PNL-02
        INT-04 ─► PRD-01/PRD-02     INT-04 ─► PNL-03

Fase 4  (roadmap) fontes complementares: APAC, INMET, CPRH, MonitorAr, DATASUS
```

## Índice das histórias

| ID | Título | Épico | Fase | Tam. |
|---|---|---|---|---|
| FND-01 | Estrutura do repositório e convenções | Fundação | 1 | P |
| FND-02 | Contratos de dados por fonte | Fundação | 1 | M |
| FND-03 | Esqueleto de orquestração e registro de execução | Fundação | 1 | M |
| ING-01 | Conector genérico CKAN Recife | Ingestão | 1 | M |
| ING-02 | Coleta epidemiológica (arboviroses) | Ingestão | 1 | M |
| ING-03 | Coleta de ocorrências / Defesa Civil | Ingestão | 1 | M |
| ING-04 | Conector ANA HidroWeb (chuva e nível) | Ingestão | 1 | G |
| ING-05 | Coleta territorial cadastral | Ingestão | 1 | M |
| INT-01 | Calendário e padronização temporal | Integração | 2 | P |
| INT-02 | Referência territorial e georreferenciamento | Integração | 2 | G |
| INT-03 | Silver — limpeza das tabelas de fato | Integração | 2 | G |
| INT-04 | Gold — situação por distrito e dia | Integração | 2 | G |
| IND-01 | Indicadores meteo-hidrológicos | Indicadores | 2 | M |
| IND-02 | População exposta em áreas de risco | Indicadores | 2 | M |
| IND-03 | Motor de classificação de risco | Indicadores | 3 | M |
| PRD-01 | Baseline de previsão de chuva e nível | Predição | 3 | G |
| PRD-02 | Previsão de arboviroses por bairro | Predição | 3 | G |
| PRD-03 | Motor de alertas preditivos | Predição | 3 | M |
| PNL-01 | Painel com dados reais (KPIs e distritos) | Painel | 2 | G |
| PNL-02 | Gráficos de série e feed de alertas | Painel | 3 | M |
| PNL-03 | Boletim situacional automático | Painel | 3 | M |
