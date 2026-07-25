#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SESSION="session-$(date +%Y%m%d-%H%M%S)"
PROFILE_RELATIVE="samples/audio-profiles/default.yaml"
REINSTALL_AGENT=false
OPEN_BROWSER=true
START_AGENT=true
START_SESSION_CORE=true
SEED_SESSION_CORE=true
SESSION_CORE_PORT="${SERVER_PORT:-8080}"
BUILD_ARGS=()

usage() {
  cat <<'USAGE'
Uso: ./scripts/wsl/start-assistant-hub.sh [opções]

  --session NOME         identificador da sessão
  --profile CAMINHO      perfil relativo à raiz do repositório
  --no-build             não recompila as imagens Docker
  --no-cache             recompila sem cache
  --skip-model-load      não aquece o Whisper
  --reinstall-agent      reinstala o agente Python do Windows
  --no-agent             sobe apenas os containers (e session-core, se habilitado)
  --no-browser           não abre o dashboard
  --no-session-core      não sobe o session-core (container Compose :8080)
  --session-core-port N  porta host do session-core (default: 8080 ou $SERVER_PORT)
  --no-seed-example      não copia samples/ai-providers se config estiver ausente
  -h, --help             mostra esta ajuda

Por padrão sobe STT + session-core (Docker Compose), aquece o Whisper,
abre o agent WASAPI no Windows e o dashboard em :8001.
Debug JVM do session-core: ./scripts/wsl/start-session-core.sh (com --no-session-core no hub).
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) SESSION="${2:?Informe o nome da sessão}"; shift ;;
    --profile) PROFILE_RELATIVE="${2:?Informe o perfil}"; shift ;;
    --no-build|--no-cache|--skip-model-load) BUILD_ARGS+=("$1") ;;
    --reinstall-agent) REINSTALL_AGENT=true ;;
    --no-agent) START_AGENT=false ;;
    --no-browser) OPEN_BROWSER=false ;;
    --no-session-core) START_SESSION_CORE=false ;;
    --session-core-port) SESSION_CORE_PORT="${2:?Informe a porta}"; shift ;;
    --no-seed-example) SEED_SESSION_CORE=false ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opção desconhecida: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

PROFILE_LINUX="$REPO_ROOT/$PROFILE_RELATIVE"
if [[ ! -f "$PROFILE_LINUX" ]]; then
  echo "Perfil não encontrado: $PROFILE_LINUX" >&2
  exit 1
fi

REBUILD_ARGS=("${BUILD_ARGS[@]}")
REBUILD_ARGS+=(--session-core-port "$SESSION_CORE_PORT")
if [[ "$START_SESSION_CORE" != true ]]; then
  REBUILD_ARGS+=(--no-session-core)
fi
if [[ "$SEED_SESSION_CORE" != true ]]; then
  REBUILD_ARGS+=(--no-seed-example)
fi

"$REPO_ROOT/scripts/wsl/rebuild-and-start.sh" "${REBUILD_ARGS[@]}"

ps_quote() {
  local value="$1"
  printf "%s" "${value//\'/\'\'}"
}

if [[ "$START_AGENT" == true ]]; then
  if ! command -v powershell.exe >/dev/null 2>&1; then
    echo "powershell.exe não está acessível pelo WSL. Verifique a interoperabilidade WSL/Windows." >&2
    exit 1
  fi

  RUN_SCRIPT_WINDOWS="$(wslpath -w "$REPO_ROOT/scripts/windows/run-audio-agent-foreground.ps1")"
  PROFILE_WINDOWS="$(wslpath -w "$PROFILE_LINUX")"
  RUN_Q="$(ps_quote "$RUN_SCRIPT_WINDOWS")"
  PROFILE_Q="$(ps_quote "$PROFILE_WINDOWS")"
  SESSION_Q="$(ps_quote "$SESSION")"

  REINSTALL_ARG=""
  if [[ "$REINSTALL_AGENT" == true ]]; then
    REINSTALL_ARG=",'-Reinstall'"
  fi

  echo "==> Abrindo o agente WASAPI em um novo PowerShell do Windows"
  powershell.exe -NoProfile -Command \
    "\$a=@('-NoExit','-ExecutionPolicy','Bypass','-File','$RUN_Q','-Session','$SESSION_Q','-Profile','$PROFILE_Q','-LogLevel','INFO'$REINSTALL_ARG); Start-Process -FilePath 'powershell.exe' -ArgumentList \$a" \
    >/dev/null
fi

if [[ "$OPEN_BROWSER" == true ]]; then
  powershell.exe -NoProfile -Command "Start-Process 'http://localhost:8001'" >/dev/null 2>&1 || true
fi

echo
echo "Assistant Hub AI iniciado a partir do WSL."
echo "Session: $SESSION"
echo "Profile: $PROFILE_RELATIVE"
echo "Dashboard: http://localhost:8001"
if [[ "$START_SESSION_CORE" == true ]]; then
  echo "session-core (Docker): http://127.0.0.1:${SESSION_CORE_PORT}"
  echo "  logs: ./scripts/wsl/compose.sh logs -f session-core"
  echo "  stop: ./scripts/wsl/stop-session-core.sh"
fi
