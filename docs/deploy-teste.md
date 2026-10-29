# Deploy de teste (gratuito)

Ambiente de **teste/demonstração**, não de produção. Três peças, todas em planos gratuitos:

```text
GitHub Actions (coleta do COP, de hora em hora) ──► Atlas (RAW) + Neon (padronizada)
                                                                    │
                                     Render (API FastAPI) ◄─────────┘
                                            │
                                     Vercel (painel React) ◄── navegador
```

| Peça | Serviço | Segredo que usa |
|---|---|---|
| Coleta do COP | GitHub Actions ([`coleta-cop.yml`](../.github/workflows/coleta-cop.yml)) | `MONGODB_URI` e `NEON_DATABASE_URL` **de dono** (escreve no banco) |
| API | Render | `NEON_DATABASE_URL` **só leitura** (`aervita_api`) |
| Painel | Vercel | nenhum — só o endereço público da API |

Siga na ordem: a API precisa existir antes do painel, e o painel antes de liberar o CORS.

> Segredos só nos painéis do GitHub, do Render e da Vercel. Nunca em arquivo do repositório nem em chat.

---

## 1. Coleta do COP no GitHub Actions

### 1.1 Liberar o Atlas para o GitHub

As máquinas do GitHub Actions mudam de IP a cada execução. No Atlas:
**Security → Network Access → Add IP Address → Allow access from anywhere** (`0.0.0.0/0`).

A proteção passa a ser só o usuário e a senha da URI — aceitável para teste. Se o projeto virar algo sério,
troque por um IP fixo (ex.: um servidor próprio rodando a coleta).

O Neon já aceita qualquer IP por padrão; não precisa mexer.

### 1.2 Cadastrar os segredos

No GitHub: **repositório → Settings → Secrets and variables → Actions → New repository secret**.

| Nome | Valor |
|---|---|
| `MONGODB_URI` | a mesma de `pipeline/.env` |
| `NEON_DATABASE_URL` | a mesma de `pipeline/.env` (usuário **dono**, não o `aervita_api`) |

### 1.3 Testar na mão

O GitHub só mostra o botão **Run workflow** (e só dispara o agendamento) quando o `coleta-cop.yml` está na
**branch padrão (`main`)**. Depois do merge:

1. aba **Actions** → **coleta-cop** → **Run workflow**;
2. escolha a frequência **todas** na primeira vez (carrega tudo do COP);
3. abra a execução e confira o passo **Coletar**: o JSON no fim deve ter `"status": "ok"` em cada camada.

Se falhar com erro de conexão no Mongo, revise o passo 1.1; com `Variável de ambiente ... não definida`, o 1.2.

### 1.4 Agendamento

| Quando (Recife) | O que coleta |
|---|---|
| toda hora, aos 10 min | indicadores (chuva, maré, estágio) e rios |
| todo dia às 06:20 | previsão de chuva e chuva mensal |
| só pelo botão (frequência `mensal` ou `todas`) | pluviômetros, áreas alagáveis e pontos de alagamento |

Detalhes do GitHub que valem saber:

- **botão manual e agendamento só funcionam com o workflow na branch padrão (`main`)**;
- os horários podem atrasar alguns minutos (às vezes mais) em horário de pico do GitHub;
- em repositório público, o agendamento é desligado depois de 60 dias sem commits (reative na aba Actions);
- custo: grátis em repositório público; em privado, ~720 dos 2.000 minutos/mês gratuitos.

Arboviroses e território quase não mudam: continue rodando na sua máquina quando precisar
(`epidemiologia.py` e `territorio.py`, ver [`pipeline/README.md`](../pipeline/README.md)).

---

## 2. API no Render

1. [render.com](https://render.com) → entrar com o GitHub → **New → Web Service** → escolher o repositório.
2. Configuração:

   | Campo | Valor |
   |---|---|
   | Branch | `main` (ou a branch que quiser testar) |
   | Region | **Ohio (US East)** — mesma região do Neon (`us-east-2`) |
   | Root Directory | `api` |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | Free |

3. **Environment Variables**:

   | Nome | Valor |
   |---|---|
   | `NEON_DATABASE_URL` | a de `api/.env` (usuário `aervita_api`, só leitura) |
   | `PYTHON_VERSION` | `3.12.8` (a mesma do CI) |
   | `API_ORIGENS_CORS` | deixe para o passo 4 |

4. **Create Web Service** e espere o deploy. Teste em `https://<sua-api>.onrender.com/saude` — deve responder
   `{"status":"ok","banco":"ok"}`. As rotas ficam em `/docs`.

O plano gratuito **hiberna depois de ~15 min sem acesso**: a primeira chamada depois disso leva até ~1 min.
Antes de apresentar, abra o painel uns minutos antes.

---

## 3. Painel na Vercel

1. [vercel.com](https://vercel.com) → entrar com o GitHub → **Add New → Project** → escolher o repositório.
2. **Root Directory**: `frontend`. A Vercel reconhece o Vite sozinha (build `npm run build`, saída `dist`).
3. **Environment Variables**: `VITE_API_URL` = `https://<sua-api>.onrender.com` (sem `/` no fim).
4. **Deploy**. Anote o endereço gerado, ex.: `https://aervita.vercel.app`.

O [`frontend/vercel.json`](../frontend/vercel.json) faz qualquer URL abrir o painel — sem ele, abrir
`/mapa` direto dá 404.

`VITE_API_URL` entra no build: se mudar o endereço da API, faça **Redeploy** na Vercel.

---

## 4. Liberar o painel no CORS da API

No Render → serviço da API → **Environment** → `API_ORIGENS_CORS` = o endereço da Vercel
(ex.: `https://aervita.vercel.app`, sem `/` no fim). Para mais de um, separe por vírgula.
Salve: o Render reinicia a API sozinho.

Sem isso, o painel abre mas todos os cards mostram "Não foi possível falar com a API" (o navegador bloqueia).

---

## 5. Conferir

- [ ] `https://<sua-api>.onrender.com/saude` responde `ok`;
- [ ] o painel abre e o selo do topo mostra **Dados conectados**;
- [ ] `/mapa` aberto direto (colando a URL) carrega o mapa;
- [ ] depois de uma coleta agendada, a Visão geral mostra a hora da última leitura sem o aviso amarelo.

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| Cards com "Não foi possível falar com a API" | API hibernando (espere 1 min e clique em "Tentar de novo"), `VITE_API_URL` errado ou CORS do passo 4 |
| Aviso amarelo de dado antigo | coleta agendada parada: veja a aba Actions (falha ou agendamento desligado) |
| Coleta falha conectando no Mongo | IP do GitHub bloqueado no Atlas (passo 1.1) |
| `/saude` responde `503` com `banco: indisponivel` | `NEON_DATABASE_URL` errada no Render |
