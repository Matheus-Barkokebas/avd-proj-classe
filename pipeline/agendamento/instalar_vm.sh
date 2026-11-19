#!/usr/bin/env bash
# Prepara a VM para o pipeline diário (ver docs/deploy-pipeline-vm.md). Roda como root no startup
# script da VM e pode rodar de novo sem estragar nada. Não cria segredos: o pipeline/.env é preenchido à mão.
set -euo pipefail
DESTINO=/opt/aervita
REPO=https://github.com/Matheus-Barkokebas/avd-proj-classe.git

timedatectl set-timezone America/Recife

if ! swapon --show | grep -q /swapfile; then
  [ -f /swapfile ] || { fallocate -l 1G /swapfile; chmod 600 /swapfile; mkswap /swapfile; }
  swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

command -v git >/dev/null && dpkg -s python3-venv >/dev/null 2>&1 || {
  apt-get update -q && apt-get install -y -q git python3-venv
}

[ -d "$DESTINO/.git" ] || git clone --quiet "$REPO" "$DESTINO"
git -C "$DESTINO" pull --ff-only --quiet || true

cd "$DESTINO/pipeline"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install --quiet -r requirements.txt
[ -f .env ] || { cp .env.example .env; chmod 600 .env; }

echo '0 6 * * * root bash /opt/aervita/pipeline/agendamento/rodar_diario_vm.sh' > /etc/cron.d/aervita
chmod 644 /etc/cron.d/aervita

echo "AerVita: VM pronta. Falta preencher $DESTINO/pipeline/.env (sudo nano $DESTINO/pipeline/.env)."
