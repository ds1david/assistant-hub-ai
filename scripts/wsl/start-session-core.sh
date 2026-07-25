#!/usr/bin/env bash
# Sobe o session-core (Memory Hub + AI Provider Hub) a partir da raiz do monorepo.
# Falha cedo se a porta já estiver ocupada por outro processo (ex.: outro Spring Boot).
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT="${SERVER_PORT:-8080}"
SEED_EXAMPLE=false
SKIP_PORT_CHECK=false
BACKGROUND=false
WAIT_SECONDS=90

usage() {
  cat <<'USAGE'
Uso: ./scripts/wsl/start-session-core.sh [opções]

  --port N             porta HTTP (default: 8080 ou $SERVER_PORT)
  --seed-example       se config/ai-providers.yaml não existir, copia o sample
  --background         sobe em background e aguarda /actuator/health = UP
  --skip-port-check    não aborta se a porta estiver ocupada (não recomendado)
  --wait-seconds N     timeout do health check em --background (default: 90)
  -h, --help           mostra esta ajuda

CWD de execução: sempre a raiz do monorepo (data/session-core e config/ relativos).

Exemplos:
  ./scripts/wsl/start-session-core.sh
  ./scripts/wsl/start-session-core.sh --seed-example --background
  SERVER_PORT=8081 ./scripts/wsl/start-session-core.sh --port 8081
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="${2:?Informe a porta}"; shift ;;
    --seed-example) SEED_EXAMPLE=true ;;
    --background) BACKGROUND=true ;;
    --skip-port-check) SKIP_PORT_CHECK=true ;;
    --wait-seconds) WAIT_SECONDS="${2:?Informe segundos}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opção desconhecida: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if ! [[ "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "Porta inválida: $PORT" >&2
  exit 2
fi

cd "$REPO_ROOT"

listener_line() {
  # Uma linha com o listener TCP na porta (quando ss suporta sport=).
  if command -v ss >/dev/null 2>&1; then
    ss -H -tlnp "( sport = :${PORT} )" 2>/dev/null | head -n1 || true
  fi
}

port_is_listening() {
  local line
  line="$(listener_line)"
  [[ -n "${line// }" ]]
}

describe_listener() {
  local line pid cmd
  line="$(listener_line)"
  if [[ -z "${line// }" ]]; then
    echo "(nenhum listener detectado via ss)"
    return
  fi
  echo "$line"
  # Extrai pid=N de users:(("bin",pid=123,fd=...))
  if [[ "$line" =~ pid=([0-9]+) ]]; then
    pid="${BASH_REMATCH[1]}"
    if [[ -r "/proc/$pid/cmdline" ]]; then
      cmd="$(tr '\0' ' ' <"/proc/$pid/cmdline" | sed 's/[[:space:]]*$//')"
      # Classpath completo polui o erro; destaque o main se existir.
      main_hint="$(printf '%s\n' "$cmd" | grep -oE '[a-zA-Z0-9_.]+Application' | tail -n1 || true)"
      echo "  pid=$pid"
      if [[ -n "$main_hint" ]]; then
        echo "  main=$main_hint"
      fi
      echo "  cmd=$(printf '%.200s' "$cmd")..."
    else
      echo "  pid=$pid (cmdline indisponível)"
    fi
  fi
}

is_assistant_hub_session_core() {
  # Health UP + endpoint do AI Provider Hub responde (não basta só Tomcat na porta).
  local health providers
  health="$(curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/actuator/health" 2>/dev/null || true)"
  providers="$(curl -fsS --max-time 2 -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/api/ai-providers" 2>/dev/null || true)"
  [[ "$health" == *'"status":"UP"'* || "$health" == *'"status" : "UP"'* ]] && [[ "$providers" == "200" ]]
}

if port_is_listening; then
  if is_assistant_hub_session_core; then
    echo "session-core já está no ar em http://127.0.0.1:${PORT}"
    echo "  health: OK"
    echo "  GET /api/ai-providers: 200"
    exit 0
  fi
  if [[ "$SKIP_PORT_CHECK" == true ]]; then
    echo "AVISO: porta ${PORT} ocupada e não parece ser o session-core; seguindo por --skip-port-check" >&2
    describe_listener >&2
  else
    echo "ERRO: porta ${PORT} já está em uso por outro processo (não é o session-core do Assistant Hub)." >&2
    echo >&2
    echo "Listener atual:" >&2
    describe_listener >&2
    echo >&2
    echo "O shell desktop grava provedores em http://localhost:8080/api/ai-providers." >&2
    echo "Se outro app (ex.: number-generator) estiver na 8080, o save devolve 500 genérico." >&2
    echo >&2
    echo "Opções:" >&2
    echo "  1) Pare o processo acima e rode este script de novo" >&2
    echo "  2) Use outra porta:  ./scripts/wsl/start-session-core.sh --port 8081" >&2
    echo "     e aponte o shell: sessionCoreBaseUrl=http://localhost:8081" >&2
    echo "  3) Confira: curl -sS http://127.0.0.1:${PORT}/actuator/health" >&2
    exit 1
  fi
fi

PROVIDERS_PATH="${SESSION_CORE_AI_PROVIDER_HUB_PATH:-config/ai-providers.yaml}"
if [[ ! -f "$PROVIDERS_PATH" ]]; then
  if [[ "$SEED_EXAMPLE" == true ]]; then
    mkdir -p "$(dirname "$PROVIDERS_PATH")"
    cp "$REPO_ROOT/samples/ai-providers/providers.example.yaml" "$PROVIDERS_PATH"
    chmod 600 "$PROVIDERS_PATH" 2>/dev/null || true
    echo "Criado $PROVIDERS_PATH a partir de samples/ai-providers/providers.example.yaml"
  else
    echo "Nota: $PROVIDERS_PATH ausente — o hub inicia sem provedores (salve pelo shell ou use --seed-example)."
  fi
fi

if ! command -v mvn >/dev/null 2>&1; then
  echo "mvn não encontrado no PATH. Ative o SDKMAN (sdk use java / mvn) no WSL." >&2
  exit 1
fi

export SERVER_PORT="$PORT"

echo "==> session-core"
echo "  repo: $REPO_ROOT"
echo "  port: $PORT"
echo "  providers: $PROVIDERS_PATH"
echo "  memory: data/session-core/ (relativo à raiz)"
echo

run_mvn() {
  # -Dspring-boot.run.arguments não é necessário: SERVER_PORT já exportado.
  mvn -pl services/session-core -am spring-boot:run -DskipTests
}

if [[ "$BACKGROUND" != true ]]; then
  echo "Foreground — Ctrl+C encerra o session-core."
  echo
  run_mvn
  exit $?
fi

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/assistant-hub-ai"
mkdir -p "$STATE_DIR"
LOG_FILE="$STATE_DIR/session-core.log"
PID_FILE="$STATE_DIR/session-core.pid"

echo "Background — log: $LOG_FILE"
nohup bash -c "cd \"$REPO_ROOT\" && export SERVER_PORT=\"$PORT\" && mvn -pl services/session-core -am spring-boot:run -DskipTests" \
  >"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
echo "  launcher pid: $(cat "$PID_FILE")"

deadline=$((SECONDS + WAIT_SECONDS))
while (( SECONDS < deadline )); do
  if is_assistant_hub_session_core; then
    echo "session-core UP em http://127.0.0.1:${PORT}"
    echo "  curl -sS http://127.0.0.1:${PORT}/actuator/health"
    echo "  curl -sS http://127.0.0.1:${PORT}/api/ai-providers"
    exit 0
  fi
  # Se a porta abriu mas a API não é a nossa, aborta.
  if port_is_listening && ! is_assistant_hub_session_core; then
    # ainda pode estar subindo — só falha perto do fim se health continuar estranho
    :
  fi
  sleep 2
done

echo "Timeout (${WAIT_SECONDS}s) aguardando health do session-core." >&2
echo "Últimas linhas do log:" >&2
tail -n 40 "$LOG_FILE" >&2 || true
exit 1
