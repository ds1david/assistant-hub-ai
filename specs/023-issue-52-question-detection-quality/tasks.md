# Tasks: Qualidade de detecção de pergunta (issue #52)

**Input**: Design documents from `/specs/023-issue-52-question-detection-quality/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md  
**Tests**: Solicitados pela spec (FR-011, SC-001, SC-006) — incluir tarefas de teste nas stories afetadas  
**Branch**: `feature/issue-52-live-answer-qualidade-de-detec-o-de-pergunta-ent`  
**Updated**: 2026-07-25 (analyze remediation)

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: parallelizable (different files, no incomplete deps)
- **[USn]**: user story label (setup/foundational/polish: no story label)

## Delivery map (plan Phase A/B/C ≠ task Phase 1–9)

| Plan delivery | Task phases | Stories |
|---------------|-------------|---------|
| **A — MVP ship** | 1 Setup, 2 Foundational, 3 US1, 4 US2, 5 US3, 6 US6 (+ FR-012 polish slice) | US1, US2, US3, US6 |
| **B — STT ops** | 7 | US4 |
| **C — Prosódia** | 8 | US5 |
| Polish | 9 | cross-cutting |

**FR ID glossary** (avoid collision):

| ID | Meaning |
|----|---------|
| **019 FR-004** | Lexical legado em `specs/019-auto-answer-assistant` |
| **FR-002** | Lexical expandido (esta feature) |
| **FR-004** | Modo entrevista (esta feature) |
| **FR-006** | Gate multimodal OR |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Alinhar docs de feature e baseline verificável

- [x] T001 Confirm feature paths and `.specify/feature.json` → `specs/023-issue-52-question-detection-quality`
- [x] T002 [P] Inventory baseline: `apps/desktop-shell/src/assistant-auto.ts`, `assistant-prefs.ts`, `assistant-panel.ts`, `session-alignment.ts`, `contracts/transcript-event.v2.schema.json`, `config/whisper-hotwords.txt`, STT `/health`
- [x] T003 [P] Run baseline shell tests: `cd apps/desktop-shell && npm test -- --run tests/assistant-auto.test.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Preferências e gate unificado — base de US1–US6  
**⚠️ CRITICAL**: Stories que disparam automático dependem deste gate  
**API surface**: exportar `looksLikeQuestion` + `isQuestionCandidate` aqui (evita fase US6 duplicada)

- [x] T004 Extend `AssistantSessionPreferences` with `interviewMode`, `useProsody`, `prosodyThreshold` + defaults/normalize in `apps/desktop-shell/src/assistant-prefs.ts`
- [x] T005 [P] Unit tests for normalize/defaults of new prefs fields in `apps/desktop-shell/tests/assistant-prefs.test.ts`
- [x] T006 Persist new prefs fields through Tauri `get_assistant_prefs` / `set_assistant_prefs` (Rust types + save payload) under `apps/desktop-shell/src-tauri/`
- [x] T007 Implement pure `isQuestionCandidate(entry, prefs)` per FR-006 (lexical OR interview OR prosody) and export stable API (`looksLikeQuestion`, `isQuestionCandidate`) in `apps/desktop-shell/src/assistant-auto.ts`
- [x] T008 Wire `shouldAutoAnswerFromEntry` / `extractNewQuestions` to use `isQuestionCandidate` in `apps/desktop-shell/src/assistant-auto.ts` (and `session-alignment.ts` if it reimplements lexical — single source of truth)
- [x] T009 Unit tests for gate truth table (research.md) including `useProsody=false` ignores high score in `apps/desktop-shell/tests/assistant-auto.test.ts`

**Checkpoint**: Prefs + gate + exported API ready

---

## Phase 3: User Story 1 — Imperativos e vocativos disparam o Assistente (Priority: P1) 🎯 MVP

**Goal**: Frases de entrevista (*Me conte…*, *David, me descreva…*, *Em que…*) são lexical-questions e disparam com auto+system  
**Independent Test**: Vitest fixtures; manual quickstart Phase A without interview mode  
**Canonical source**: lista de prefixos em **spec FR-002** (código deve espelhar a spec, não o contrário)

### Tests

- [x] T010 [P] [US1] Complete FR-002 regression fixtures (session phrases + rejections `qualidade` / *vamos seguir*) in `apps/desktop-shell/tests/assistant-auto.test.ts`
- [x] T011 [P] [US1] Assert partials never candidate via gate in `apps/desktop-shell/tests/assistant-auto.test.ts`

### Implementation

- [x] T012 [US1] Align exported prefix lists / `looksLikeQuestion` with **spec FR-002** canonical list in `apps/desktop-shell/src/assistant-auto.ts` (gap-fill only; spec is source of truth)
- [x] T013 [US1] Add short “**019 FR-004** superseded in shell by 023 FR-002” note under Clarifications in `specs/019-auto-answer-assistant/spec.md`
- [x] T014 [US1] Run `npm test -- --run tests/assistant-auto.test.ts` green for US1

**Checkpoint**: SC-001 path automated; MVP lexical ready

---

## Phase 4: User Story 2 — Operador entende onde e por que não há resposta (Priority: P1)

**Goal**: Docs + empty states leave no doubt: answer is Assistente, not STT dashboard  
**Independent Test**: Grep docs for “Assistente” vs STT chat; empty states still show 019 copy (auto-off + generic elegibility only)

### Implementation

- [x] T015 [P] [US2] Document “Onde ver resposta do **modelo** / painel Assistente” (prefer product terms; avoid implying ChatGPT-only) and trigger checklist (origem, sessionId, Final) in `docs/development/running.md`
- [x] T016 [P] [US2] Cross-link min-flow or note if appropriate in `docs/release/min-flow.md`
- [x] T017 [US2] Confirm Phase A section of `specs/023-issue-52-question-detection-quality/quickstart.md` matches operator flow (edit if drift)
- [x] T018 [US2] Verify empty-state copy remains **auto-off + generic elegibility only** (no multi-reason UI for interview/prosody/mismatch) in `apps/desktop-shell/src/assistant-panel.ts` — adjust only if wording contradicts FR

**Checkpoint**: SC-005 documentable

---

## Phase 5: User Story 3 — Modo entrevista (Priority: P2)

**Goal**: `interviewMode` (FR-004 desta feature) makes Final system ≥ 8 candidate; mic not expanded  
**Independent Test**: Vitest interview fixtures; UI toggle visible

### Tests

- [x] T019 [P] [US3] Tests: interviewMode system long non-prefix → candidate; mic same text → not via interview; off → not in `apps/desktop-shell/tests/assistant-auto.test.ts`

### Implementation

- [x] T020 [US3] Ensure gate interview branch uses canonical `system` only and min length 8 in `apps/desktop-shell/src/assistant-auto.ts`
- [x] T021 [US3] Add “Modo entrevista” toggle (default off) to Assistente panel in `apps/desktop-shell/src/assistant-panel.ts`
- [x] T022 [US3] Panel render/interaction test for interview toggle in `apps/desktop-shell/tests/assistant-panel.test.ts`
- [x] T023 [US3] Persist toggle via existing prefs save path (verify round-trip with memory store + Tauri path)

**Checkpoint**: SC-003 satisfied for Phase A ship

---

## Phase 6: User Story 6 — Gate multimodal checkpoint (Priority: P2)

**Goal**: Confirm single pure gate owns eligibility (work mostly done in Foundational T007–T009)  
**Independent Test**: Truth-table tests already in T009

### Implementation

- [x] T024 [US6] Sanity: contract `specs/023-issue-52-question-detection-quality/contracts/question-detection.md` matches FR-006 OR formula and exported API from T007 (edit contract only if drift)
- [x] T025 [US6] Confirm no second lexical implementation remains in `apps/desktop-shell/src/session-alignment.ts` (delegates to `assistant-auto` or shared export)
- [x] T026 [P] [US6] [FR-012] Run session-alignment / active-session regression tests if present under `apps/desktop-shell/tests/` (e.g. tests covering session match); document “FR-012 inherited — green” in PR notes or skip with explicit path if no suite exists yet

**Checkpoint**: Gate is single source of truth; FR-012 regression touched

---

## Phase 7: User Story 4 — Qualidade de STT / hotwords (Priority: P2) — plan Phase B

**Goal**: Ops docs + interview hotwords sample; model default unchanged  
**Independent Test**: Doc checklist A/B + sample file committed; health shows model

### Implementation

- [x] T027 [P] [US4] Expand `config/whisper-hotwords.txt` with technical interview terms (Spring, REST, session-core, Kubernetes, …) without removing useful existing entries
- [x] T028 [P] [US4] Document modelo STT `WHISPER_MODEL=small|medium|large-v3`, VRAM/latency, recreate container, rollback in `docs/development/running.md` and comments in `.env.example` if present
- [x] T029 [US4] Confirm `/health` exposes `model` (already present) and document curl in `docs/development/running.md` referencing `services/transcription-service/app/main.py`
- [x] T030 [US4] Complete Phase B A/B section (3 fixed phrases) in `specs/023-issue-52-question-detection-quality/quickstart.md`

**Checkpoint**: ops path; no product default model change

---

## Phase 8: User Story 5 — Prosódia no Final (Priority: P3) — plan Phase C

**Goal**: Optional `prosody` on finals; **STT** extractor (not agent); shell prefs/UI useProsody; gate branch  
**Independent Test**: pytest synthetic fixture; vitest score≥T; event without prosody still valid

### Implementation (schema first)

- [x] T031 [US5] Add optional `prosody` object to `contracts/transcript-event.v2.schema.json` (in-place additive)
- [x] T032 [US5] Schema tests: final without prosody validates; with prosody validates; invalid score rejected — under existing schema test harness or new test next to contracts (depends on T031)
- [x] T033 [P] [US5] Settings `PROSODY_ENABLED` (default false), `PROSODY_END_WINDOW_MS` (default 500) in `services/transcription-service/app/config.py`
- [x] T034 [P] [US5] Implement prosody extractor module `services/transcription-service/app/prosody.py` (fail → omit; no PCM logs; **no agent path**)
- [x] T035 [US5] Attach `prosody` only on `transcript.final.v2` emission path in `services/transcription-service/app/` (transcriber/main pipeline)
- [x] T036 [US5] Health field `prosodyEnabled` in `services/transcription-service/app/main.py`
- [x] T037 [P] [US5] pytest extractor fixture (synthetic rising F0 / silence) in `services/transcription-service/tests/test_prosody.py`
- [x] T038 [US5] Type optional `prosody` on feed/transcript types in `apps/desktop-shell/src/api-client.ts` (or equivalent feed types)
- [x] T039 [P] [US5] Vitest: useProsody + score≥0.65 + non-lexical Final system → candidate in `apps/desktop-shell/tests/assistant-auto.test.ts`
- [x] T040 [US5] UI toggle `useProsody` in `apps/desktop-shell/src/assistant-panel.ts` (threshold remains store-only 0.65)
- [x] T041 [US5] Panel test for useProsody toggle in `apps/desktop-shell/tests/assistant-panel.test.ts`
- [x] T042 [US5] **NFR-002 MUST**: document prosody CPU budget from fixture timing **or** explicit “unmeasured; default off remains” note in `specs/023-issue-52-question-detection-quality/research.md` (and Phase C in quickstart.md)

**Checkpoint**: SC-004; Phase C optional for MVP ship

---

## Phase 9: Polish & Cross-Cutting

**Purpose**: Consistency, privacy, full suite, quickstart readiness

- [x] T043 [P] Grep repo for residual claims that prosody is extracted on Windows agent; fix any remaining docs (spec Problema already remediado)
- [x] T044 [P] Privacy pass: no PCM/token logging in new STT paths (`services/transcription-service/app/prosody.py` and callers)
- [x] T045 Run full shell related tests: `cd apps/desktop-shell && npm test -- --run tests/assistant-auto.test.ts tests/assistant-prefs.test.ts tests/assistant-panel.test.ts`
- [x] T046 Run STT unit tests for prosody when Phase C present: `PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests/test_prosody.py`
- [x] T047 Walk quickstart Phase A checklist manually (or document blockers in `docs/validation/`) for SC-002
- [x] T048 Update issue #52 task checkboxes / PR body with Phase A vs B vs C status

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (1)** → **Foundational (2)** → blocks story work that needs gate/prefs
- **US1 (3)** and **US2 (4)** after Foundational (US2 mostly docs — can parallel US1)
- **US3 (5)** needs Foundational prefs/gate
- **US6 (6)** thin checkpoint after US1/US3; includes FR-012 regression
- **US4 (7)** independent of shell gate — parallel anytime after Setup
- **US5 (8)** after Foundational; **T031 schema before T032 tests**; STT before shell types
- **Polish (9)** after desired stories

### User Story Dependencies

| Story | Depends on | Independently testable? |
|-------|------------|-------------------------|
| US1 | Foundational + looksLikeQuestion | Yes (vitest) |
| US2 | Docs only (minimal code) | Yes (doc review) |
| US3 | Foundational prefs/gate | Yes (vitest + UI) |
| US6 | Foundational gate | Yes (truth table + FR-012 tests) |
| US4 | None of shell stories | Yes (ops manual) |
| US5 | Foundational + schema T031 | Yes (pytest + vitest); optional for MVP |

### Parallel Opportunities

```text
# After Foundational:
US1 tests T010/T011 || US2 docs T015/T016 || US4 hotwords/docs T027/T028

# Phase C:
T031 schema → T032 schema tests
T033/T034 STT settings+extractor [P] → T035 attach → T036 health
T037 pytest [P] after T034
T038 shell types → T039 vitest [P] → T040/T041 UI
T042 NFR-002 note anytime during Phase C
```

---

## Parallel Example: Phase A MVP (US1 + US3 + US2)

```bash
# After T004–T009 complete:
# Dev A: T010–T014 (US1 lexical)
# Dev B: T019–T023 (US3 interview)
# Dev C: T015–T018 (US2 docs)
# Then: T024–T026 (US6 + FR-012)
```

---

## Implementation Strategy

### MVP First (plan Phase A)

1. Setup + Foundational (T001–T009)  
2. US1 lexical (T010–T014)  
3. US3 interview (T019–T023)  
4. US2 docs (T015–T018)  
5. US6 + FR-012 (T024–T026)  
6. **STOP**: ship/demo Phase A — SC-001…003, SC-005, SC-006  

### Incremental

7. US4 STT ops (T027–T030) — plan Phase B  
8. US5 prosody (T031–T042) — plan Phase C  
9. Polish (T043–T048)

### Definition of done (feature)

- [x] SC-001…SC-006 per spec  
- [x] Phase A mergeable without Phase C  
- [x] CI shell green without GPU  
- [x] FR-012 regression green or explicitly documented  
- [x] NFR-002 budget or “unmeasured; default off” note if Phase C ships  
- [x] No regression: auto default off; mic default off; partials never fire; no PCM logs  

---

## Notes

- Baseline lexical expansion already partially implemented — T012 is gap-fill; **spec FR-002 is canonical**.  
- Do not change product defaults: `autoEnabled=false`, `WHISPER_MODEL=small`, `PROSODY_ENABLED=false`.  
- Prefer small commits per task or logical group (US1, US3, US4, US5).  
- Analyze remediation 2026-07-25: I1/I2 fixed in spec; C1→T026; C2→T042 MUST; O1→T031 before T032 (no false [P] on schema tests); D1→US6 thinned into Foundational export.  

---

## Phase 10: Convergence

**Purpose**: Close gaps found by `/speckit-converge` (2026-07-25) against current codebase vs spec/plan/tasks.  
**Do not renumber prior tasks.**

- [x] T049 Wire `PROSODY_ENABLED` and `PROSODY_END_WINDOW_MS` from host `.env` into `infra/compose/docker-compose.yml` (and `docker-compose.gpu.yml` if it overrides env) for service `transcription`, default false/500 — per FR-008 / plan Phase C (`partial`: settings exist in STT but Compose does not pass env, so container never enables prosody via product `.env`)
- [x] T050 [P] Add Rust unit test that `transcript_feed_entries` maps HubEvent payload `prosody.questionScore` / `contour` / `f0EndSlopeSemitones` into `TranscriptFeedEntry.prosody` (and omits when absent) in `apps/desktop-shell/src-tauri/src/session_core_client.rs` — per FR-007 / US5 (`partial`: mapping code present, no dedicated test)
- [x] T051 [P] Add STT health assertion or small test that `/health` includes `prosodyEnabled` boolean (default false) covering `services/transcription-service/app/main.py` — per FR-008 / US5 AC health (`partial`: field implemented, not covered by service test)
- [x] T052 Record manual SC-002 quickstart Phase A evidence in `docs/validation/` (environment, commit, steps, result: ≥1 Assistente turn after eligible Final; resposta **not** on :8001) — per SC-002 / Constitution P10 (`missing`: no validation artifact; automated suite does not cover full E2E)
- [x] T053 [P] Update GitHub issue #52 checkboxes / status note to reflect implemented Phases A–C and remaining Convergence tasks T049–T052 — per plan polish / T048 residual (`partial`: issue body may still list open Phase A–C items)
