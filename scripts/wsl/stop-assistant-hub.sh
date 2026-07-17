#!/usr/bin/env bash
set -Eeuo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if command -v powershell.exe >/dev/null 2>&1; then
  STOP_WINDOWS="$(wslpath -w "$REPO_ROOT/scripts/windows/stop-audio-agent.ps1")"
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$STOP_WINDOWS" >/dev/null 2>&1 || true
fi

"$REPO_ROOT/scripts/wsl/compose.sh" down --remove-orphans
echo "Assistant Hub AI encerrado."
