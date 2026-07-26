# Tasks: STT UI — sessionId e profile no header do Streaming Foundation

**Input**: Design documents from `/specs/022-issue-51-stt-ui-header/`

**Prerequisites**: plan.md, spec.md (clarify + analyze remediação 2026-07-25: primary=most recent, URL MUST, FR-006 note, feed-only, política canônica Python), research.md, data-model.md, contracts/stt-dashboard-header.md, quickstart.md

**Tests**: Incluídos — SC-001–SC-006 / FR-001–FR-014 (FR-015 unificado em FR-004) e plan Testing: pytest de estrutura + `header_session_state` canônico (P10). SC-001/SC-004 e clipboard real no quickstart manual.

**FR note (analyze D1)**: Feedback de Copiar = **FR-004** (FR-015 reservado/retirado). Tasks que citavam FR-015 como feedback referem-se a FR-004.

**Organization**: Tasks grouped by user story (US1 → US2 → US3 → US4) after shared foundation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3 / US4 maps to spec user stories
- Paths are repo-relative from monorepo root

## Path Conventions

- STT UI: `services/transcription-service/app/static/index.html`
- State helper (recommended): `services/transcription-service/app/header_session_state.py` (pure Python policy mirror for tests)
- Tests: `services/transcription-service/tests/test_stt_dashboard_header.py`
- Docs: `docs/development/running.md`, `docs/release/min-flow.md`
- Feature docs: `specs/022-issue-51-stt-ui-header/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inventário e baseline; monorepo e transcription-service já existem.

- [x] T001 Review design docs in `specs/022-issue-51-stt-ui-header/` (spec FR-001–FR-014 + FR-015 reserved, clarify + analyze remediação, plan.md, research.md Decisions 1–9, data-model.md, contracts/stt-dashboard-header.md, quickstart.md) and list gaps vs current `services/transcription-service/app/static/index.html` header (title + `#status` only; `sessions` Set unused in UI)
- [x] T002 [P] Run baseline green: `PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests` (or a representative subset); record any pre-existing failures before changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pure session-header state policy + contract markers — bloqueia US1–US4.

**⚠️ CRITICAL**: Nenhuma user story de header completa sem esta fase.

- [x] T003 Create **canonical** pure policy module `services/transcription-service/app/header_session_state.py` (source of truth — analyze U1) implementing observe/primary/multi rules per `specs/022-issue-51-stt-ui-header/data-model.md`: empty → no primary; non-empty `sessionId` → set primary + add to observed; blank/whitespace ignored; multi when size > 1; `copy_enabled(primary)` helper; document that `index.html` JS must mirror this module
- [x] T004 [P] Unit tests for T003 in `services/transcription-service/tests/test_stt_dashboard_header.py` (or split `test_header_session_state.py`): empty, observe X, observe Y→primary Y + multi count, re-observe X→primary X, blank ignored (FR-009/FR-010/FR-014 foundation)
- [x] T005 [P] Structure skeleton: add header placeholder elements with stable markers from `specs/022-issue-51-stt-ui-header/contracts/stt-dashboard-header.md` to `services/transcription-service/app/static/index.html` (`session-id`, `session-copy`, multi, profile note, `stt-base-url`) without breaking existing `#status` / channel grid; assert markers exist in the same test file

**Checkpoint**: Foundation ready — pure state green; HTML markers present; existing channel feed still works.

---

## Phase 3: User Story 1 - Ver sessionId no header (Priority: P1) 🎯 MVP

**Goal**: Header shows full primary sessionId from transcript feed; empty state without inventing id; long ids layout-safe.

**Independent Test**: Fixture/event with sessionId X → header shows X; no events → waiting placeholder.

### Tests for User Story 1

- [x] T006 [P] [US1] Extend `services/transcription-service/tests/test_stt_dashboard_header.py`: assert empty-state placeholder semantics in HTML/script (no fabricated default id) and that script wires `data.sessionId` from feed into header update (FR-001/FR-009/FR-014 / SC-001 structure)
- [x] T007 [P] [US1] Extend tests for long-id CSS/layout hooks in `services/transcription-service/app/static/index.html` (word-break/overflow or mono class present for session-id region) (FR-008 / SC-003)

### Implementation for User Story 1

- [x] T008 [US1] Implement header session display in `services/transcription-service/app/static/index.html`: on transcript `onmessage`, **mirror** `header_session_state` rules (comment in script), set primary text to full id, multi `#session-multi` with count «N sessões» when ≥2 ids; empty → «aguardando sessão» (or equivalent); keep `#status`; **do not** clear observed set on `ws.onclose`/reconnect (A1)
- [x] T009 [US1] CSS in `services/transcription-service/app/static/index.html` for header meta row: long ids (wrap/break), no layout collapse vs status
- [x] T010 [US1] Run `PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests/test_stt_dashboard_header.py` until US1 structure/state asserts hold

**Checkpoint**: US1 — sessionId visível no header a partir do feed.

---

## Phase 4: User Story 2 - Copiar sessionId (Priority: P1) 🎯 MVP

**Goal**: Copy control writes exact primary to clipboard; disabled when empty; failure feedback without crash.

**Independent Test**: With primary X, copy targets X; empty → copy disabled; failure path sets failure feedback.

### Tests for User Story 2

- [x] T011 [P] [US2] Extend `services/transcription-service/tests/test_stt_dashboard_header.py`: copy control present; disabled/absent when no primary; script contains clipboard write of primary + success/failure feedback paths (**FR-003/FR-004** / SC-002; FR-015 unificado em FR-004)

### Implementation for User Story 2

- [x] T012 [US2] Wire copy control in `services/transcription-service/app/static/index.html`: `navigator.clipboard.writeText(primary)` when available; brief «copiado» / «falha ao copiar» feedback on control (~2s, FR-004); enable only when primary set; keep full id selectable on failure
- [x] T013 [US2] Ensure multi-session: copy always uses **primary** (most recent), not joined list (FR-010)
- [x] T014 [US2] Run pytest for header tests until SC-002 structure/behavior contracts hold

**Checkpoint**: US2 — Copiar primário com feedback. **MVP = US1+US2.**

---

## Phase 5: User Story 3 - Profile note / name (Priority: P2)

**Goal**: Profile region shows name if known without inventing; else agent-origin note; never on channel cards.

**Independent Test**: Default page shows note (no invented profile); channel sections lack session/profile session fields.

### Tests for User Story 3

- [x] T015 [P] [US3] Assert in `services/transcription-service/tests/test_stt_dashboard_header.py`: profile marker text includes agent/`--profile` note by default (**FR-006** path; no invented name); `ensureChannel` HTML template has no sessionId/profile session fields (FR-006–FR-007 / SC-005)

### Implementation for User Story 3

- [x] T016 [US3] Implement `#session-profile` (or data-testid) in `services/transcription-service/app/static/index.html` with **only** the agent-origin note (FR-006). **Do not** invent profile, parse query string, or hunt for a “non-schema source” in this slice (analyze U2; FR-005 MAY deferred with no source)
- [x] T017 [US3] Audit channel card markup in `services/transcription-service/app/static/index.html` remains free of session/profile session chrome (FR-007)
- [x] T018 [US3] Run header pytest until US3 asserts hold

**Checkpoint**: US3 — profile note; cards limpos.

---

## Phase 6: User Story 4 - URL base + docs (Priority: P3)

**Goal**: Header shows document origin; docs mention header sessionId + copy for agent/shell align.

**Independent Test**: stt-base-url marker present with origin wiring; docs searchable for Streaming Foundation header/sessionId.

### Tests for User Story 4

- [x] T019 [P] [US4] Assert `stt-base-url` marker and script sets origin (or equivalent) in `services/transcription-service/tests/test_stt_dashboard_header.py` (FR-011)

### Implementation for User Story 4

- [x] T020 [US4] Render STT base URL from `location.origin` in `services/transcription-service/app/static/index.html` header (no tokens/paths)
- [x] T021 [P] [US4] Update `docs/development/running.md` with short note: Streaming Foundation header shows sessionId in use; use Copiar to align agent `--session` / shell without PowerShell log (FR-012 / SC-006)
- [x] T022 [P] [US4] Update `docs/release/min-flow.md` with equivalent short operational note if not redundant with running.md (FR-012 / SC-006)
- [x] T023 [US4] Run full relevant pytest + spot-check docs grep for sessionId/header/Streaming Foundation

**Checkpoint**: US4 — URL + docs.

---

## Phase 7: Polish & Cross-Cutting

**Purpose**: Regression, privacy, quickstart alignment.

- [x] T024 [P] Confirm no transcript-event.v2 / schema changes in diff; no desktop-shell changes required for this feature
- [x] T025 [P] Privacy skim: header must not log or display raw audio/tokens/transcript text (P9)
- [x] T026 Run `PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests` and fix regressions
- [x] T027 Align `specs/022-issue-51-stt-ui-header/quickstart.md` if commands/paths drifted during implement

---

## Dependencies & Execution Order

```text
Phase 1 Setup
    ↓
Phase 2 Foundation (T003–T005)
    ↓
Phase 3 US1 (sessionId display) ──┐
    ↓                              │ MVP
Phase 4 US2 (copy) ───────────────┘
    ↓
Phase 5 US3 (profile note)
    ↓
Phase 6 US4 (URL + docs)
    ↓
Phase 7 Polish
```

- US2 depends on US1 primary display.
- US3/US4 can start after foundation markers exist; safest after US1 layout.
- Docs (T021/T022) parallelizable with code once behavior is stable.

## Parallel Opportunities

- T002 ∥ T001
- T004 ∥ T005 (after T003 API shape known)
- T006 ∥ T007
- T015 ∥ T019 after markers exist
- T021 ∥ T022 ∥ T024 ∥ T025

## Implementation Strategy

1. **MVP (code path)**: T001–T014 (foundation + US1 + US2) — operator sees and copies sessionId.
2. **Same PR / full issue #51**: US3 (profile **note**) + US4 (**URL base MUST** + docs) — low cost; not “optional URL”.
3. **Do not**: change transcript v2, shell select, agent auto-align, invent profile source.

## Independent Test Criteria (summary)

| Story | Independent test |
|-------|------------------|
| US1 | Feed event X → header primary X; empty → no invent; reconnect preserves observed |
| US2 | Copy enabled with X; targets exact X; disabled empty; FR-004 feedback |
| US3 | FR-006 note present; channel cards clean |
| US4 | Origin MUST in header; docs mention header/sessionId |

## Suggested MVP Scope

- **MVP mínimo**: US1 + US2 (Phases 1–4).
- **Entrega completa issue #51** (preferida na mesma PR): + US3 + US4. URL base is **MUST** (FR-011), not optional. Profile path is **note** (FR-006), not a new data source.
