# Tasks: Release Hardening e tag de produto (pós R1–R6)

**Input**: Design documents from `/specs/016-issue-39-release-hardening/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/release-process.md, quickstart.md

**Tests**: Não solicitados na spec (feature de processo/release). Validação = scripts existentes, CI remoto e [quickstart.md](./quickstart.md).

**Organization**: Tasks agrupadas por user story para entrega incremental e testável.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: US1–US4 conforme spec.md
- Toda task inclui caminho de arquivo

## Path Conventions

Monorepo raiz: `VERSION`, `CHANGELOG.md`, `README.md`, `.gitignore`, `.github/workflows/ci.yml`, `scripts/release/`, `docs/release/`, `docs/governance/`, `apps/desktop-shell/`, `agents/windows-audio-agent/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar baseline e criar diretórios/docs de release sem ainda alterar comportamento de CI/versão.

- [x] T001 Confirm baseline: run `./scripts/release/check-version.sh` and record current `VERSION` (file `VERSION`); list existing tags with `git tag -l`
- [x] T002 [P] Create directory `docs/release/` and placeholder note if empty (ensure path exists for template and min-flow)
- [x] T003 [P] Verify no tracked memory-hub databases: `git ls-files '*.db' '**/memory-hub.db'` and document result for hygiene work in `.gitignore`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infra compartilhada que bloqueia as user stories — higiene de db, bump completo, template de checklist, smoke desktop no CI.

**⚠️ CRITICAL**: User story work (além de leitura) assume esta fase completa.

- [x] T004 Harden Memory Hub ignore rules in `.gitignore` for `data/session-core/*.db`, `data/session-core/*.db-*`, `services/session-core/data/*.db`, `services/session-core/data/*.db-*`, and `**/memory-hub.db` / `**/memory-hub.db-*` (FR-009; research Decision 5); untrack with `git rm --cached` only if any `.db` is already tracked
- [x] T005 Extend `scripts/release/bump-version.sh` to also update `agents/windows-audio-agent/src/assistant_hub_audio/__init__.py` `__version__` so it stays aligned with `VERSION` (research Decision 1; required by `scripts/release/check-version.sh`)
- [x] T006 [P] Create `docs/release/checklist-template.md` with required sections from `specs/016-issue-39-release-hardening/contracts/release-process.md` §3 (Metadata, CI, Version, Gaps, Debts, Hygiene, Min-flow docs, Ready for tag) and minimum gap/debt row ids (`SF-020-T024`, `DESKTOP-T033`, `InvocationResult-sourceType`, `frontend-vite-audit`)
- [x] T007 Add job `desktop-shell-smoke` to `.github/workflows/ci.yml` on `ubuntu-latest`: checkout; setup Node LTS + `npm ci` / `npm test` / `npm run build` in `apps/desktop-shell`; setup Rust stable + `cargo test --manifest-path apps/desktop-shell/src-tauri/Cargo.toml` (no `tauri build`/MSI) (FR-013; research Decision 3)
- [x] T008 Dry-run desktop smoke commands locally from repo root matching T007 (`apps/desktop-shell` npm + `src-tauri` cargo test) and fix only config/path issues if the smoke would fail CI without domain-feature changes

**Checkpoint**: gitignore + bump + checklist template + desktop CI job ready; user stories can proceed.

---

## Phase 3: User Story 1 — Main verde e auditável (Priority: P1) 🎯 MVP

**Goal**: Mantenedor confia que a linha principal é shippable: CI inventariado, versão coerente verificável, gaps sem PASS inventado.

**Independent Test**: Inspecionar checklist (template ou cópia) + status dos jobs no escopo + `check-version.sh` e confirmar que jobs existentes têm slot de evidência, jobs ausentes seriam “sem job”, e gaps T024/T033 aparecem como `gap` se não houver `docs/validation` real.

### Implementation for User Story 1

- [x] T009 [US1] Fill CI job inventory table in `docs/release/checklist-template.md` with job ids from `.github/workflows/ci.yml` (`policy`, `java`, `transcription-python`, `windows-audio-agent-unit`, `windows-audio-agent-windows-smoke`, `compose`, `desktop-shell-smoke`) and columns exists/status/evidence per contracts/release-process.md §2
- [x] T010 [P] [US1] Document gap policy in `docs/release/checklist-template.md` Gaps section: status only `gap`|`pass`|`n-a`; forbid invented PASS; pre-seed rows for `SF-020-T024` (expect gap until `docs/validation/sf-020-windows.md` has real PASS) and `DESKTOP-T033` (expect gap until Windows GUI validation exists) (FR-008, SC-005)
- [x] T011 [P] [US1] Add short “Version audit” subsection to `docs/release/checklist-template.md` instructing run of `./scripts/release/check-version.sh` and listing consistency points (`VERSION`, `README.md` `## Versão`, transcription FastAPI version, agent pyproject + `__init__.py`, CI assert if literal) (FR-003, SC-002)
- [x] T012 [US1] Optionally align `docs/governance/sdd-process.md` Versionamento section with links to `docs/release/checklist-template.md` and `CHANGELOG.md` (create link targets even if CHANGELOG still empty stub) without changing constitutional policy
- [x] T013 [US1] Verify `./scripts/release/check-version.sh` passes on current tree after T005; if drift remains, fix only version-propagation bugs in `scripts/release/bump-version.sh` or known version fields (no domain features)

**Checkpoint**: Template auditável para CI/versão/gaps; checker verde no estado atual — MVP de auditabilidade.

---

## Phase 4: User Story 2 — Tag de produto + changelog (Priority: P1)

**Goal**: Changelog curto do marco + processo para publicar tag SemVer em `main` após CI verde e checklist YES (gate humano).

**Independent Test**: `CHANGELOG.md` descreve o marco; checklist versionado existe; sequência de tag documentada; **tag real** só após merge em `main` + CI verde (pode ficar pendente de gate humano no final desta phase).

**Note**: T019–T022 dependem de US1 (CI/gaps template) e são mais seguros após US3/US4 docs/debts; a tag (T022) é o último ato e exige gate humano (P8).

### Implementation for User Story 2

- [x] T014 [US2] Create `CHANGELOG.md` at repo root with Keep-a-Changelog-style skeleton and a draft section for the target version (recommended `0.2.0` per research.md) including Summary / Gaps / Known debts placeholders (FR-004)
- [x] T015 [US2] Document tag sequence in `docs/release/checklist-template.md` (or short `docs/release/tagging.md` linked from template): merge to `main` → CI green on that SHA → Ready for tag YES → annotated tag `v`+VERSION on that SHA → push tag (FR-005; contracts §5); explicitly forbid tagging feature branch only
- [x] T016 [US2] Choose final SemVer for this release (default recommend `0.2.0`), run `./scripts/release/bump-version.sh <semver>` updating `VERSION`, `README.md`, `services/transcription-service/app/main.py`, `agents/windows-audio-agent/pyproject.toml`, `agents/windows-audio-agent/src/assistant_hub_audio/__init__.py`, and CI assert in `.github/workflows/ci.yml`, then `./scripts/release/check-version.sh` must exit 0
- [x] T017 [US2] Copy `docs/release/checklist-template.md` to `docs/release/checklist-<versão>.md` and fill Metadata (version, date, maintainer); leave CI evidence/SHA until after merge if needed
- [x] T018 [US2] Complete Gaps and Debts tables in `docs/release/checklist-<versão>.md` and mirror the same in `CHANGELOG.md` section (no invented PASS; debts need issue links or won’t-fix from US4) (SC-005, SC-007)
- [ ] T019 [US2] After hardening PR is on `main` (human merge), record commit SHA and CI run links for every existing in-scope job in `docs/release/checklist-<versão>.md`; any red job blocks tag (FR-002, SC-001)
- [ ] T020 [US2] Set Ready for tag = YES only when SC-001/002/005/006/007/008 satisfied in `docs/release/checklist-<versão>.md` (SC-008)
- [ ] T021 [US2] **Human gate**: create annotated tag `v$(cat VERSION)` on the documented `main` SHA and `git push origin <tag>` (do not automate merge/tag in scripts) (FR-005, SC-003)
- [ ] T022 [P] [US2] Optional: publish GitHub Release for the tag with body copied from the `CHANGELOG.md` section for that version

**Checkpoint**: Tag `vX.Y.Z` no remoto aponta para `main`; changelog e checklist auditáveis.

---

## Phase 5: User Story 3 — Fluxo mínimo só com README (Priority: P1)

**Goal**: Outro dev sobe WSL + agent Windows + desktop + provedores seguindo só README e links de ops.

**Independent Test**: Seguir `docs/release/min-flow.md` a partir do README e verificar critérios de “no ar” por pilar (ou registrar bloqueio de ambiente sem chamar de sucesso parcial).

### Implementation for User Story 3

- [x] T023 [US3] Write `docs/release/min-flow.md` covering three mandatory pillars with prerequisites, commands, verification criteria, and common failures: (1) WSL — compose/STT + session-core health, (2) Windows agent connected, (3) desktop shell up — plus providers section using `samples/ai-providers/providers.example.yaml` → gitignored `config/ai-providers.yaml` and `docs/security/provider-secrets.md` (FR-006, FR-007; research Decision 6)
- [x] T024 [US3] Add README section “Fluxo mínimo (release)” in `README.md` that links to `docs/release/min-flow.md`, states all three pillars are required for acceptance, and keeps WSL vs Windows boundary explicit (SC-004)
- [x] T025 [P] [US3] Cross-link from `docs/release/min-flow.md` to existing ops docs: `docs/development/wsl-first.md`, `docs/desktop-shell/packaging.md`, compose/start scripts under `scripts/wsl/`, and agent CLI notes already in `README.md` / AGENTS.md without duplicating long content
- [x] T026 [US3] Ensure `docs/release/checklist-template.md` Min-flow docs section requires links to `README.md` + `docs/release/min-flow.md` as checklist evidence
- [x] T027 [US3] Walkthrough dry-run of min-flow docs for consistency (commands exist, paths real); fix broken links/paths in `docs/release/min-flow.md` and `README.md` only — full hardware SC-004 may remain environment-blocked and must be noted, not faked

**Checkpoint**: Onboarding documentado de ponta a ponta; SC-004 executável por outro dev com host completo.

---

## Phase 6: User Story 4 — Higiene e débitos explícitos (Priority: P2)

**Goal**: Db local não polui git; débitos conhecidos listados com issue link ou won’t-fix justificado.

**Independent Test**: `git check-ignore` / `git status` não oferece `memory-hub.db`; checklist/changelog apontam issues (ou won’t-fix) para débitos do escopo.

### Implementation for User Story 4

- [x] T028 [US4] Re-verify hygiene after T004: create temp touch paths if needed and `git check-ignore -v` for `data/session-core/memory-hub.db` and `services/session-core/data/memory-hub.db`; confirm `git ls-files` has zero memory-hub db files (SC-006)
- [x] T029 [P] [US4] Open or locate GitHub issue for `InvocationResult` / `sourceType` consistency debt; record number/URL for checklist Debts row `InvocationResult-sourceType` (FR-010)
- [x] T030 [P] [US4] Open or locate GitHub issue for frontend npm audit / Vite major; document won’t major-bump this tag (FR-012) with issue link or explicit won’t-fix rationale in checklist (FR-010)
- [x] T031 [US4] Fill Debts table in `docs/release/checklist-template.md` examples and in `docs/release/checklist-<versão>.md` + `CHANGELOG.md` Known debts with the issue URLs / won’t-fix text from T029–T030 (SC-007)
- [x] T032 [US4] Confirm `.gitignore` still ignores `config/ai-providers.yaml` (already present) and that min-flow docs do not instruct committing secrets (`docs/release/min-flow.md`, `docs/security/provider-secrets.md` link)

**Checkpoint**: Higiene verificável; débitos rastreáveis (list + issue).

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Fechar o ciclo SDD, PR e validação quickstart sem violar P8.

- [x] T033 [P] Link release artifacts from `docs/governance/sdd-process.md` (checklist template, CHANGELOG, min-flow) if not fully done in T012
- [x] T034 [P] Run local validation Passos 0–3 from `specs/016-issue-39-release-hardening/quickstart.md` (check-version, gitignore, desktop smoke, checklist presence) and fix only release-hardening scope failures
- [x] T035 Ensure PR description lists files touched, tests/commands run, open gaps (T024/T033 validation), and debt issue links; no secrets in diff
- [ ] T036 **Human gates**: PR review → merge to `main` → confirm CI green → complete T019–T021 if not already; do not force-push or auto-merge
- [ ] T037 Final audit &lt;15 min per SC-002 using checklist + tag remote + `check-version.sh` on the tagged commit

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: imediato
- **Foundational (Phase 2)**: após Setup — **bloqueia** stories de implementação de artefatos
- **US1 (Phase 3)**: após Foundational — 🎯 MVP auditabilidade
- **US2 (Phase 4)**: template/changelog cedo (T014–T015) após Foundational; **bump/checklist preenchido/tag (T016–T022)** após US1 + preferencialmente US3 + US4; tag só pós-merge `main` + CI verde
- **US3 (Phase 5)**: após Foundational; pode paralelizar com US1 e início de US2/US4
- **US4 (Phase 6)**: após Foundational (T004); issues em paralelo com US3
- **Polish (Phase 7)**: após stories desejadas; merge/tag com gate humano

### User Story Dependencies

```text
Phase 1 Setup
    ↓
Phase 2 Foundational (T004–T008)
    ↓
    ├─→ US1 (T009–T013) ──┐
    ├─→ US3 (T023–T027) ──┼─→ US2 late (T016–T022 tag)
    └─→ US4 (T028–T032) ──┘
    ↓
Phase 7 Polish (T033–T037)
```

- **US1**: independente após Foundational
- **US3**: independente após Foundational (docs)
- **US4**: depende de T004; issues [P]
- **US2 tag**: depende de CI job (T007), checklist template (T006/US1), débitos (US4), min-flow links (US3), merge humano

### Parallel Opportunities

- T002 || T003
- T006 || T007 (depois T004/T005 podem sequenciar com T007)
- T010 || T011
- T022 opcional após T021
- T025 || resto de US3 após T023
- T029 || T030
- T033 || T034

---

## Parallel Example: After Foundational

```bash
# Em paralelo por pessoa/agente:
Task: "US1 — CI inventory + gap policy in docs/release/checklist-template.md"   # T009–T011
Task: "US3 — Write docs/release/min-flow.md + README section"                  # T023–T024
Task: "US4 — Open debt issues InvocationResult + Vite/npm audit"               # T029–T030
```

## Parallel Example: User Story 1

```bash
Task: "Gap policy rows in docs/release/checklist-template.md"          # T010
Task: "Version audit subsection in docs/release/checklist-template.md" # T011
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup  
2. Phase 2 Foundational (gitignore, bump, template, desktop CI)  
3. Phase 3 US1 (auditabilidade)  
4. **STOP**: validar template + `check-version.sh` + job CI presente  

### Incremental Delivery

1. MVP = US1 + foundation  
2. + US3 docs → onboarding  
3. + US4 debts → rastreio  
4. + US2 bump/changelog/checklist/tag → **marco de produto**  
5. Polish + human merge/tag  

### Suggested MVP scope

**T001–T013** (Setup + Foundational + US1): repositório auditável e CI desktop smoke sem ainda publicar tag.

### Full acceptance (issue #39)

Completar através de **T037**, com **T021** (tag) obrigatório para SC-003.

---

## Notes

- Não implementar features de domínio (FR-011) nem bump major Vite (FR-012)
- Não marcar PASS em SF-020 T024 / Desktop T033 sem `docs/validation` real
- Tag e merge: sempre gate humano (constituição P8)
- [P] = arquivos distintos e sem dependência de task incompleta
- Commit por task ou grupo lógico; PR draft permitido; merge/tag manuais
