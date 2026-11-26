# Deploy de teste (gratuito)

Ambiente de **teste/demonstração**, não de produção. Três peças:

```text
VM no Google Cloud (pipeline, todo dia às 6h) ──► Atlas (RAW) + Neon (Silver e Gold)
                                                                    │
                                     Render (API FastAPI) ◄─────────┘
                                            │
                                     Vercel (painel React) ◄── navegador
```

| Peça | Serviço | Segredo que usa |
|---|---|---|
| Pipeline | VM do Google Cloud ([`deploy-pipeline-vm.md`](deploy-pipeline-vm.md)) | `MONGODB_URI` e `NEON_DATABASE_URL` **de dono** (escreve no banco), no `.env` da VM |
| API | Render | `NEON_DATABASE_URL` **só leitura** (`aervita_api`) |
| Painel | Vercel | nenhum — só o endereço público da API |

Siga na ordem: a API precisa existir antes do painel, e o painel antes de liberar o CORS.

> Segredos só no `.env` da VM e nos painéis do Render e da Vercel. Nunca em arquivo do repositório nem em chat.

---

## 1. Pipeline na VM

Passo a passo em [`deploy-pipeline-vm.md`](deploy-pipeline-vm.md). A coleta do COP saiu do GitHub Actions:
o servidor do COP não responde a IPs de fora do Brasil e, desde nov/2026, exige login.

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
| Aviso amarelo de dado antigo | pipeline parado: veja `gold.execucao_pipeline` ou o log do dia na VM |
| Coleta falha conectando no Mongo | IP do GitHub bloqueado no Atlas (passo 1.1) |
| `/saude` responde `503` com `banco: indisponivel` | `NEON_DATABASE_URL` errada no Render |
