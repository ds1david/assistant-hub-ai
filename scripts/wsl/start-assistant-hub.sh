#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SESSION="session-$(date +%Y%m%d-%H%M%S)"
PROFILE_RELATIVE="samples/audio-profiles/default.yaml"
REINSTALL_AGENT=false
OPEN_BROWSER=true
START_AGENT=true
BUILD_ARGS=()

usage() {
  cat <<'USAGE'
Uso: ./scripts/wsl/start-assistant-hub.sh [opções]

  --session NOME       identificador da sessão
  --profile CAMINHO    perfil relativo à raiz do repositório
  --no-build           não recompila as imagens Docker
  --no-cache           recompila sem cache
  --skip-model-load    não aquece o Whisper
  --reinstall-agent    reinstala o agente Python do Windows
  --no-agent           sobe apenas os containers
  --no-browser         não abre o dashboard
  -h, --help           mostra esta ajuda
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

"$REPO_ROOT/scripts/wsl/rebuild-and-start.sh" "${BUILD_ARGS[@]}"

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
