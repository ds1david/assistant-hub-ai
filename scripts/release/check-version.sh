#!/usr/bin/env bash
# Verifica se os pontos de versão do monorepo batem com VERSION na raiz.
# Uso: ./scripts/release/check-version.sh
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

VERSION_FILE="${ROOT}/VERSION"
[[ -f "${VERSION_FILE}" ]] || { echo "ERRO: VERSION não encontrado na raiz"; exit 1; }

EXPECTED="$(tr -d '[:space:]' < "${VERSION_FILE}")"
[[ -n "${EXPECTED}" ]] || { echo "ERRO: VERSION vazio"; exit 1; }

errors=0
check() {
  local label="$1"
  local actual="$2"
  if [[ "${actual}" != "${EXPECTED}" ]]; then
    echo "FAIL  ${label}: encontrado='${actual}' esperado='${EXPECTED}'"
    errors=$((errors + 1))
  else
    echo "OK    ${label}: ${actual}"
  fi
}

# README: linha "## Versão X.Y.Z"
readme_ver="$(grep -E '^## Versão ' README.md 2>/dev/null | head -1 | sed -E 's/^## Versão[[:space:]]+//' | tr -d '[:space:]' || true)"
check "README.md (## Versão)" "${readme_ver:-<ausente>}"

# FastAPI app.version
if [[ -f services/transcription-service/app/main.py ]]; then
  app_ver="$(python3 - <<'PY'
import re, pathlib
text = pathlib.Path("services/transcription-service/app/main.py").read_text(encoding="utf-8")
m = re.search(r'FastAPI\([^)]*version\s*=\s*["\']([^"\']+)["\']', text, re.S)
print(m.group(1) if m else "")
PY
)"
  check "transcription-service app.version" "${app_ver:-<ausente>}"
fi

# Agent pyproject
if [[ -f agents/windows-audio-agent/pyproject.toml ]]; then
  agent_ver="$(python3 - <<'PY'
import re, pathlib
text = pathlib.Path("agents/windows-audio-agent/pyproject.toml").read_text(encoding="utf-8")
m = re.search(r'(?m)^version\s*=\s*["\']([^"\']+)["\']', text)
print(m.group(1) if m else "")
PY
)"
  check "windows-audio-agent pyproject" "${agent_ver:-<ausente>}"
fi

# Agent CLI (__init__.py __version__, fonte usada por main.py --version)
if [[ -f agents/windows-audio-agent/src/assistant_hub_audio/__init__.py ]]; then
  agent_cli_ver="$(python3 - <<'PY'
import re, pathlib
text = pathlib.Path("agents/windows-audio-agent/src/assistant_hub_audio/__init__.py").read_text(encoding="utf-8")
m = re.search(r'(?m)^__version__\s*=\s*["\']([^"\']+)["\']', text)
print(m.group(1) if m else "")
PY
)"
  check "windows-audio-agent __init__.py" "${agent_cli_ver:-<ausente>}"
fi

# CI assert (se existir literal)
if [[ -f .github/workflows/ci.yml ]]; then
  ci_ver="$(grep -oE "app\.version == ['\"][^'\"]+['\"]" .github/workflows/ci.yml | head -1 | sed -E "s/.*['\"]([^'\"]+)['\"]/\1/" || true)"
  if [[ -n "${ci_ver}" ]]; then
    check "CI assert app.version" "${ci_ver}"
  else
    echo "SKIP  CI assert app.version (padrão não encontrado — use VERSION via env no workflow)"
  fi
fi

if [[ "${errors}" -gt 0 ]]; then
  echo
  echo "Drift de versão: ${errors} inconsistência(s). Corrija antes do merge/release."
  exit 1
fi

echo
echo "Versões alinhadas em ${EXPECTED}"
