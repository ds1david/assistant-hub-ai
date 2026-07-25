# Tasks: Débito frontend — auditoria de dependências e decisão Vite (issue #41)

**Input**: Design documents from `/specs/018-issue-41-frontend-npm-audit/`

**Prerequisites**: plan.md, spec.md (clarifications Q1–Q5), research.md, data-model.md, contracts/dependency-audit-evidence.md, quickstart.md

**Tests**: Não há suíte de domínio nova. DoD usa scripts já existentes do shell (`npm test`, `npm run build`, `npm run lint`) + `npm audit` / reauditoria (FR-008, SC-003, quickstart).

**Organization**: Setup → Foundational (artefato + baseline env) → US1 inventário → US2 upgrade/decisão → US3 verificação → Polish.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3 maps to spec user stories
- Paths are repo-relative from monorepo root

## Path Conventions

- Desktop package: `apps/desktop-shell/`
- Evidence: `docs/validation/issue-41-frontend-npm-audit.md`
- Feature docs: `specs/018-issue-41-frontend-npm-audit/`
- CI: `.github/workflows/ci.yml` (job `desktop-shell-smoke`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar contexto e ambiente; monorepo e app já existem.

- [x] T001 Review design docs in `specs/018-issue-41-frontend-npm-audit/` (spec clarifications Q1–Q5, plan.md, research.md Decisions 1–7, data-model.md, contracts/dependency-audit-evidence.md, quickstart.md) and note current pins in `apps/desktop-shell/package.json` + `apps/desktop-shell/package-lock.json`
- [x] T002 [P] Confirm Node toolchain in WSL (`node -v`, prefer Node 22 to match CI) and that `apps/desktop-shell/package.json` scripts `test`, `build`, and `lint` exist as DoD entry points

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Artefato canônico esqueleto + dependências instaláveis antes de inventário e upgrades.

**⚠️ CRITICAL**: Nenhuma user story completa sem esta fase.

- [x] T003 Create evidence skeleton `docs/validation/issue-41-frontend-npm-audit.md` with required section headings from `specs/018-issue-41-frontend-npm-audit/contracts/dependency-audit-evidence.md` (Header, Baseline, Disposition, Reaudit, Verification, Residual, Close readiness) and fill Header (feature dir, issue #41, environment placeholders, **branch note**: “no-major-bump” = política da tag #39; esta fatia prefere upgrade major quando limpar o audit — spec Q1 / I1)
- [x] T004 Run `npm ci` in `apps/desktop-shell` so lockfile-resolved tree matches CI and is ready for audit/upgrade work

**Checkpoint**: Evidence file exists; `apps/desktop-shell` installable via `npm ci`.

---

## Phase 3: User Story 1 - Inventariar e entender o risco (Priority: P1) 🎯 MVP

**Goal**: Inventário reproduzível da baseline (severidade, major necessário, runtime vs dev/CI) no artefato canônico.

**Independent Test**: Revisor lê só `docs/validation/issue-41-frontend-npm-audit.md` § Baseline e lista cada finding com severity + role + fixRequiresMajor, sem reexecutar investigação ad hoc (SC-001 parcial).

### Implementation for User Story 1

- [x] T005 [US1] Run `npm audit` and `npm audit --omit=dev` in `apps/desktop-shell`; capture severity counts, commit SHA (`git rev-parse --short HEAD`), and Node version into `docs/validation/issue-41-frontend-npm-audit.md` § Baseline
- [x] T006 [US1] Fill findings table in `docs/validation/issue-41-frontend-npm-audit.md` § Baseline per `specs/018-issue-41-frontend-npm-audit/data-model.md` entity `DependencyFinding` (packageName, severity, isDirect, role, fixRequiresMajor, fixAvailableVersion, notes/advisory); if role is ambiguous use `both`
- [x] T007 [US1] Explicitly record `prodOnlyClean` from `npm audit --omit=dev` and classify each finding as `dev_ci`, `runtime_packaged`, or `both` in `docs/validation/issue-41-frontend-npm-audit.md` § Baseline. For `both` or unknown, treat high/critical with the **runtime** close bar (FR-013): residual must not close the issue until reclassified to pure `dev_ci` with evidence or upgraded

**Checkpoint**: US1 done — baseline complete and reviewable in the canonical file.

---

## Phase 4: User Story 2 - Decidir e executar upgrade ou mitigação (Priority: P1)

**Goal**: Prefer major toolchain upgrades to clear the audit cluster; document disposition for 100% of baseline findings; reaudit.

**Independent Test**: Disposition section covers every baseline finding/family; package.json/lockfile match upgrades; reaudit section matches final state; residual only if inviability documented (SC-002, SC-005, FR-004–FR-007).

### Implementation for User Story 2

- [x] T008 [US2] Bump toolchain versions in `apps/desktop-shell/package.json` per research Decision 2 (Vite major to clear advisories, Vitest major aligned to Vite peer, ESLint major if needed for minimatch/brace-expansion); keep `@tauri-apps/api` unless peer conflict; **do not** use `npm audit fix --force`
- [x] T009 [US2] Run `npm install` in `apps/desktop-shell` to refresh `apps/desktop-shell/package-lock.json` for the new pins
- [x] T010 [US2] Apply minimal config adaptations only if required by majors in `apps/desktop-shell/vite.config.ts` and/or `apps/desktop-shell/eslint.config.js` (and `apps/desktop-shell/tsconfig.json` only if forced); preserve Tauri dev conventions (`clearScreen: false`, port `5173`, `strictPort`, `outDir: dist`) documented in research Decision 2
- [x] T011 [US2] Apply inviability rule (spec Assumptions): one documented major attempt (T008–T010). If `npm test` / `npm run build` / `npm run lint` still fail without domain/UI changes, revert or pin viable versions in `apps/desktop-shell/package.json` + lockfile and prepare residual justification for evidence (FR-006); otherwise keep upgraded pins
- [x] T012 [US2] Fill Disposition table in `docs/validation/issue-41-frontend-npm-audit.md` § Disposition for 100% of baseline findings/families (`upgraded` with from→to versions, or `residual_accepted` with inviability evidence) — FR-004, SC-002
- [x] T013 [US2] Run post-change `npm audit` and `npm audit --omit=dev` in `apps/desktop-shell` and write § Reaudit in `docs/validation/issue-41-frontend-npm-audit.md` (counts + remaining list)
- [x] T014 [US2] If any residual remains, fill § Residual in `docs/validation/issue-41-frontend-npm-audit.md` with role=`dev_ci`, mitigation, and both FR-014 triggers (`reevalNextProductRelease`, `reevalOnRiskIncrease`); **block close** if any residual is `runtime_packaged` + high/critical (FR-013, SC-007, SC-008)

**Checkpoint**: US2 done — decision + lockfile/manifest reflect upgrade or documented residual; reaudit recorded.

---

## Phase 5: User Story 3 - Manter shell desktop verificável (Priority: P1)

**Goal**: test + build + lint verdes; CI desktop-shell-smoke verde; evidência de verificação no artefato.

**Independent Test**: Commands in quickstart §3 pass; CI job green if present; § Verification filled (SC-003, SC-004, FR-008, FR-009).

### Implementation for User Story 3

- [x] T015 [US3] Run `npm test` in `apps/desktop-shell` until exit 0; fix only minimal breakage from toolchain upgrade (no domain features) under `apps/desktop-shell/src/` and `apps/desktop-shell/tests/` if needed
- [x] T016 [US3] Run `npm run build` in `apps/desktop-shell` until exit 0; fix minimal config/source issues if the major toolchain requires it
- [x] T017 [US3] Run `npm run lint` in `apps/desktop-shell` until exit 0; adjust `apps/desktop-shell/eslint.config.js` or sources only as required by ESLint major
- [x] T018 [US3] Record Verification results (test/build/lint + reaudit summary + commit SHA) in `docs/validation/issue-41-frontend-npm-audit.md` § Verification per contract
- [x] T019 [US3] Optionally add `npm run lint` to the frontend step of job `desktop-shell-smoke` in `.github/workflows/ci.yml` (research Decision 4 recommended); ensure the job still runs `npm ci`, `npm test`, `npm run build` — **do this before treating CI as final green**
- [x] T020 [US3] After T019 decision (lint added or explicitly skipped), confirm CI path: push/PR then `desktop-shell-smoke` green; if validating only locally, note “CI pending push” in evidence and keep local DoD complete — never treat missing CI as PASS inventado (FR-009). Depends on T015–T018; depends on T019 if lint was added to the job
- [x] T021 [P] [US3] Optionally run `cargo test` in `apps/desktop-shell/src-tauri` if Rust toolchain available; record pass/skip in evidence § Verification (CI already covers this job step)

**Checkpoint**: US3 done — local DoD green; evidence verification complete; CI green or status explicit.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Tracking de débito, close readiness, validação quickstart ponta a ponta.

- [x] T022 [P] Update `CHANGELOG.md` with a short note that issue #41 frontend dependency audit debt was addressed (upgrade and/or residual decision + link to `docs/validation/issue-41-frontend-npm-audit.md`)
- [x] T023 [P] Update release debt tracking for `frontend-vite-audit` in `docs/release/checklist-0.2.0.md` and/or `CHANGELOG.md` / related release notes so the item no longer reads as open “won’t major this tag” without the #41 outcome
- [x] T024 Complete Close readiness checklist in `docs/validation/issue-41-frontend-npm-audit.md` (SC-003, SC-005, SC-006, SC-007, SC-008) and ensure PR description links the canonical evidence path (FR-001, FR-012) and states: branch name is historical (no Vite major in product tag #39); this PR may major-bump Vite/Vitest/ESLint per #41
- [x] T025 Run end-to-end validation path from `specs/018-issue-41-frontend-npm-audit/quickstart.md` (baseline already done; re-run test/build/lint/audit once on final pins) and fix any gaps before handoff
- [x] T026 Human-only handoff: do **not** auto-merge or auto-close GitHub issue #41 (P8); leave PR ready for review with evidence link

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: starts immediately
- **Phase 2 Foundational**: depends on Setup — **blocks** US1–US3
- **Phase 3 US1**: depends on Foundational — inventário before decisions
- **Phase 4 US2**: depends on US1 baseline (need findings to dispose)
- **Phase 5 US3**: depends on US2 pins/config (verify after change); can re-run after residual-only path too
- **Phase 6 Polish**: depends on US1–US3 evidence complete

### User Story Dependencies

| Story | Depends on | Independently testable deliverable |
|-------|------------|--------------------------------------|
| US1 | Phase 2 | Baseline section complete in evidence file |
| US2 | US1 | Disposition + reaudit + package pins |
| US3 | US2 | test/build/lint green + verification section |

### Parallel Opportunities

- T001 ∥ T002 (setup)
- Within US2: config fix files may iterate, but package.json bump (T008) before install (T009)
- T019 before T020 when lint is added to CI (T019 is not parallel with T020)
- T021 optional cargo after local green (independent of T019/T020)
- T022 ∥ T023 (changelog vs release checklist)

---

## Parallel Example: After Foundational

```bash
# US1 sequential (same evidence file):
Task: T005 capture audit commands into docs/validation/issue-41-frontend-npm-audit.md
Task: T006 findings table
Task: T007 role classification

# After US2 pins stable, verification can be sequential commands:
cd apps/desktop-shell && npm test && npm run build && npm run lint && npm audit
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1–2  
2. Phase 3 US1 → **STOP**: baseline inventário revisável  
3. Demo: revisor lê só o artefato e entende o risco  

### Incremental Delivery (recommended full close)

1. US1 inventário  
2. US2 upgrade preferido + reaudit  
3. US3 test/build/lint + CI  
4. Polish tracking + PR  

### Suggested full-slice order (single implementer)

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → (T011 if needed) → T012 → T013 → T014 → T015 → T016 → T017 → T018 → T019 → T020 → T021 → T022 → T023 → T024 → T025 → T026

---

## Notes

- Prefer major toolchain clean-up (Q1); residual only for **dev/CI** with FR-014 (Q2, Q5)
- Canonical evidence path is fixed: `docs/validation/issue-41-frontend-npm-audit.md` (Q3)
- Mandatory local checks: test + build + lint (Q4)
- No domain features; no `npm audit fix --force`; no auto close issue
- Commit after US1 baseline, after US2 lockfile, after US3 green — small reviewable commits preferred
