#!/usr/bin/env bash
# Orquestrador SDD do Assistant Hub AI.
# Não contém lógica de domínio. Automação com gates humanos.
# Contrato: ver docs/governance/sdd-process.md e constituição.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "${ROOT}" ]] || { echo "ERRO: execute dentro de um repositório Git" >&2; exit 1; }
cd "${ROOT}"

RUNS_DIR=".specify/workflows/runs"
CMD="${1:-}"
shift || true

DRY_RUN=0
ALLOW_DIRTY=0
SCOPE="auto"
JSON_OUT=0
DRAFT=1

for arg in "$@"; do
  case "${arg}" in
    --dry-run) DRY_RUN=1 ;;
    --allow-dirty) ALLOW_DIRTY=1 ;;
    --json) JSON_OUT=1 ;;
    --draft) DRAFT=1 ;;
    --no-draft) DRAFT=0 ;;
    --scope=*) SCOPE="${arg#--scope=}" ;;
    --scope) : ;; # handled below if needed
  esac
done

# parse --scope value when passed as separate token
prev=""
for arg in "$@"; do
  if [[ "${prev}" == "--scope" ]]; then
    SCOPE="${arg}"
  fi
  prev="${arg}"
done

die() { echo "ERRO: $*" >&2; exit 1; }
info() { echo "→ $*"; }
need() { command -v "$1" >/dev/null 2>&1 || die "dependência ausente: $1"; }

confirm() {
  local prompt="${1:-Continuar?}"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    info "[dry-run] pularia confirmação: ${prompt}"
    return 0
  fi
  read -r -p "${prompt} [y/N] " ans || true
  [[ "${ans}" == "y" || "${ans}" == "Y" || "${ans}" == "yes" ]] || die "cancelado pelo usuário"
}

run_or_echo() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    info "[dry-run] $*"
  else
    eval "$@"
  fi
}

tree_clean() {
  [[ -z "$(git status --porcelain)" ]]
}

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g' | cut -c1-48
}

latest_run_id() {
  [[ -d "${RUNS_DIR}" ]] || return 1
  find "${RUNS_DIR}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort | tail -1
}

meta_path() {
  echo "${RUNS_DIR}/$1/meta.json"
}

write_meta() {
  local run_id="$1"
  local file
  file="$(meta_path "${run_id}")"
  mkdir -p "$(dirname "${file}")"
  cat > "${file}"
}

read_meta_field() {
  local run_id="$1" field="$2"
  local file
  file="$(meta_path "${run_id}")"
  [[ -f "${file}" ]] || die "run não encontrado: ${run_id}"
  jq -r --arg f "${field}" '.[$f] // empty' "${file}"
}

# ---------------------------------------------------------------------------
cmd_doctor() {
  local ok=1
  for bin in git gh jq python3; do
    if command -v "${bin}" >/dev/null 2>&1; then
      echo "OK    ${bin}: $(command -v "${bin}")"
    else
      echo "FAIL  ${bin}: não encontrado"
      ok=0
    fi
  done
  for bin in specify claude docker mvn; do
    if command -v "${bin}" >/dev/null 2>&1; then
      echo "OK    ${bin}: $(command -v "${bin}")"
    else
      echo "WARN  ${bin}: não encontrado (pode ser necessário depois)"
    fi
  done

  git rev-parse --is-inside-work-tree >/dev/null
  echo "OK    git repo: ${ROOT}"

  if gh auth status >/dev/null 2>&1; then
    echo "OK    gh auth"
  else
    echo "WARN  gh auth: não autenticado"
  fi

  if [[ -f VERSION ]]; then
    echo "OK    VERSION=$(tr -d '[:space:]' < VERSION)"
  else
    echo "WARN  VERSION ausente na raiz"
  fi

  if [[ -f .specify/memory/constitution.md ]]; then
    echo "OK    constituição presente"
  else
    echo "WARN  .specify/memory/constitution.md ausente"
  fi

  if [[ "${ok}" -ne 1 ]]; then
    die "doctor encontrou dependências obrigatórias faltando"
  fi
  echo "doctor: OK"
}

# ---------------------------------------------------------------------------
cmd_start() {
  local issue="${1:-}"
  [[ -n "${issue}" ]] || die "uso: start <issue-number> [--allow-dirty] [--dry-run]"
  need gh
  need jq

  if [[ "${ALLOW_DIRTY}" -ne 1 ]] && ! tree_clean; then
    die "árvore suja; faça commit/stash ou use --allow-dirty"
  fi

  local issue_json title key slug branch run_id now
  issue_json="$(gh issue view "${issue}" --json number,title,state,url)"
  local state
  state="$(echo "${issue_json}" | jq -r .state)"
  [[ "${state}" == "OPEN" ]] || die "issue #${issue} não está OPEN (state=${state})"

  title="$(echo "${issue_json}" | jq -r .title)"
  # tenta extrair SF-018 ou similar do título
  key="$(echo "${title}" | grep -oE '[Ss][Ff]-[0-9]+' | head -1 | tr '[:upper:]' '[:lower:]' || true)"
  if [[ -z "${key}" ]]; then
    key="issue-${issue}"
  fi
  slug="$(slugify "${title}")"
  branch="feature/${key}-${slug}"
  # evita branch absurdamente longa
  branch="$(echo "${branch}" | cut -c1-80 | sed -E 's/-+$//')"

  now="$(date -u +%Y%m%dT%H%M%SZ)"
  run_id="${key}-${now}"

  info "issue=#${issue} title=${title}"
  info "branch=${branch}"
  info "run_id=${run_id}"

  if git show-ref --verify --quiet "refs/heads/${branch}"; then
    info "branch local já existe; reutilizando"
    run_or_echo "git switch '${branch}'"
  elif git ls-remote --exit-code --heads origin "${branch}" >/dev/null 2>&1; then
    info "branch remota existe; fazendo checkout"
    run_or_echo "git fetch origin '${branch}:${branch}'"
    run_or_echo "git switch '${branch}'"
  else
    run_or_echo "git switch main"
    run_or_echo "git pull --ff-only origin main || git pull --ff-only"
    run_or_echo "git switch -c '${branch}'"
  fi

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    info "[dry-run] gravaria meta em ${RUNS_DIR}/${run_id}/meta.json"
  else
    write_meta "${run_id}" <<EOF
{
  "run_id": "${run_id}",
  "issue": ${issue},
  "issue_url": $(echo "${issue_json}" | jq .url),
  "title": $(echo "${issue_json}" | jq .title),
  "branch": "${branch}",
  "key": "${key}",
  "stage": "start",
  "spec_dir": null,
  "created_at": "${now}",
  "updated_at": "${now}"
}
EOF
  fi

  cat <<EOF

Próximos passos (Claude Code no WSL):
  1. /speckit.specify   → criar/atualizar specs/00x-${key}-*/
  2. Gate G1 (humano)   → validar requisitos
  3. /speckit.clarify → /speckit.plan → /speckit.checklist → /speckit.tasks
  4. /speckit.analyze   → Gate G2 (humano)
  5. /speckit.implement → testes → ./scripts/wsl/spec-cycle.sh test
  6. ./scripts/wsl/spec-cycle.sh finalize ${issue} --draft

Run: ${run_id}
EOF
}

# ---------------------------------------------------------------------------
cmd_status() {
  local run_id="${1:-}"
  if [[ -z "${run_id}" ]]; then
    run_id="$(latest_run_id || true)"
    [[ -n "${run_id}" ]] || die "nenhum run local; informe run-id"
  fi
  local file
  file="$(meta_path "${run_id}")"
  [[ -f "${file}" ]] || die "run não encontrado: ${run_id}"

  if [[ "${JSON_OUT}" -eq 1 ]]; then
    cat "${file}"
    return 0
  fi

  echo "run_id:    $(jq -r .run_id "${file}")"
  echo "issue:     #$(jq -r .issue "${file}")"
  echo "branch:    $(jq -r .branch "${file}")"
  echo "stage:     $(jq -r .stage "${file}")"
  echo "spec_dir:  $(jq -r .spec_dir "${file}")"
  echo "updated:   $(jq -r .updated_at "${file}")"
  echo "git:       $(git branch --show-current) | $(git rev-parse --short HEAD)"
  echo "dirty:     $(tree_clean && echo no || echo yes)"
}

# ---------------------------------------------------------------------------
cmd_resume() {
  local run_id="${1:-}"
  [[ -n "${run_id}" ]] || die "uso: resume <run-id>"
  local branch stage
  branch="$(read_meta_field "${run_id}" branch)"
  stage="$(read_meta_field "${run_id}" stage)"
  info "retomando run=${run_id} stage=${stage} branch=${branch}"
  run_or_echo "git switch '${branch}'"
  cmd_status "${run_id}"
  cat <<EOF

Retome no Claude Code a partir do stage '${stage}'.
Use /speckit.* na ordem da constituição. Não pule Analyze antes de Implement.
EOF
}

# ---------------------------------------------------------------------------
cmd_test() {
  local failed=0
  local paths
  paths="$(git diff --name-only origin/main...HEAD 2>/dev/null || git diff --name-only HEAD~1...HEAD 2>/dev/null || true)"

  should_agent=0
  should_service=0
  should_java=0
  should_scripts=0

  case "${SCOPE}" in
    all)
      should_agent=1; should_service=1; should_java=1; should_scripts=1
      ;;
    agent) should_agent=1 ;;
    service) should_service=1 ;;
    java) should_java=1 ;;
    auto|*)
      echo "${paths}" | grep -q '^agents/windows-audio-agent/' && should_agent=1 || true
      echo "${paths}" | grep -q '^services/transcription-service/' && should_service=1 || true
      echo "${paths}" | grep -qE '^(packages/|services/session-core/|pom.xml)' && should_java=1 || true
      echo "${paths}" | grep -q '^scripts/' && should_scripts=1 || true
      # se nada detectado, roda agent+service por segurança em feature de áudio
      if [[ "${should_agent}" -eq 0 && "${should_service}" -eq 0 && "${should_java}" -eq 0 ]]; then
        should_agent=1
        should_service=1
      fi
      ;;
  esac

  info "scope=${SCOPE} agent=${should_agent} service=${should_service} java=${should_java} scripts=${should_scripts}"

  if [[ "${should_scripts}" -eq 1 ]]; then
    if command -v shellcheck >/dev/null 2>&1; then
      run_or_echo "shellcheck scripts/wsl/*.sh scripts/release/*.sh || true"
    fi
    run_or_echo "bash -n scripts/wsl/spec-cycle.sh"
    run_or_echo "bash -n scripts/release/check-version.sh || true"
  fi

  if [[ "${should_agent}" -eq 1 ]]; then
    info "testes agent"
    if [[ "${DRY_RUN}" -eq 1 ]]; then
      info "[dry-run] compileall + pytest agents/windows-audio-agent"
    else
      python3 -m compileall -q agents/windows-audio-agent/src || failed=1
      if [[ -d agents/windows-audio-agent/tests ]]; then
        PYTHONPATH=agents/windows-audio-agent/src python3 -m pytest -q agents/windows-audio-agent/tests || failed=1
      fi
    fi
  fi

  if [[ "${should_service}" -eq 1 ]]; then
    info "testes transcription-service"
    if [[ "${DRY_RUN}" -eq 1 ]]; then
      info "[dry-run] compileall + pytest transcription-service"
    else
      python3 -m compileall -q services/transcription-service/app || failed=1
      if [[ -d services/transcription-service/tests ]]; then
        PYTHONPATH=services/transcription-service python3 -m pytest -q services/transcription-service/tests || failed=1
      fi
    fi
  fi

  if [[ "${should_java}" -eq 1 ]]; then
    info "testes Java"
    if command -v mvn >/dev/null 2>&1; then
      run_or_echo "mvn -q test" || failed=1
    else
      echo "WARN  mvn ausente; pulando Java"
    fi
  fi

  if [[ -x scripts/release/check-version.sh ]]; then
    run_or_echo "./scripts/release/check-version.sh" || failed=1
  fi

  [[ "${failed}" -eq 0 ]] || die "testes falharam"
  echo "test: OK"
}

# ---------------------------------------------------------------------------
cmd_finalize() {
  local issue="${1:-}"
  [[ -n "${issue}" ]] || die "uso: finalize <issue-number> [--draft] [--dry-run]"
  need gh
  need jq

  info "diff vs main (stat)"
  git fetch origin main >/dev/null 2>&1 || true
  git diff --stat origin/main...HEAD || git diff --stat main...HEAD || true
  echo
  git diff --check || die "git diff --check falhou"

  info "Gate G3 — validação humana antes de commit/push/PR"
  confirm "Diff e testes estão OK para publicar PR draft?"

  # bloquear arquivos sensíveis no stage
  if git status --porcelain | grep -E '\.env$|secrets|\.venv|__pycache__|\.wav$' >/dev/null 2>&1; then
    die "arquivos sensíveis ou transitórios detectados no working tree; limpe antes"
  fi

  local branch
  branch="$(git branch --show-current)"
  [[ "${branch}" != "main" ]] || die "não finalize a partir de main"

  info "branch=${branch} issue=#${issue}"

  if [[ -z "$(git status --porcelain)" ]]; then
    info "nada para commitar no working tree; seguirá para push/PR se houver commits locais"
  else
    confirm "Criar commit(s) com o estado atual?"
    run_or_echo "git add -A"
    # segurança extra: unstage padrões perigosos
    run_or_echo "git reset HEAD -- .env .env.local '*.wav' recordings/ .venv .venv-transcription .specify/workflows/runs 2>/dev/null || true"
    run_or_echo "git commit -m \"feat: close issue #${issue} on ${branch}\""
  fi

  run_or_echo "git push -u origin '${branch}'"

  local existing
  existing="$(gh pr list --head "${branch}" --json number,url --jq '.[0].url // empty' || true)"
  if [[ -n "${existing}" ]]; then
    info "PR já existe: ${existing}"
    confirm "Atualizar descrição da PR existente?"
    # descrição mínima; usuário completa
    run_or_echo "gh pr edit --body \"Atualizado por spec-cycle. Issue #${issue}. Ver checklist do template.\""
  else
    local draft_flag=()
    [[ "${DRAFT}" -eq 1 ]] && draft_flag=(--draft)
    run_or_echo "gh pr create ${draft_flag[*]} --title \"${branch}\" --body \"## Objetivo\n\nFecha trabalho da issue #${issue}.\n\n## Spec\n- Diretório: (preencher)\n- Issue: #${issue}\n\n## Validação\n- [ ] CI\n- [ ] Testes locais\n- [ ] Validação manual se aplicável\n\nCloses #${issue}\""
  fi

  echo "finalize: OK — merge continua MANUAL (Gate G4)"
}

# ---------------------------------------------------------------------------
cmd_clean() {
  local run_id="${1:-}"
  [[ -n "${run_id}" ]] || die "uso: clean <run-id>"
  local dir="${RUNS_DIR}/${run_id}"
  [[ -d "${dir}" ]] || die "run não encontrado: ${run_id}"
  confirm "Remover estado local ${dir}?"
  run_or_echo "rm -rf '${dir}'"
  echo "clean: OK"
}

# ---------------------------------------------------------------------------
cmd_report() {
  local issue="${1:-}"
  [[ -n "${issue}" ]] || die "uso: report <issue-number> [--json]"
  local branch head
  branch="$(git branch --show-current)"
  head="$(git rev-parse --short HEAD)"
  if [[ "${JSON_OUT}" -eq 1 ]]; then
    jq -n --arg issue "${issue}" --arg branch "${branch}" --arg head "${head}" \
      '{issue:$issue, branch:$branch, head:$head, generatedAt:now|todate}'
  else
    cat <<EOF
# Report issue #${issue}

- Branch: ${branch}
- HEAD: ${head}
- Dirty: $(tree_clean && echo no || echo yes)
- VERSION: $(tr -d '[:space:]' < VERSION 2>/dev/null || echo n/a)

## Diff stat vs main
$(git diff --stat origin/main...HEAD 2>/dev/null || git diff --stat main...HEAD 2>/dev/null || echo "(indisponível)")
EOF
  fi
}

# ---------------------------------------------------------------------------
usage() {
  cat <<'USAGE'
Uso: ./scripts/wsl/spec-cycle.sh <comando> [args]

  doctor
  start <issue> [--allow-dirty] [--dry-run]
  status [run-id] [--json]
  resume <run-id>
  test [--scope auto|all|agent|service|java] [--dry-run]
  finalize <issue> [--draft|--no-draft] [--dry-run]
  clean <run-id>
  report <issue> [--json]

Princípios: merge manual, sem force push, gates humanos, sem lógica de domínio.
USAGE
}

case "${CMD}" in
  doctor)   cmd_doctor ;;
  start)    cmd_start "$@" ;;
  status)   cmd_status "$@" ;;
  resume)   cmd_resume "$@" ;;
  test)     cmd_test ;;
  finalize) cmd_finalize "$@" ;;
  clean)    cmd_clean "$@" ;;
  report)   cmd_report "$@" ;;
  ""|-h|--help|help) usage ;;
  *) usage; die "comando desconhecido: ${CMD}" ;;
esac
