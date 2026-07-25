#!/usr/bin/env bash
# Atualiza VERSION e propaga para README, FastAPI e pyproject do agent.
# Uso: ./scripts/release/bump-version.sh 0.1.9
# Não cria tag nem commit — apenas edita arquivos.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

NEW="${1:-}"
[[ -n "${NEW}" ]] || { echo "uso: $0 <nova-versão-semver>"; exit 1; }
[[ "${NEW}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][A-Za-z0-9.]+)?$ ]] || {
  echo "ERRO: versão inválida: ${NEW}"
  exit 1
}

OLD="$(tr -d '[:space:]' < VERSION 2>/dev/null || echo "")"
echo "${NEW}" > VERSION
echo "VERSION: ${OLD:-<novo>} -> ${NEW}"

if [[ -f README.md ]]; then
  if grep -qE '^## Versão ' README.md; then
    sed -i -E "s/^## Versão .*/## Versão ${NEW}/" README.md
  else
    echo "AVISO: README sem linha '## Versão'; adicione manualmente"
  fi
fi

if [[ -f services/transcription-service/app/main.py ]]; then
  python3 - <<PY
from pathlib import Path
import re
path = Path("services/transcription-service/app/main.py")
text = path.read_text(encoding="utf-8")
new_text, n = re.subn(
    r'(FastAPI\([^)]*version\s*=\s*)["\'][^"\']+["\']',
    r'\1"${NEW}"',
    text,
    count=1,
    flags=re.S,
)
if n == 0:
    print("AVISO: app.version não encontrado em main.py")
else:
    path.write_text(new_text, encoding="utf-8")
    print("transcription-service app.version atualizado")
PY
fi

if [[ -f agents/windows-audio-agent/pyproject.toml ]]; then
  python3 - <<PY
from pathlib import Path
import re
path = Path("agents/windows-audio-agent/pyproject.toml")
text = path.read_text(encoding="utf-8")
new_text, n = re.subn(
    r'(?m)^(version\s*=\s*)["\'][^"\']+["\']',
    r'\1"${NEW}"',
    text,
    count=1,
)
if n == 0:
    print("AVISO: version não encontrado em pyproject.toml")
else:
    path.write_text(new_text, encoding="utf-8")
    print("windows-audio-agent pyproject atualizado")
PY
fi

# Agent CLI __version__ (fonte usada por --version / check-version.sh)
if [[ -f agents/windows-audio-agent/src/assistant_hub_audio/__init__.py ]]; then
  python3 - <<PY
from pathlib import Path
import re
path = Path("agents/windows-audio-agent/src/assistant_hub_audio/__init__.py")
text = path.read_text(encoding="utf-8")
new_text, n = re.subn(
    r'(?m)^(__version__\s*=\s*)["\'][^"\']+["\']',
    r'\1"${NEW}"',
    text,
    count=1,
)
if n == 0:
    print("AVISO: __version__ não encontrado em assistant_hub_audio/__init__.py")
else:
    path.write_text(new_text, encoding="utf-8")
    print("windows-audio-agent __init__.__version__ atualizado")
PY
fi

if [[ -f .github/workflows/ci.yml ]]; then
  # Atualiza assert literal se existir
  sed -i -E "s/(app\.version == ['\"])[^'\"]+(['\"])/\1${NEW}\2/" .github/workflows/ci.yml || true
  echo "CI workflow: assert alinhado (se padrão existia)"
fi

echo
echo "Próximo: ./scripts/release/check-version.sh && git diff"
