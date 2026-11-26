#!/usr/bin/env bash
# Execução diária na VM (ver docs/deploy-pipeline-vm.md): atualiza o código, roda o pipeline e guarda o log.
# Os segredos ficam em pipeline/.env na própria VM (chmod 600), nunca no Git.
set -u

main() {
  local pipeline logs log
  pipeline="$(cd "$(dirname "$0")/.." && pwd)"
  logs="$pipeline/data/logs"
  mkdir -p "$logs"
  log="$logs/$(date +%Y-%m-%d).log"
  {
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') início"
    git -C "$pipeline/.." pull --ff-only --quiet || echo "=== aviso: git pull falhou, rodando o código atual"
    "$pipeline/.venv/bin/pip" install --quiet -r "$pipeline/requirements.txt"
    cd "$pipeline" && ORIGEM_EXECUCAO=agendamento "$pipeline/.venv/bin/python" -m aervita diario "$@"
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') fim, código $?"
  } >> "$log" 2>&1
  find "$logs" -name '*.log' -mtime +30 -delete
}

# A função inteira é lida antes de rodar: o git pull acima pode trocar este arquivo sem afetar a execução atual.
main "$@"
exit
