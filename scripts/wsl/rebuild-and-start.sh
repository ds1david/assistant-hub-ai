#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE="$REPO_ROOT/scripts/wsl/compose.sh"
REBUILD=true
NO_CACHE=false
LOAD_MODEL=true

usage() {
  cat <<'USAGE'
Uso: rebuild-and-start.sh [opções]

  --no-build          não recompila as imagens
  --no-cache          recompila sem usar cache
  --skip-model-load   não aquece o modelo Whisper
  -h, --help          mostra esta ajuda
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build) REBUILD=false ;;
    --no-cache) NO_CACHE=true ;;
    --skip-model-load) LOAD_MODEL=false ;;
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

# compose.sh cria .env quando necessário e sempre o fornece explicitamente ao Compose.
"$COMPOSE" config --quiet

echo "==> Configuração efetiva"
"$COMPOSE" config | sed -n '/environment:/,/restart:/p' | sed -n '1,80p'

echo "==> Encerrando containers anteriores"
"$COMPOSE" down --remove-orphans

# Remove um container legado criado por versões que usavam outro project name.
if docker container inspect assistant-hub-transcription >/dev/null 2>&1; then
  echo "==> Removendo container legado assistant-hub-transcription"
  docker rm -f assistant-hub-transcription >/dev/null
fi

if [[ "$REBUILD" == true ]]; then
  echo "==> Recompilando imagens Docker"
  BUILD_ARGS=(build --pull)
  if [[ "$NO_CACHE" == true ]]; then
    BUILD_ARGS+=(--no-cache)
  fi
  "$COMPOSE" "${BUILD_ARGS[@]}"
fi

echo "==> Iniciando stack com GPU"
"$COMPOSE" up -d --force-recreate

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

echo "==> Container atual: ${CONTAINER_ID:0:12}"
echo "==> Aguardando health check em http://localhost:8001/health"
for attempt in $(seq 1 90); do
  if curl --fail --silent --show-error http://localhost:8001/health >/tmp/assistant-hub-health.json 2>/dev/null; then
    cat /tmp/assistant-hub-health.json
    echo
    break
  fi
  if [[ "$attempt" -eq 90 ]]; then
    echo "Serviço não ficou saudável dentro do prazo." >&2
    "$COMPOSE" logs --tail=200 transcription >&2
    exit 1
  fi
  sleep 2
done

if [[ "$LOAD_MODEL" == true ]]; then
  echo "==> Carregando modelo Whisper"
  curl --fail --silent --show-error --max-time 900 \
    -X POST http://localhost:8001/v1/model/load
  echo
fi

echo "==> Containers ativos"
"$COMPOSE" ps

echo "Dashboard: http://localhost:8001"
