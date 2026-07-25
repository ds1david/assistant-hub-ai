#!/usr/bin/env bash
# Encerra o session-core iniciado por start-session-core.sh --background (ou o Java
# na porta padrão se for claramente o Assistant Hub).
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT="${SERVER_PORT:-8080}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/assistant-hub-ai"
PID_FILE="$STATE_DIR/session-core.pid"

usage() {
  cat <<'USAGE'
Uso: ./scripts/wsl/stop-session-core.sh [--port N]

  Encerra o launcher gravado em $XDG_STATE_HOME/assistant-hub-ai/session-core.pid
  e, se ainda houver listener na porta que responde /api/ai-providers, tenta
  encerrar o processo Java correspondente.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="${2:?Informe a porta}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opção desconhecida: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

stop_pid() {
  local pid="$1"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "Encerrando pid $pid..."
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.25
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi
}

if [[ -f "$PID_FILE" ]]; then
  stop_pid "$(cat "$PID_FILE" 2>/dev/null || true)"
  rm -f "$PID_FILE"
fi

# Mata o Java do monorepo na porta, se ainda estiver ouvindo e for o nosso hub.
if command -v ss >/dev/null 2>&1; then
  line="$(ss -H -tlnp "( sport = :${PORT} )" 2>/dev/null | head -n1 || true)"
  if [[ "$line" =~ pid=([0-9]+) ]]; then
    pid="${BASH_REMATCH[1]}"
    cmd="$(tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null || true)"
    if [[ "$cmd" == *assistanthub* || "$cmd" == *session-core* || "$cmd" == *"$REPO_ROOT"* ]]; then
      # Pode ser o processo-filho Maven/Spring; encerra a árvore a partir do pid do listener.
      stop_pid "$pid"
    else
      echo "Porta ${PORT} ainda em uso por outro processo (não interrompido):" >&2
      echo "  pid=$pid" >&2
      echo "  cmd=$cmd" >&2
      exit 1
    fi
  fi
fi

echo "session-core parado (porta ${PORT})."
