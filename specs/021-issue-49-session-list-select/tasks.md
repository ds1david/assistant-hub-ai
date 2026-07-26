# Tasks: Sessão — seleção na lista e alinhar agent ao sessionId ativo

**Input**: Design documents from `/specs/021-issue-49-session-list-select/`

**Prerequisites**: plan.md, spec.md (clarify orphan→null, no auto-select, in-memory), research.md, data-model.md, contracts/session-picker-shell.md, quickstart.md

**Tests**: Incluídos — FR-013 / SC-001–SC-005 e plan Testing exigem vitest (select, create→active, reconcile preserve/orphan, start id, guidance com active, mismatch regressão).

**Organization**: Tasks grouped by user story (US1 → US2 → US3 → US4) after shared foundation.

**FR ID note (analyze I1)**: Neste arquivo, **021 FR-xxx** refere `specs/021-issue-49-session-list-select/spec.md`. Quando for requisito da 020, escrever **020 FR-xxx** explicitamente. Em especial: **020 FR-009** = select **não** reinicia agent; **021 FR-009** = permitir **reiniciar** agent com sessão ativa; **021 FR-011** = mismatch + select não reinicia.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3 / US4 maps to spec user stories
- Paths are repo-relative from monorepo root

## Path Conventions

- Shell TS: `apps/desktop-shell/src/`, tests: `apps/desktop-shell/tests/`
- Docs: `docs/development/running.md`, `docs/release/min-flow.md`
- Feature docs: `specs/021-issue-49-session-list-select/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inventário e baseline; monorepo e shell já existem.

- [x] T001 Review design docs in `specs/021-issue-49-session-list-select/` (spec FR-001–FR-016 + clarify, plan.md, research.md Decisions 1–9, data-model.md, contracts/session-picker-shell.md, quickstart.md) and list gaps vs current `apps/desktop-shell/src/session-picker.ts`, `apps/desktop-shell/src/main.ts` (`selectSession` / `createAndSelectSession` / `refreshSessionList`), `apps/desktop-shell/src/agent-session-actions.ts`, `apps/desktop-shell/tests/session-picker.test.ts`
- [x] T002 [P] Run baseline green: `npx vitest run` in `apps/desktop-shell`; record any pre-existing failures before changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pure selection/reconcile helpers + contract testids — bloqueia US1–US3.

**⚠️ CRITICAL**: Nenhuma user story de seletor completa sem esta fase.

- [x] T003 Create pure module `apps/desktop-shell/src/session-selection.ts` exporting `reconcileActiveSessionAfterList(activeSessionId, sessions) -> string | null`, `isSelectableSessionId(id: string): boolean`, and `afterCreateSuccess(createdSessionId: string, selectSession: (id: string) => void | Promise<void>): void | Promise<void>` (create→active wiring testável: chama `selectSession(createdSessionId)` se `isSelectableSessionId`) per `specs/021-issue-49-session-list-select/data-model.md` and `contracts/session-picker-shell.md` (orphan → null; no auto-select; blank → not selectable)
- [x] T004 [P] Keep or re-export `onSessionSelected` from `apps/desktop-shell/src/agent-session-actions.ts` (or move to `session-selection.ts` with re-export) so selection **cannot** take agent stop/start in its signature (**020 FR-009** / **021 FR-011** — select ≠ restart agent; **não** confundir com **021 FR-009** restart CTA)
- [x] T005 [P] Unit tests for T003 in `apps/desktop-shell/tests/session-selection.test.ts`: preserve when id in list; orphan → null; null active stays null with non-empty list (no auto-select); blank id not selectable; `afterCreateSuccess` calls select with created id (FR-013b / SC-002 foundation)

**Checkpoint**: Foundation ready — pure reconcile/select/create helpers; vitest session-selection green.

---

## Phase 3: User Story 1 - Selecionar sessão na lista e ver sessão ativa (Priority: P1) 🎯 MVP

**Goal**: Clique no item define sessão ativa com id completo; UI sai de «Nenhuma sessão selecionada»; item selecionado marcado.

**Independent Test**: Lista com 1 item → select → active = id completo em `session-active-id`; troca S→T atualiza active e highlight.

### Tests for User Story 1

- [x] T006 [P] [US1] Extend `apps/desktop-shell/tests/session-picker.test.ts`: lista com 1 item + active null → click `session-item` chama `onSelect` com **id completo** (`data-session-id` não truncado); com view active setado, `session-active-id` contém UUID completo (021 FR-002 / FR-013a / SC-001)
- [x] T007 [P] [US1] Extend `apps/desktop-shell/tests/session-picker.test.ts` (or session-selection): two items S/T, active S → select T fires `onSelect(T)` and selected class only on T when re-rendered with active T

### Implementation for User Story 1

- [x] T008 [US1] Harden `apps/desktop-shell/src/session-picker.ts`: ensure each `session-item` uses full `data-session-id={s.id}`; `session-active-id` shows full id when active; selected class when `s.id === activeSessionId`; ignore select when `!isSelectableSessionId(id)`
- [x] T009 [US1] Wire `selectSession` in `apps/desktop-shell/src/main.ts` via `onSessionSelected` + `isSelectableSessionId`; after set active, paint picker/assistant/agent so UI leaves «Nenhuma sessão selecionada» (021 FR-004); MUST NOT call agent stop/start (**020 FR-009** / **021 FR-011**)
- [x] T010 [US1] Run `npx vitest run tests/session-picker.test.ts tests/session-selection.test.ts tests/agent-session-actions.test.ts` in `apps/desktop-shell` until SC-001 holds

**Checkpoint**: US1 — select gruda active com id completo; select ≠ restart agent.

---

## Phase 4: User Story 2 - Criar sessão e torná-la ativa automaticamente (Priority: P1) 🎯 MVP

**Goal**: Create success → active = created.id; create fail → erro legível sem active inventado; refresh preserve/orphan com paint.

**Independent Test**: create fake success → active id; refresh with id present preserves; refresh without id clears to null and UI shows «Nenhuma sessão selecionada».

### Tests for User Story 2

- [x] T011 [P] [US2] Tests in `apps/desktop-shell/tests/session-selection.test.ts` (or `session-lifecycle.test.ts`): (1) `afterCreateSuccess("new-uuid", selectFn)` → `selectFn` called with `"new-uuid"`; (2) blank/invalid created id → select **not** called / no invent (021 FR-005 / FR-013b / SC-002). Prefer exported pure helper from T003 — **não** só “simular mentalmente” o create.
- [x] T012 [P] [US2] Tests for refresh reconcile: preserve when still listed; orphan → null (021 FR-013c–d / SC-003) via `reconcileActiveSessionAfterList`; assert contract that `refreshSessionList` **must** apply reconcile on success

### Implementation for User Story 2

- [x] T013 [US2] Update `refreshSessionList` in `apps/desktop-shell/src/main.ts`: on **successful** list, set `activeSessionId = reconcileActiveSessionAfterList(activeSessionId, sessionList)` then **paint** session picker + assistant + agent (inclui caso orphan → `null` reexibindo «Nenhuma sessão selecionada» e reaplicando bloqueios FR-003); on list **failure**, set error, do **not** invent sessions, **keep prior active** + show error (data-model refresh_fail — **sem** alternativa “product chooses clear”)
- [x] T014 [US2] Update `createAndSelectSession` in `apps/desktop-shell/src/main.ts`: on success call `afterCreateSuccess(session.id, selectSession)` (or `selectSession(session.id)`) so create→active without second click (021 FR-005); on failure set `sessionListError`, do not invent active
- [x] T015 [US2] Run `npx vitest run tests/session-picker.test.ts tests/session-selection.test.ts` (e lifecycle se criado) until SC-002/SC-003 hold

**Checkpoint**: US2 — create→active; refresh preserve/orphan + paint.

---

## Phase 5: User Story 3 - Iniciar/reiniciar agent com sessão ativa (Priority: P1) 🎯 MVP (mesma entrega)

**Goal**: Start/restart/guidance usam active UUID; sem active bloqueia; mismatch se agent ≠ active (reuso 020). **Obrigatório na mesma PR/entrega que US1+US2** (analyze item 4 / issue #49 ponta a ponta).

**Independent Test**: Fake start receives active id; no active → no start; guidance contains `--session <active>`; mismatch banner when ids differ.

### Tests for User Story 3

- [x] T016 [P] [US3] Regression in `apps/desktop-shell/tests/agent-panel.test.ts` and/or `agent-session-actions.test.ts`: start path with active `S` passes `S`; no active blocks start; restart Direct uses active (**021 FR-008 / FR-009 / FR-010** / FR-013e / SC-004)
- [x] T017 [P] [US3] **021 FR-012**: assert em `apps/desktop-shell/tests/agent-panel.test.ts` (ou helper `withActiveGuidance`): com `activeSessionId = S`, o comando guiado / `guidanceCommand` / texto `agent-guidance` **contém** `--session S` (UUID completo da sessão ativa)
- [x] T018 [P] [US3] Regression mismatch: active UUID vs agent `session-YYYYMMDD-…` (or other id) shows `session-mismatch-banner` (**021 FR-011** / FR-013f / SC-005)

### Implementation for User Story 3

- [x] T019 [US3] In `apps/desktop-shell/src/main.ts` start/restart handlers: always pass current `activeSessionId` to `startAgent` / `restartAgentWithActiveSession`; never generate `session-YYYYMMDD-…` for UI-managed start; paint guidance with active id via `withActiveGuidance` (020). **Se audit encontrar gap, implementar o fix na mesma task** — não fechar só com “confirmado mentalmente”
- [x] T020 [US3] Confirm + assert: select path still does not restart agent (`onSessionSelected` only / **020 FR-009** / **021 FR-011**) when switching sessions with agent running — mismatch surfaces via 020 paint; keep `agent-session-actions` test that select does not call stop/start
- [x] T021 [US3] Run `npx vitest run tests/agent-panel.test.ts tests/agent-session-actions.test.ts tests/session-alignment.test.ts tests/session-selection.test.ts` until SC-004/SC-005 **and** FR-012 guidance assert hold

**Checkpoint**: US3 — agent id alinhado ao picker; guidance com active; regressão 020 verde. **MVP incompleto sem este checkpoint.**

---

## Phase 6: User Story 4 - Documentação list-sessions vs agent path id (Priority: P2)

**Goal**: Docs operacionais cobrem mesmo sessionId, list-sessions = core only, `session-YYYYMMDD` não lista sozinho, select ≠ reconfig agent.

**Independent Test**: Revisor encontra regras em &lt;2 min (SC-006) em `running.md` e/ou `min-flow.md`.

### Implementation for User Story 4

- [x] T022 [P] [US4] Update `docs/development/running.md`: list-sessions only session-core; agent-only `session-YYYYMMDD-…` does not appear alone; same sessionId UI↔agent↔STT; select does not reconfigure running agent; prefer UI start/restart with active UUID (021 FR-014)
- [x] T023 [P] [US4] Update `docs/release/min-flow.md` with the same rules (cross-link `running.md` if appropriate)
- [x] T024 [US4] Cross-check wording against `specs/021-issue-49-session-list-select/quickstart.md` manual pass criteria; adjust quickstart only if doc paths/steps diverge

**Checkpoint**: US4 — docs acionáveis (SC-006).

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Suite completa, privacidade, testids, out of scope.

- [x] T025 Run full shell verification: `npx vitest run` in `apps/desktop-shell`; fix regressions in session picker/selection/agent tests
- [x] T026 [P] Audit logs/UI: no secrets, raw audio, or full model output in changed files under `apps/desktop-shell/` (021 FR-016 / P9)
- [x] T027 [P] Verify testids in `specs/021-issue-49-session-list-select/contracts/session-picker-shell.md` match implementation (`session-active-id`, `session-item`, `data-session-id`, `session-create`, `session-refresh`) and agent guidance testid used by T017
- [x] T028 Confirm 021 FR-015: no edits to `contracts/transcript-event.v2.schema.json`; no injection of STT-only ids into list-sessions client
- [x] T029 Final pass of `specs/021-issue-49-session-list-select/quickstart.md` automated section; mark Windows-only rows as manual

---

## Dependencies & Execution Order

### Story completion order

```text
Phase 1 Setup
    ↓
Phase 2 Foundational (reconcile / selectable / afterCreateSuccess)
    ↓
Phase 3 US1 Select  ──┐
    ↓                 ├── can partially parallel after foundation
Phase 4 US2 Create/refresh ──┘
    ↓
Phase 5 US3 Agent  ← MVP obrigatório (mesma entrega US1+US2)
    ↓
Phase 6 US4 Docs [P]
    ↓
Phase 7 Polish
```

### Parallel opportunities

- T002 ∥ T001 after review starts  
- T004 ∥ T005 after T003 API shape known  
- T006 ∥ T007 (tests) before/with T008  
- T011 ∥ T012  
- T016 ∥ T017 ∥ T018  
- T022 ∥ T023  

### Independent test criteria (per story)

| Story | Independent test |
|-------|------------------|
| US1 | Select 1 item → full active id; UI not “none selected” |
| US2 | Create → active; reconcile preserve/orphan + paint |
| US3 | Start fake gets active; guidance has `--session` active; mismatch banner fakes |
| US4 | Docs locate rules &lt;2 min |

### MVP scope (pós-analyze)

**MVP = Phase 1–5 (US1 + US2 + US3)**: seleção confiável + create→active + refresh/orphan + agent start/restart/guidance/mismatch na **mesma entrega**. US4 docs + Phase 7 polish fecham a issue #49 para PR.

### Format validation

All tasks use `- [ ] Tnnn ...` with sequential IDs **T001–T029**, file paths; story phases include `[USn]`; setup/foundation/polish omit story labels; `[P]` only when parallel-safe.
