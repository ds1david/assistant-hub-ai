#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE="$REPO_ROOT/scripts/wsl/compose.sh"
REBUILD=true
NO_CACHE=false
LOAD_MODEL=true
START_SESSION_CORE=true
SESSION_CORE_PORT="${SESSION_CORE_PORT:-${SERVER_PORT:-8080}}"
SEED_SESSION_CORE=true

usage() {
  cat <<'USAGE'
Uso: rebuild-and-start.sh [opções]

  --no-build             não recompila as imagens
  --no-cache             recompila sem usar cache
  --skip-model-load      não aquece o modelo Whisper
  --no-session-core      sobe só transcription (não sobe session-core)
  --session-core-port N  porta host do session-core (default: 8080)
  --no-seed-example      não copia samples/ai-providers se config estiver ausente
  -h, --help             mostra esta ajuda
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build) REBUILD=false ;;
    --no-cache) NO_CACHE=true ;;
    --skip-model-load) LOAD_MODEL=false ;;
    --no-session-core) START_SESSION_CORE=false ;;
    --session-core-port) SESSION_CORE_PORT="${2:?Informe a porta}"; shift ;;
    --no-seed-example) SEED_SESSION_CORE=false ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opção desconhecida: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

cd "$REPO_ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker não está disponível no WSL. Habilite a integração da distribuição no Docker Desktop." >&2
  exit 1
fi

export SESSION_CORE_PORT

# compose.sh cria .env quando necessário e sempre o fornece explicitamente ao Compose.
"$COMPOSE" config --quiet

seed_ai_providers() {
  local providers_path="${SESSION_CORE_AI_PROVIDER_HUB_PATH:-config/ai-providers.yaml}"
  # Paths absolutos no container (/config/...) mapeiam para ./config no host.
  if [[ "$providers_path" == /config/* ]]; then
    providers_path="config/${providers_path#/config/}"
  fi
  if [[ -f "$providers_path" ]]; then
    return 0
  fi
  if [[ "$SEED_SESSION_CORE" != true ]]; then
    echo "Nota: $providers_path ausente — session-core sobe sem provedores."
    return 0
  fi
  mkdir -p "$(dirname "$providers_path")"
  cp "$REPO_ROOT/samples/ai-providers/providers.example.yaml" "$providers_path"
  chmod 600 "$providers_path" 2>/dev/null || true
  echo "Criado $providers_path a partir de samples/ai-providers/providers.example.yaml"
}

if [[ "$START_SESSION_CORE" == true ]]; then
  seed_ai_providers
  mkdir -p "$REPO_ROOT/data/session-core"
fi

echo "==> Configuração efetiva"
"$COMPOSE" config | sed -n '/^  transcription:/,/^  [a-z]/p; /^  session-core:/,/^volumes:/p' | sed -n '1,120p'

echo "==> Encerrando containers anteriores"
"$COMPOSE" down --remove-orphans

# Remove containers legados criados por versões com outro project name.
for legacy in assistant-hub-transcription assistant-hub-session-core; do
  if docker container inspect "$legacy" >/dev/null 2>&1; then
    echo "==> Removendo container legado $legacy"
    docker rm -f "$legacy" >/dev/null
  fi
done

# Libera a porta do session-core se um JVM local (start-session-core.sh) ainda estiver no ar.
if [[ "$START_SESSION_CORE" == true ]] && [[ -x "$REPO_ROOT/scripts/wsl/stop-session-core.sh" ]]; then
  SERVER_PORT="$SESSION_CORE_PORT" "$REPO_ROOT/scripts/wsl/stop-session-core.sh" --port "$SESSION_CORE_PORT" >/dev/null 2>&1 || true
fi

if [[ "$REBUILD" == true ]]; then
  echo "==> Recompilando imagens Docker"
  BUILD_ARGS=(build --pull)
  if [[ "$NO_CACHE" == true ]]; then
    BUILD_ARGS+=(--no-cache)
  fi
  if [[ "$START_SESSION_CORE" == true ]]; then
    "$COMPOSE" "${BUILD_ARGS[@]}"
  else
    "$COMPOSE" "${BUILD_ARGS[@]}" transcription
  fi
fi

UP_SERVICES=(transcription)
if [[ "$START_SESSION_CORE" == true ]]; then
  UP_SERVICES+=(session-core)
fi

echo "==> Iniciando stack (${UP_SERVICES[*]})"
"$COMPOSE" up -d --force-recreate "${UP_SERVICES[@]}"

# Se session-core ficou de uma subida anterior e pedimos só STT, garante que pare.
if [[ "$START_SESSION_CORE" != true ]]; then
  "$COMPOSE" stop session-core >/dev/null 2>&1 || true
fi

wait_http_health() {
  local name="$1"
  local url="$2"
  local attempts="${3:-90}"
  local body
  echo "==> Aguardando health de $name em $url"
  for attempt in $(seq 1 "$attempts"); do
    if body="$(curl --fail --silent --show-error --max-time 3 "$url" 2>/dev/null)"; then
      echo "$body"
      echo
      return 0
    fi
    if [[ "$attempt" -eq "$attempts" ]]; then
      echo "Serviço $name não ficou saudável dentro do prazo." >&2
      "$COMPOSE" logs --tail=200 "$name" >&2 || true
      return 1
    fi
    sleep 2
  done
}

CONTAINER_ID="$("$COMPOSE" ps -q transcription)"
if [[ -z "$CONTAINER_ID" ]]; then
  echo "O Compose não criou o container do serviço transcription." >&2
  "$COMPOSE" logs --tail=200 transcription >&2 || true
  exit 1
fi

if [[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER_ID")" != "true" ]]; then
  echo "O container transcription foi criado, mas não está executando." >&2
  "$COMPOSE" logs --tail=200 transcription >&2 || true
  exit 1
fi

echo "==> Container transcription: ${CONTAINER_ID:0:12}"
wait_http_health transcription "http://localhost:8001/health" 90

if [[ "$START_SESSION_CORE" == true ]]; then
  CORE_ID="$("$COMPOSE" ps -q session-core)"
  if [[ -z "$CORE_ID" ]]; then
    echo "O Compose não criou o container do serviço session-core." >&2
    "$COMPOSE" logs --tail=200 session-core >&2 || true
    exit 1
  fi
  if [[ "$(docker inspect -f '{{.State.Running}}' "$CORE_ID")" != "true" ]]; then
    echo "O container session-core foi criado, mas não está executando." >&2
    "$COMPOSE" logs --tail=200 session-core >&2 || true
    exit 1
  fi
  echo "==> Container session-core: ${CORE_ID:0:12}"
  wait_http_health session-core "http://127.0.0.1:${SESSION_CORE_PORT}/actuator/health" 90
  if ! curl -fsS --max-time 3 "http://127.0.0.1:${SESSION_CORE_PORT}/api/ai-providers" >/dev/null; then
    echo "session-core respondeu health, mas GET /api/ai-providers falhou." >&2
    "$COMPOSE" logs --tail=200 session-core >&2 || true
    exit 1
  fi
  echo "session-core UP em http://127.0.0.1:${SESSION_CORE_PORT}"
fi

if [[ "$LOAD_MODEL" == true ]]; then
  echo "==> Carregando modelo Whisper"
  curl --fail --silent --show-error --max-time 900 \
    -X POST http://localhost:8001/v1/model/load
  echo
fi

echo "==> Containers ativos"
"$COMPOSE" ps

echo "Dashboard: http://localhost:8001"
if [[ "$START_SESSION_CORE" == true ]]; then
  echo "session-core: http://127.0.0.1:${SESSION_CORE_PORT}"
fi
