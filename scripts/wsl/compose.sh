#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-assistant-hub-ai}"

"$REPO_ROOT/scripts/wsl/init-env.sh" >/dev/null

exec docker compose \
  --project-name "$PROJECT_NAME" \
  --project-directory "$REPO_ROOT" \
  --env-file "$ENV_FILE" \
  -f "$REPO_ROOT/infra/compose/docker-compose.yml" \
  -f "$REPO_ROOT/infra/compose/docker-compose.gpu.yml" \
  "$@"
