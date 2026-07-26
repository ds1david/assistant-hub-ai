#!/usr/bin/env bash
# Gera SHA256SUMS (ou SHA256SUMS.txt) para todos os arquivos regulares de um diretório.
# Uso: scripts/release/checksum-artifacts.sh <dir> [output-file]
# issue #66 / specs/031-issue-66-r5-release-hardening
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "uso: $0 <artifact-dir> [SHA256SUMS]" >&2
  exit 2
fi

DIR="${1%/}"
OUT="${2:-$DIR/SHA256SUMS}"

if [[ ! -d "$DIR" ]]; then
  echo "diretório inexistente: $DIR" >&2
  exit 1
fi

# Lista arquivos regulares (não dirs), relativo a DIR; exclui o próprio SUMS se re-rodar.
mapfile -t FILES < <(
  find "$DIR" -type f ! -name 'SHA256SUMS' ! -name 'SHA256SUMS.txt' ! -name '*.sig' | sort
)

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "nenhum artefato em $DIR" >&2
  exit 1
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

for f in "${FILES[@]}"; do
  rel="${f#"$DIR"/}"
  if command -v sha256sum >/dev/null 2>&1; then
    # sha256sum imprime "hash  path" — normalizamos path relativo
    hash="$(sha256sum "$f" | awk '{print $1}')"
  elif command -v shasum >/dev/null 2>&1; then
    hash="$(shasum -a 256 "$f" | awk '{print $1}')"
  else
    echo "precisa de sha256sum ou shasum" >&2
    exit 1
  fi
  printf '%s  %s\n' "$hash" "$rel" >>"$TMP"
done

mkdir -p "$(dirname "$OUT")"
mv "$TMP" "$OUT"
trap - EXIT
echo "escrito: $OUT (${#FILES[@]} arquivos)"
cat "$OUT"
