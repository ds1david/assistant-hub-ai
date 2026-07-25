#!/usr/bin/env bash
set -Eeuo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ -d "$REPO_ROOT/services/transcription-service" ]]
[[ -d "$REPO_ROOT/services/session-core" ]]
[[ -f "$REPO_ROOT/services/session-core/Dockerfile" ]]
[[ -d "$REPO_ROOT/config" ]]
grep -q 'context: services/transcription-service' "$REPO_ROOT/infra/compose/docker-compose.yml"
grep -q -- '- ./config:/config:ro' "$REPO_ROOT/infra/compose/docker-compose.yml"
grep -q 'dockerfile: services/session-core/Dockerfile' "$REPO_ROOT/infra/compose/docker-compose.yml"
grep -q 'container_name: assistant-hub-session-core' "$REPO_ROOT/infra/compose/docker-compose.yml"
grep -q 'ws://transcription:8001/ws/transcripts' "$REPO_ROOT/infra/compose/docker-compose.yml"
grep -q -- './data/session-core:/data/session-core' "$REPO_ROOT/infra/compose/docker-compose.yml"
! grep -R -q 'context: ../../services/transcription-service' "$REPO_ROOT/infra/compose"
echo "Compose paths OK"
