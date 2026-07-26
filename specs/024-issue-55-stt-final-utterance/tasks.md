# Tasks: STT — `transcript.final.v2` ao fim de utterance (issue #55)

**Input**: Design documents from `/specs/024-issue-55-stt-final-utterance/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md  
**Tests**: Solicitados pela spec (FR-011, SC-002, SC-005) — incluir tarefas de teste  
**Branch**: `feature/issue-55-stt-emitir-transcript-final-v2-ao-fim-de-utteran`  
**Created**: 2026-07-25

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: parallelizable (different files, no incomplete deps)
- **[USn]**: user story label (setup/foundational/polish: no story label)

## Delivery map

| Plan delivery | Task phases | Stories |
|---------------|-------------|---------|
| **A — MVP** | 1 Setup, 2 Foundational, 3 US1, 4 US3 | US1, US3 |
| **B — Live-answer** | 5 US2 | US2 |
| **Docs** | 6 US4 | US4 |
| Polish | 7 | cross-cutting |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Alinhar paths e baseline verificável

- [x] T001 Confirm `.specify/feature.json` points to `specs/024-issue-55-stt-final-utterance` and branch matches issue #55
- [x] T002 [P] Inventory baseline: `services/transcription-service/app/main.py` (emit/final only on disconnect), `transcriber.py` (None on empty/same text), `config.py`, `contracts/transcript-event.v2.schema.json`
- [x] T003 [P] Run baseline STT tests: `PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests/test_ws_audio_contract.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Settings + pure state machine — base de US1–US3  
**⚠️ CRITICAL**: Nenhuma story de emissão começa sem o finalizer testável

- [x] T004 Add settings `finalization_idle_windows: int = 1` and `finalization_max_open_seconds: float = 45.0` with validation (≥1, >0) in `services/transcription-service/app/config.py`
- [x] T005 Implement pure `UtteranceFinalizer` (states idle/open, `on_text` / `on_no_result` / `on_tick` or max-open check / `on_disconnect`) per `data-model.md` in `services/transcription-service/app/utterance.py`
- [x] T006 [P] Unit tests for open→partials→idle close (exactly 1 final), second utterance, empty never finals, max-open force final, disconnect dedupe in `services/transcription-service/tests/test_utterance_finalizer.py`
- [x] T007 Run `PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests/test_utterance_finalizer.py` green

**Checkpoint**: State machine + settings ready; no WS wire yet

---

## Phase 3: User Story 1 — Fechar utterance e ver final (Priority: P1) 🎯 MVP

**Goal**: Após fala + idle de janela(s), publicar `transcript.final.v2` no feed STT/session path sem disconnect  
**Independent Test**: WS + fake engine: partials then no-text window → one final; events list includes final type  
**Maps**: FR-001, FR-002, FR-003, FR-005, FR-006, FR-007, SC-001, SC-004

### Tests

- [x] T008 [P] [US1] WS integration: scripted fake_engine sequence (text, text, None) yields partials then exactly one final; schema-valid final in `services/transcription-service/tests/test_ws_utterance_final.py`
- [x] T009 [P] [US1] WS integration: two utterance cycles → two finals in `services/transcription-service/tests/test_ws_utterance_final.py`
- [x] T010 [P] [US1] Regression: existing contract partial tests still pass in `services/transcription-service/tests/test_ws_audio_contract.py`

### Implementation

- [x] T011 [US1] Wire per-channel `UtteranceFinalizer` in audio WS handler in `services/transcription-service/app/main.py` (observe every window evaluation including None; emit partial/final via existing `emit` path)
- [x] T012 [US1] Ensure identity fields (sessionId, channelId, label, sourceType, device) on final match partials of same channel in `services/transcription-service/app/main.py`
- [x] T013 [US1] Preserve prosody-on-final path (023) when `final=True` in `services/transcription-service/app/main.py` without requiring prosody for close
- [x] T014 [US1] Apply echo-suppression rule R8: suppressed mic text does not call `on_text` in `services/transcription-service/app/main.py`
- [x] T015 [US1] Run full targeted pytest suite for US1 green

**Checkpoint**: SC-001 path automated; MVP emit works without disconnect

---

## Phase 4: User Story 3 — Um final por utterance / anti-spam (Priority: P2)

**Goal**: N partials → 0 finals until close; after close, no duplicate without new speech  
**Independent Test**: Unit + WS assert cardinality  
**Maps**: FR-004, FR-010, SC-002

### Tests

- [x] T016 [P] [US3] Unit: N partials same utterance → 0 finals until idle; then 1 final only in `services/transcription-service/tests/test_utterance_finalizer.py`
- [x] T017 [P] [US3] Unit/WS: disconnect after final already emitted does not double-final same residual in `services/transcription-service/tests/test_utterance_finalizer.py` and/or `test_ws_utterance_final.py`

### Implementation

- [x] T018 [US3] Harden disconnect flush path to use finalizer (no double final) in `services/transcription-service/app/main.py`
- [x] T019 [US3] Ensure max-open timeout path emits at most one final and resets state in `services/transcription-service/app/utterance.py` + wire tick/check in worker if needed in `main.py`
- [x] T020 [US3] Re-run anti-spam + disconnect tests green

**Checkpoint**: SC-002 enforced; FR-010 covered

---

## Phase 5: User Story 2 — Live-answer pode disparar após final (Priority: P1)

**Goal**: Confirmar que finais chegam ao session-core/feed e desbloqueiam o caminho do Assistente sem mudar 019 FR-003  
**Independent Test**: Fixture/manual: Final in session events; shell still ignores partials  
**Maps**: FR-007, FR-008, FR-009, SC-003

### Tests / validation

- [x] T021 [P] [US2] Confirm shell unit still rejects partials for auto-answer (no code change expected) via `cd apps/desktop-shell && npm test -- --run tests/assistant-auto.test.ts` (or existing partial rejection test)
- [x] T022 [P] [US2] If needed, add/adjust a minimal shell fixture test that a Final question entry is eligible (existing 019/023 tests may already cover) in `apps/desktop-shell/tests/`
- [x] T023 [US2] Document Manual B steps outcome expectations in `specs/024-issue-55-stt-final-utterance/quickstart.md` (align if drift after implement)
- [x] T024 [US2] Smoke: with fake or real stack, assert session events can include `transcript.final.v2` after idle (script or documented curl in quickstart) — no session-core code change unless ingest bug found

### Implementation (only if gap found)

- [x] T025 [US2] **Conditional**: fix session-core feed mapping only if finals are dropped (unlikely) under `services/session-core/` — **N/A** (feed already accepts `transcript.final.v2`)
- [x] T026 [US2] **MUST NOT** implement partial→live-answer or change question heuristic (FR-008/009) — shell auto tests green; no heuristic changes

**Checkpoint**: SC-003 path documented; 019 boundary preserved

---

## Phase 6: User Story 4 — Documentação operacional (Priority: P3)

**Goal**: running/min-flow/quickstart explicam final-on-utterance vs awaiting_final  
**Independent Test**: Grep docs; quickstart Manual A runnable  
**Maps**: FR-012, SC-006

- [x] T027 [P] [US4] Update `docs/development/running.md` Assistente section: STT emits final at end of utterance (idle); Assistente waits for Final not only disconnect
- [x] T028 [P] [US4] Cross-link note in `docs/release/min-flow.md` if appropriate (one sentence + link to running/quickstart)
- [x] T029 [US4] Finalize `specs/024-issue-55-stt-final-utterance/quickstart.md` automated + manual steps against actual setting names
- [x] T030 [US4] Ensure no secrets/transcript dumps in docs examples (P9)

**Checkpoint**: SC-006 satisfiable from docs alone

---

## Phase 7: Polish & Cross-Cutting

**Purpose**: Logging, regression, privacy, optional ops surface

- [x] T031 [P] Add INFO/DEBUG counters only (finals emitted, idle closes, max-open closes) without full text in `services/transcription-service/app/main.py` / `utterance.py` (FR-014)
- [x] T032 [P] Optional: expose finalization settings on STT `/health` in `services/transcription-service/app/main.py` (nice-to-have; skip if out of time)
- [x] T033 Run full transcription-service pytest: `PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests`
- [x] T034 [P] Update `specs/024-issue-55-stt-final-utterance/checklists/requirements.md` notes if status changes post-implement (optional)
- [x] T035 Execute quickstart automated section; record manual evidence path if E2E done (`docs/validation/` only if manual validation performed)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup** → no deps
- **Phase 2 Foundational** → after Setup; **blocks** US1–US3
- **Phase 3 US1** → after Foundational (MVP)
- **Phase 4 US3** → after US1 wire (shares main.py) — can extend tests in parallel with care
- **Phase 5 US2** → after US1 (needs finals emitted); shell tests [P] can run anytime
- **Phase 6 US4** → can start in parallel after plan; finish after US1 so docs match behavior
- **Phase 7 Polish** → after desired stories

### User Story Dependencies

| Story | Depends on | Independently testable? |
|-------|------------|-------------------------|
| US1 | Foundational | Yes — STT WS + unit |
| US3 | US1 wire | Yes — cardinality tests |
| US2 | US1 emit | Yes — shell fixtures + session events |
| US4 | Spec/plan; best after US1 | Yes — doc review |

### Parallel Opportunities

```text
# After Foundational:
T008, T009, T010 in parallel (test files)
# Docs anytime after clarify:
T027, T028 parallel
# Shell regression anytime:
T021 parallel with STT work
```

---

## Parallel Example: User Story 1

```bash
# Tests first (should fail before wire):
Task: T008 WS idle→final
Task: T009 two utterances
Task: T010 regression partials

# Then implement wire T011–T014, run T015
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 + 2  
2. Phase 3 US1  
3. **STOP**: pytest green; optional Manual A once  
4. Then US3 anti-spam, US4 docs, US2 confirmation  

### Incremental Delivery

1. Setup + Foundational → pure machine  
2. US1 → finals in conversation (MVP ship)  
3. US3 → hard guarantees anti-spam/disconnect  
4. US2 → live-answer path confidence  
5. US4 + polish → ops ready  

---

## Notes

- Prefer clock injection (`now` parameter) in `UtteranceFinalizer` for max-open tests.
- Do not change agent Windows code.
- Do not change schema v2 unless blocked (should not be).
- Schema contract tests should still validate finals.
- Commit after each logical group (foundational, US1, US3, docs).
