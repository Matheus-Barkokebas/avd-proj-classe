# Plano de Ação — AerVita

> **Porta de entrada do projeto.** Quem for desenvolver (pessoa ou assistente de IA) começa por aqui:
> entende as siglas, vê a ordem das issues e sabe qual pegar primeiro.

## Onde está cada coisa

| Documento | Para quê |
|---|---|
| [`CRISP-DM.md`](CRISP-DM.md) | O problema de negócio e a metodologia (o *porquê* do projeto) |
| [`ARQUITETURA.md`](ARQUITETURA.md) | O fluxo técnico: fontes → ingestão → RAW/Bronze/Silver/Gold → modelos → entrega |
| [`HISTORIAS.md`](HISTORIAS.md) | As 21 histórias detalhadas (escopo, critérios de aceitação, bloco "Para IA") |
| **Este documento** | Ordem de execução, caminho crítico, significado das siglas |
| [GitHub Issues](https://github.com/Matheus-Barkokebas/avd-proj-classe/issues) · [Project AerVita](https://github.com/users/Matheus-Barkokebas/projects/1) | O trabalho em si (#5–#31) e o quadro |

---

## As siglas dos épicos

Cada história tem um ID `SIGLA-NN` (ex.: `ING-02`). A sigla diz a que **épico** ela pertence, e cada épico
corresponde a uma **camada do fluxo de dados** da arquitetura. As siglas são abreviações em português:

| Sigla | Épico | Origem do nome | Camada na arquitetura | Por que existe | Issues |
|---|---|---|---|---|---|
| **FND** | Fundação & Padrões | **FuNDação** | estrutura, contratos, orquestração | Sem estrutura de pastas, contrato de dados e um "runner", toda história de ingestão reinventaria o básico e sairia inconsistente. | #5–#7 · épico #26 |
| **ING** | Ingestão | **INGestão** | Fontes → RAW → Bronze | Trazer os dados das APIs (Recife CKAN e ANA) para dentro do projeto, guardando o original e uma versão tipada. É a matéria-prima de todo o resto. | #8–#12 · épico #27 |
| **INT** | Integração | **INTegração** | Bronze → Silver → Gold | Limpar, padronizar tempo e território e **cruzar** as fontes numa tabela única (distrito × dia). É o que transforma dados soltos em base analítica. | #13–#16 · épico #28 |
| **IND** | Indicadores & Risco | **INDicadores** | Gold (indicadores + regra de risco) | Traduzir a base integrada em números que o time entende (chuva vs. média, nível vs. cota) e num nível de risco por distrito. | #17–#19 · épico #29 |
| **PRD** | Predição & Alertas | **PReDição** | modelos + motor de alertas | Sair do "o que está acontecendo" para o "o que vai acontecer": prever chuva/nível/arboviroses e disparar alerta antes do agravamento. | #20–#22 · épico #30 |
| **PNL** | Painel & Boletim | **PaiNeL** | camada de entrega (serving) | Levar tudo para o usuário final: o painel situacional (o protótipo com dados reais), o feed de alertas e o boletim automático. | #23–#25 · épico #31 |

**Por que dividir assim?** Os épicos espelham as etapas do fluxo de dados. Cada um é uma fatia testável de
forma independente (com dados mockados), o que permite **paralelizar** o trabalho e medir progresso por camada.
As issues-épico (#26–#31) agregam as filhas e mostram o percentual concluído.

Outras marcações nas issues:

- `epic:<nome>` — a que épico pertence · `tipo:historia` / `tipo:epico`
- `fase:1`…`fase:4` e o **milestone** correspondente — em que onda do roadmap entra

---

## Ordem de execução

Ondas sucessivas; dentro de uma onda, as issues podem correr em paralelo (respeitando as dependências).

### Onda 0 — Fundação  *(destrava todo o resto)*
1. **#5 · FND-01** Estrutura do repositório e convenções → **começa aqui, bloqueia quase tudo**
2. **#6 · FND-02** Contratos de dados por fonte
3. **#7 · FND-03** Esqueleto de orquestração (runner + registro de execução)

### Onda 1 — Ingestão  *(Fase 1)*
4. **#8 · ING-01** Conector genérico CKAN Recife → base de ING-02/03/05
5. Em paralelo depois de #8: **#9 · ING-02** (epidemiologia), **#10 · ING-03** (ocorrências), **#12 · ING-05** (território)
6. **#11 · ING-04** Conector ANA HidroWeb → independente dos anteriores, pode andar em paralelo com #8

### Onda 2 — Integração  *(Fase 2)*
7. **#13 · INT-01** Calendário e padronização temporal
8. **#14 · INT-02** Referência territorial e georreferenciamento *(precisa de #12)*
9. **#15 · INT-03** Silver — limpeza das tabelas de fato *(precisa de #9, #10, #11, #13, #14)*
10. **#16 · INT-04** Gold — situação por distrito e dia *(precisa de #15)*

### Onda 3 — Primeiro valor visível  *(Fase 2)*
11. **#17 · IND-01** Indicadores meteo-hidrológicos
12. **#18 · IND-02** População exposta em áreas de risco
13. **#19 · IND-03** Motor de classificação de risco *(precisa de #17 e #18)*
14. **#23 · PNL-01** Painel com dados reais (KPIs e tabela de distritos) *(precisa de #16, #17, #19)* → **primeira entrega que o cliente vê**

### Onda 4 — Predição e entrega completa  *(Fase 3)*
15. **#20 · PRD-01** Baseline de previsão de chuva e nível · **#21 · PRD-02** Previsão de arboviroses
16. **#22 · PRD-03** Motor de alertas preditivos *(precisa de #19 e #20)*
17. **#24 · PNL-02** Gráficos de série e feed de alertas *(precisa de #23 e #22)* · **#25 · PNL-03** Boletim automático *(precisa de #16, #19, #22)*

### Fase 4 — Roadmap
Fontes complementares (APAC, INMET, CPRH, MonitorAr, DATASUS) e novos indicadores. Ainda sem issues.

---

## Caminho crítico

O que **não pode atrasar**, porque tudo depois depende:

```text
#5 FND-01 ─► #8 ING-01 ─► #9/#10 ING-02/03 ─┐
                                             ├─► #15 INT-03 ─► #16 INT-04 ─► (IND-*, PRD-*, PNL-*)
            #11 ING-04 ───────────────────────┘
```

`INT-04` (#16) é o gargalo central: **seis** histórias dependem dele (todos os indicadores, previsões e o painel real).
Priorizar a linha `FND-01 → ING-01 → ING-02/03/04 → INT-03 → INT-04`.

---

## Começar agora (Fase 1)

| # | Issue | Uma frase | Pré-req |
|---|---|---|---|
| #5 | FND-01 | Criar `src/`, `conf/`, `data/` (ignorada), `tests/`, `docs/PADROES.md` | — |
| #6 | FND-02 | YAML de contrato por fonte + função `validar(lote, contrato)` | #5 |
| #7 | FND-03 | `runner.py` que roda um coletor, grava RAW e registra a execução | #5 |
| #8 | ING-01 | Cliente CKAN reutilizável (paginação + retry) por `resource_id` | #5, #7 |

**Fase 1 está "pronta" quando:** os quatro conectores (ING-02, 03, 04, 05) gravam RAW + Bronze de forma
idempotente, validados pelos contratos, orquestrados pelo `runner`, com testes passando sem depender de rede.

---

## Como pegar uma issue

1. No [Project AerVita](https://github.com/users/Matheus-Barkokebas/projects/1), mover a issue para **Doing** e se atribuir.
2. Criar a branch: `feature/<id-minusculo>-AAAA.MM.DD` — ex.: `feature/ing-01-2026.09.15`.
3. Seguir o **escopo** e o bloco **Para IA** da issue (detalhe completo em [`HISTORIAS.md`](HISTORIAS.md)). Não fazer trabalho de outra issue.
4. Abrir PR contra `develop` com `Closes #N` na descrição; pedir revisão de outra pessoa do time.
5. Merge → a issue fecha e o épico atualiza o progresso.
