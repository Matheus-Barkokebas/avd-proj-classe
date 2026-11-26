# `agendamento/` — execução diária numa VM

| Script | Papel |
|---|---|
| `instalar_vm.sh` | prepara a VM: fuso, swap, `git clone` em `/opt/aervita`, venv e o `cron` das 6h |
| `rodar_diario_vm.sh` | o que o `cron` chama: `git pull`, `python -m aervita diario` e o log do dia (guarda 30 dias) |

O resultado de cada execução fica em `gold.execucao_pipeline`. Passo a passo em
[`docs/deploy-pipeline-vm.md`](../../docs/deploy-pipeline-vm.md).
