# Pipeline diário numa VM do Google Cloud

Uma VM Linux pequena (Compute Engine, `e2-micro`, São Paulo) roda o pipeline todo dia às 6h do Recife,
pelo `cron`. A cada execução ela atualiza o código com `git pull` da `main` e roda `python -m aervita diario`.

```text
cron (06:00, America/Recife) ──► pipeline/agendamento/rodar_diario_vm.sh
                                   ├─ git pull (branch main)
                                   ├─ território, arboviroses, INMET ──► Atlas (Bronze) e Neon (Silver)
                                   ├─ Gold ──► Neon (schema gold)
                                   └─ resultado ──► gold.execucao_pipeline e pipeline/data/logs/AAAA-MM-DD.log
```

| Arquivo | Papel |
|---|---|
| `pipeline/agendamento/instalar_vm.sh` | prepara a VM: fuso, swap, `git clone` em `/opt/aervita`, venv e `/etc/cron.d/aervita`; pode rodar de novo |
| `pipeline/agendamento/rodar_diario_vm.sh` | o que o `cron` chama todo dia |
| `pipeline/aervita/diario.py` | roda as etapas e grava o resultado em `gold.execucao_pipeline` |

O COP Recife fica **fora** por padrão: desde nov/2026 os serviços exigem login. Quando o acesso for
liberado, acrescente `--com-cop` no fim da linha de `/etc/cron.d/aervita`.

## 1. Projeto e VM

1. Em <https://console.cloud.google.com>, crie um projeto e vincule uma conta de faturamento.
2. Crie a VM: `e2-micro`, Debian, zona `southamerica-east1-c`, disco padrão, sem HTTP/HTTPS.

## 2. Saída para a internet sem IP externo

O projeto tem a política `constraints/compute.vmExternalIpAccess`, que proíbe IP externo em VM.
A saída passa por um Cloud NAT, no **Cloud Shell**:

```bash
gcloud compute routers create aervita-router --network=default --region=southamerica-east1
gcloud compute routers nats create aervita-nat --router=aervita-router --region=southamerica-east1 --auto-allocate-nat-external-ips --nat-all-subnet-ip-ranges
gcloud compute routers get-status aervita-router --region=southamerica-east1 --format="value(result.natStatus[0].autoAllocatedNatIps)"
```

O último comando mostra o IP de saída. Libere esse IP no MongoDB Atlas, em **Network Access**
(`IP/32`). O Neon aceita qualquer IP com a senha.

## 3. Instalar

No **SSH** da VM (botão no console):

```bash
curl -fsSL https://raw.githubusercontent.com/Matheus-Barkokebas/avd-proj-classe/main/pipeline/agendamento/instalar_vm.sh | sudo bash
```

Termina com `AerVita: VM pronta`.

## 4. Segredos

Envie uma cópia do seu `pipeline/.env` pelo botão **Fazer upload do arquivo** do SSH (com outro nome, por
exemplo `aervita.env`) e mova para o lugar certo:

```bash
sudo mv ~/aervita.env /opt/aervita/pipeline/.env && sudo chown root:root /opt/aervita/pipeline/.env && sudo chmod 600 /opt/aervita/pipeline/.env
```

**Os segredos ficam só nesse arquivo da VM: nunca no chat, no código ou em commit.** Apague a cópia local depois.

## 5. Testar

```bash
sudo bash /opt/aervita/pipeline/agendamento/rodar_diario_vm.sh
sudo tail -3 /opt/aervita/pipeline/data/logs/$(date +%Y-%m-%d).log
```

O log termina com `=== registrado: ok`. Daí em diante, roda sozinho todo dia às 6h.

## Como acompanhar

| O quê | Onde |
|---|---|
| Resultado de cada execução | tabela `gold.execucao_pipeline` no Neon |
| Log completo do dia | `/opt/aervita/pipeline/data/logs/AAAA-MM-DD.log` na VM (guarda 30 dias) |
| Rodar fora do horário | o primeiro comando do passo 5 |
| Agendamento | `cat /etc/cron.d/aervita` |

Custos: VM em São Paulo, Cloud NAT e o IP do NAT são pagos. Crie um alerta em **Faturamento > Orçamentos e alertas**.

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| `curl` com tempo esgotado na VM | sem saída para a internet: falta o Cloud NAT (passo 2) |
| `Variável de ambiente ... não definida` | faltou o `.env` (passo 4) |
| território e arboviroses falham com tempo esgotado no Atlas | o IP do NAT não está liberado no Atlas (passo 2) |
| `Killed` no log | faltou memória; confira o swap com `free -h` |
