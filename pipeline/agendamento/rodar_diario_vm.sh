#!/usr/bin/env bash
# Execução diária na VM (ver docs/deploy-pipeline-vm.md): atualiza o código, roda o pipeline e guarda o log.
# Os segredos ficam em pipeline/.env na própria VM (chmod 600), nunca no Git.
set -u
PIPELINE="$(cd "$(dirname "$0")/.." && pwd)"
LOGS="$PIPELINE/data/logs"
mkdir -p "$LOGS"
LOG="$LOGS/$(date +%Y-%m-%d).log"

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') início"
  git -C "$PIPELINE/.." pull --ff-only --quiet || echo "=== aviso: git pull falhou, rodando o código atual"
  "$PIPELINE/.venv/bin/pip" install --quiet -r "$PIPELINE/requirements.txt"
  cd "$PIPELINE" && ORIGEM_EXECUCAO=agendamento "$PIPELINE/.venv/bin/python" src/rodar_diario.py "$@"
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') fim, código $?"
} >> "$LOG" 2>&1

# Mantém só os últimos 30 dias de log
find "$LOGS" -name '*.log' -mtime +30 -delete
