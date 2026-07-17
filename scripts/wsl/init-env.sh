#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
ENV_EXAMPLE="$REPO_ROOT/.env.example"

if [[ ! -f "$ENV_EXAMPLE" ]]; then
  echo "Arquivo de exemplo não encontrado: $ENV_EXAMPLE" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  install -m 600 "$ENV_EXAMPLE" "$ENV_FILE"
  echo "Arquivo .env criado em $ENV_FILE"
else
  chmod 600 "$ENV_FILE"
fi

# Acrescenta somente chaves novas do template, sem sobrescrever valores locais.
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
  key="${line%%=*}"
  [[ -z "$key" ]] && continue
  if ! grep -qE "^[[:space:]]*${key}=" "$ENV_FILE"; then
    printf '\n%s\n' "$line" >> "$ENV_FILE"
    echo "Chave adicionada ao .env: $key"
  fi
done < "$ENV_EXAMPLE"

printf '%s\n' "$ENV_FILE"
