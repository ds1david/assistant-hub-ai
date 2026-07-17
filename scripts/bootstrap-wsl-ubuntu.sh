#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf '\n==> %s\n' "$1"
}

if ! grep -qi microsoft /proc/version 2>/dev/null; then
  echo "AVISO: este script foi pensado para Ubuntu dentro do WSL 2." >&2
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "Erro: apt-get não encontrado. Execute em Ubuntu/Debian." >&2
  exit 1
fi

log "Atualizando pacotes do Ubuntu"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

log "Instalando ferramentas base"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  build-essential \
  ca-certificates \
  curl \
  git \
  gh \
  jq \
  make \
  unzip \
  zip \
  python3 \
  python3-venv \
  python3-pip

export SDKMAN_DIR="${SDKMAN_DIR:-$HOME/.sdkman}"
if [[ ! -s "$SDKMAN_DIR/bin/sdkman-init.sh" ]]; then
  log "Instalando SDKMAN"
  curl -s "https://get.sdkman.io" | bash
fi

# shellcheck disable=SC1091
source "$SDKMAN_DIR/bin/sdkman-init.sh"

# Evita prompts em automação. Versões específicas podem ser passadas por env:
# SDKMAN_JAVA_VERSION, SDKMAN_MAVEN_VERSION e SDKMAN_GRADLE_VERSION.
if [[ -f "$SDKMAN_DIR/etc/config" ]]; then
  sed -i 's/^sdkman_auto_answer=.*/sdkman_auto_answer=true/' "$SDKMAN_DIR/etc/config"
fi

install_candidate_if_missing() {
  local candidate="$1"
  local command_name="$2"
  local version="${3:-}"

  if command -v "$command_name" >/dev/null 2>&1; then
    echo "$candidate já disponível: $(command -v "$command_name")"
    return
  fi

  if [[ -n "$version" ]]; then
    sdk install "$candidate" "$version"
  else
    sdk install "$candidate"
  fi
}

log "Preparando Java, Maven e Gradle pelo SDKMAN"
install_candidate_if_missing java java "${SDKMAN_JAVA_VERSION:-}"
install_candidate_if_missing maven mvn "${SDKMAN_MAVEN_VERSION:-}"
install_candidate_if_missing gradle gradle "${SDKMAN_GRADLE_VERSION:-}"

if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
  log "Arquivo .env criado a partir de .env.example"
fi

log "Versões detectadas"
sdk current || true
java -version
mvn -version
gradle -version | sed -n '1,12p'
python3 --version
git --version
gh --version

if command -v docker >/dev/null 2>&1; then
  docker version || true
  docker compose version || true
else
  cat <<'MSG'

Docker não foi encontrado dentro do Ubuntu.
Instale o Docker Desktop no Windows e habilite:
Settings > Resources > WSL Integration > Ubuntu-24.04.
MSG
fi

if command -v code >/dev/null 2>&1; then
  echo "VS Code CLI detectado. Abra este diretório com: code ."
else
  echo "VS Code CLI não detectado. Instale o VS Code e a extensão WSL no Windows."
fi

if command -v claude >/dev/null 2>&1; then
  claude --version || true
else
  cat <<'MSG'

Claude Code ainda não está instalado no Ubuntu.
Instalação:
  curl -fsSL https://claude.ai/install.sh | bash
MSG
fi

log "Bootstrap do Ubuntu/WSL concluído"
