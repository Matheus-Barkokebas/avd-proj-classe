# Pipeline diário numa VM do Google Cloud

Uma máquina virtual Linux pequena (Compute Engine) roda o pipeline todo dia às 6h do Recife,
pelo `cron`. A VM se configura sozinha ao ligar: o startup script baixa e roda
`pipeline/agendamento/instalar_vm.sh`. Falta só uma coisa manual: preencher os segredos.

```text
startup da VM ──► instalar_vm.sh: fuso do Recife, swap, git clone em /opt/aervita, venv, /etc/cron.d/aervita

cron (06:00, America/Recife) ──► pipeline/agendamento/rodar_diario_vm.sh
                                   ├─ git pull (branch main)
                                   ├─ território, arboviroses, INMET ──► Atlas (Bronze) e Neon (Silver)
                                   ├─ Gold ──► Neon (schema gold)
                                   └─ resultado ──► gold.execucao_pipeline e pipeline/data/logs/AAAA-MM-DD.log
```

| Arquivo | Papel |
|---|---|
| `pipeline/agendamento/instalar_vm.sh` | prepara a VM; pode rodar de novo sem estragar nada |
| `pipeline/agendamento/rodar_diario_vm.sh` | o que o `cron` chama todo dia |
| `pipeline/src/rodar_diario.py` | roda as etapas e grava o resultado em `gold.execucao_pipeline` |

**Pré-requisito:** esses arquivos precisam estar na branch `main`, porque a VM baixa o projeto de lá.

O COP Recife fica **fora** por padrão: desde nov/2026 os serviços exigem login. Quando o acesso
for liberado, acrescente `--com-cop` no fim da linha de `/etc/cron.d/aervita`. O COP só responde a
IPs do Brasil, então nesse dia a VM precisa estar em São Paulo.

## 1. Projeto e faturamento

1. Em <https://console.cloud.google.com>, crie um projeto (por exemplo `aervita-pipeline`).
2. Em **Faturamento**, vincule uma conta de faturamento. O Google exige cartão.

## 2. Criar a VM

Abra o **Cloud Shell** (ícone `>_` no topo do console) e rode:

```bash
gcloud services enable compute.googleapis.com
gcloud compute instances create aervita-pipeline --zone=us-central1-a --machine-type=e2-micro --image-family=debian-12 --image-project=debian-cloud --boot-disk-size=30GB --boot-disk-type=pd-standard --metadata=startup-script='#!/bin/bash
curl -fsSL https://raw.githubusercontent.com/Matheus-Barkokebas/avd-proj-classe/main/pipeline/agendamento/instalar_vm.sh | bash'
```

| Região | Custo | Quando usar |
|---|---|---|
| `us-central1-a` (EUA), como no comando | dentro do nível gratuito do Google para uma `e2-micro` com disco padrão de até 30 GB | agora, enquanto o COP está fora |
| `southamerica-east1-a` (São Paulo) | pago, alguns dólares por mês | quando o COP liberar o acesso |

Confira as regras do nível gratuito e os preços nas páginas do Google antes de criar.
A VM não abre nenhuma porta para a internet: não precisa de HTTP nem de HTTPS.

A instalação leva de 2 a 5 minutos depois que a VM liga. Para acompanhar:

```bash
gcloud compute instances get-serial-port-output aervita-pipeline --zone=us-central1-a | grep AerVita
```

Quando aparecer `AerVita: VM pronta`, siga para o passo 3.

## 3. Preencher os segredos (manual)

Na lista de VMs, clique em **SSH** ao lado de `aervita-pipeline` e rode:

```bash
sudo nano /opt/aervita/pipeline/.env
```

Deixe o arquivo igual ao seu `pipeline/.env` local, em especial `MONGODB_URI`, `MONGODB_DB` e
`NEON_DATABASE_URL`. Use o usuário do Neon com escrita, não o `aervita_api`. Para salvar, `Ctrl+O` e `Enter`; para sair, `Ctrl+X`.
**Os segredos ficam só nesse arquivo da VM: nunca no chat, no Gemini, no código ou em commit.**

## 4. Liberar a VM no MongoDB Atlas

No Atlas, em **Network Access**, confira se existe a entrada `0.0.0.0/0`. Outra opção é reservar um IP
fixo para a VM (**Rede VPC > Endereços IP > Reservar IP externo estático**) e liberar só esse IP.
O Neon aceita conexões de qualquer IP com a senha.

## 5. Testar uma vez

Ainda no SSH da VM:

```bash
sudo bash /opt/aervita/pipeline/agendamento/rodar_diario_vm.sh
sudo cat /opt/aervita/pipeline/data/logs/$(date +%Y-%m-%d).log
```

O log mostra cada etapa como `=== etapa: código N` e termina com `=== registrado: ok`.
Leva cerca de 4 minutos. Daí em diante, roda sozinho todo dia às 6h.

## 6. Alerta de orçamento

Em **Faturamento > Orçamentos e alertas**, crie um orçamento baixo (por exemplo, R$ 10) com aviso
por e-mail em 50%, 90% e 100%.

## Como acompanhar

| O quê | Onde |
|---|---|
| Resultado de cada execução | tabela `gold.execucao_pipeline` no Neon |
| Log completo do dia | `/opt/aervita/pipeline/data/logs/AAAA-MM-DD.log` na VM (guarda 30 dias) |
| Rodar fora do horário | o primeiro comando do passo 5 |
| Agendamento | `cat /etc/cron.d/aervita` |

O código se atualiza sozinho: cada execução faz `git pull` da branch `main` antes de rodar.

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| `AerVita: VM pronta` não aparece | o startup script não achou o `instalar_vm.sh`: ele precisa estar na `main` |
| `Variável de ambiente ... não definida` | faltou preencher o `.env` (passo 3) |
| território e arboviroses falham com tempo esgotado no Atlas | a VM não está liberada no Atlas (passo 4) |
| `Killed` no log, na etapa de arboviroses | faltou memória; confira o swap com `free -h` |
