#!/usr/bin/env bash
set -Eeuo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ -d "$REPO_ROOT/services/transcription-service" ]]
[[ -d "$REPO_ROOT/config" ]]
grep -q 'context: services/transcription-service' "$REPO_ROOT/infra/compose/docker-compose.yml"
grep -q -- '- ./config:/config:ro' "$REPO_ROOT/infra/compose/docker-compose.yml"
! grep -R -q 'context: ../../services/transcription-service' "$REPO_ROOT/infra/compose"
echo "Compose paths OK"
