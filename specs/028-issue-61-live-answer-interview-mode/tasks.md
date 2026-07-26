# Tasks: Live-answer — modo entrevista (contexto mic+system, 1ª pessoa, latência)

**Input**: Design documents from `/specs/028-issue-61-live-answer-interview-mode/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md  
**Tests**: Solicitados pela spec (FR-012, FR-019, SC-001–009) — incluir tarefas de teste nas stories  
**Branch**: `feature/issue-61-live-answer-modo-entrevista-contexto-mic-system`  
**Issue**: [#61](https://github.com/ds1david/assistant-hub-ai/issues/61)

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: parallelizable (different files, no incomplete deps)
- **[USn]**: user story label (setup/foundational/polish: no story label)

## Delivery map

| Plan delivery | Task phases | Stories |
|---------------|-------------|---------|
| **A — MVP** | 1 Setup, 2 Foundational, 3 US1, 4 US3 | US1, US3 |
| **B — Estilo** | 5 | US2 |
| **C — Docs/latência** | 6 | US4 |
| Polish | 7 | cross-cutting |

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar paths e baseline verde

- [x] T001 Confirm `.specify/feature.json` → `specs/028-issue-61-live-answer-interview-mode` and branch `feature/issue-61-live-answer-modo-entrevista-contexto-mic-system`
- [x] T002 [P] Inventory current code: `apps/desktop-shell/src/assistant-auto.ts` (`buildInvokeInput`, `recentFinals`), `assistant-prefs.ts`, `assistant-panel.ts`, `main.ts`, `src-tauri/src/assistant_prefs.rs`
- [x] T003 [P] Run baseline shell tests: `cd apps/desktop-shell && npm test -- --run tests/assistant-auto.test.ts tests/assistant-prefs.test.ts tests/assistant-panel.test.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Preferência `includeMicrophoneInContext` + buffer com `sourceType` — base de US1–US4  
**⚠️ CRITICAL**: Builder e UI dependem deste shape

- [x] T004 Extend `AssistantSessionPreferences` with `includeMicrophoneInContext: boolean` default **true** + `clonePrefs` / `normalizePrefs` (missing → true) in `apps/desktop-shell/src/assistant-prefs.ts`
- [x] T005 [P] Unit tests for default true / explicit false / isolation helpers in `apps/desktop-shell/tests/assistant-prefs.test.ts`
- [x] T006 Persist field through Tauri `AssistantSessionPreferences` + serde default true in `apps/desktop-shell/src-tauri/src/assistant_prefs.rs` (and save payload in `apps/desktop-shell/src/assistant-prefs.ts` `savePrefs`)
- [x] T007 Extend `recentFinals` / `trackFinal` to store `sourceType: CanonicalSourceType | null` via `normalizeSourceType` in `apps/desktop-shell/src/assistant-auto.ts`
- [x] T008 Update any prefs cloning in `apps/desktop-shell/src/session-alignment.ts` / `main.ts` view mapping to include the new field (compile-safe)

**Checkpoint**: Prefs + buffer shape ready; existing tests may need temporary type fixes before US1 asserts

---

## Phase 3: User Story 1 — Contexto inclui respostas do mic (Priority: P1) 🎯 MVP

**Goal**: `buildInvokeInput` includes labeled system+mic finals when preferência ON; exclude mic when OFF; question-only unchanged; no trigger change  
**Independent Test**: Vitest fixtures mixed finals → input asserts; mic Final with default origins does not start turn

### Tests

- [x] T009 [P] [US1] Tests: mixed finals + include mic ON → input contains mic text, system text, labels `Entrevistador:` and `Candidato (eu):` in `apps/desktop-shell/tests/assistant-auto.test.ts`
- [x] T010 [P] [US1] Tests: include mic OFF → no microphone text in context block in `apps/desktop-shell/tests/assistant-auto.test.ts`
- [x] T011 [P] [US1] Tests: question-only ignores context + include-mic flag in `apps/desktop-shell/tests/assistant-auto.test.ts`
- [x] T012 [P] [US1] Tests: unknown/null sourceType omitted from context in `apps/desktop-shell/tests/assistant-auto.test.ts`
- [x] T013 [P] [US1] Tests: Final microphone-only with default `enabledSourceTypes=["system"]` does **not** create turn in `apps/desktop-shell/tests/assistant-auto.test.ts`

### Implementation

- [x] T014 [US1] Implement labeled, filtered `buildInvokeInput` per `contracts/interview-live-answer.md` (pass `includeMicrophoneInContext`, filter origins, labels, 12/4000 window) in `apps/desktop-shell/src/assistant-auto.ts`
- [x] T015 [US1] Wire `startTurn` / controller to pass `prefs.includeMicrophoneInContext` into builder in `apps/desktop-shell/src/assistant-auto.ts`
- [x] T016 [US1] Export label constants for tests (`CONTEXT_LABEL_SYSTEM`, `CONTEXT_LABEL_MICROPHONE` or equivalent) in `apps/desktop-shell/src/assistant-auto.ts`
- [x] T017 [US1] Run `npm test -- --run tests/assistant-auto.test.ts` green for US1

**Checkpoint**: SC-001, SC-002, SC-003 path automated

---

## Phase 4: User Story 3 — Preferência “Incluir minha voz no contexto” (Priority: P2)

**Goal**: UI toggle explícito, persistência por sessão, default ON  
**Independent Test**: Panel checkbox + prefs store isolation tests

### Tests

- [x] T018 [P] [US3] Panel renders checkbox `data-testid="assistant-include-mic-context"` reflecting prefs in `apps/desktop-shell/tests/assistant-panel.test.ts`
- [x] T019 [P] [US3] Prefs isolation S/T for `includeMicrophoneInContext` in `apps/desktop-shell/tests/assistant-prefs.test.ts` (if not fully covered in T005)

### Implementation

- [x] T020 [US3] Add checkbox “Incluir minha voz no contexto” in `apps/desktop-shell/src/assistant-panel.ts` (disabled when controls disabled)
- [x] T021 [US3] Wire toggle → `savePrefs` + controller `setPrefs` in `apps/desktop-shell/src/main.ts`
- [x] T022 [US3] Ensure default view prefs use `includeMicrophoneInContext: true` in panel fallbacks (`assistant-panel.ts` defaults object)
- [x] T023 [US3] Run panel + prefs tests green

**Checkpoint**: SC-008 path automated; US3 demonstrable in UI

---

## Phase 5: User Story 2 — Resposta 1ª pessoa (Priority: P1)

**Goal**: Com `interviewMode` ON, prefixar instrução fixa; detector de estilo para fixtures; sem reject runtime  
**Independent Test**: Vitest instruction presence + `hasMetaAssistantStyle` fixtures

### Tests

- [x] T024 [P] [US2] Tests: `interviewMode=true` → built input starts with / contains instruction block; `false` → absent in `apps/desktop-shell/tests/assistant-auto.test.ts`
- [x] T025 [P] [US2] Tests: `hasMetaAssistantStyle` detects FR-012 bad fixtures and accepts good 1st-person fixtures in `apps/desktop-shell/tests/assistant-auto.test.ts`

### Implementation

- [x] T026 [US2] Add exported `INTERVIEW_ANSWER_INSTRUCTION` constant covering FR-009–011 in `apps/desktop-shell/src/assistant-auto.ts` (or small `interview-style.ts` if preferred)
- [x] T027 [US2] Prefix instruction in `buildInvokeInput` (or wrapper used by `startTurn`) when `prefs.interviewMode` in `apps/desktop-shell/src/assistant-auto.ts`
- [x] T028 [US2] Implement pure `hasMetaAssistantStyle(text)` for FR-012 patterns (runtime **not** used to drop answers) in `apps/desktop-shell/src/assistant-auto.ts`
- [x] T029 [US2] Confirm `startTurn` still assigns `result.output` as-is (FR-012b) in `apps/desktop-shell/src/assistant-auto.ts`
- [x] T030 [US2] Run assistant-auto tests green for US2

**Checkpoint**: SC-004 automated

---

## Phase 6: User Story 4 — Latência docs e não-regressão (Priority: P2)

**Goal**: Docs disparo vs contexto, elos de latência, knobs entrevista; partial never fires; latencyMs still shown  
**Independent Test**: Grep/docs review + vitest partial; panel still shows ms

### Tests

- [x] T031 [P] [US4] Regression: partial entries never create turns in `apps/desktop-shell/tests/assistant-auto.test.ts` (extend if gap)
- [x] T032 [P] [US4] Confirm panel still renders `latencyMs` for done turns in `apps/desktop-shell/tests/assistant-panel.test.ts` (extend if gap)

### Implementation

- [x] T033 [US4] Update `docs/development/running.md`: disparo ≠ contexto; include-mic default; interview style 1ª pessoa; latency chain + recommended knobs table; Assistente vs :8001
- [x] T034 [P] [US4] Cross-link quickstart / one-line note in `docs/release/min-flow.md` if appropriate
- [x] T035 [US4] Align `specs/028-issue-61-live-answer-interview-mode/quickstart.md` with final UI labels/testids
- [x] T036 [US4] Optional short note under Clarifications in `specs/019-auto-answer-assistant/spec.md` that context may include mic when preferência ON (028)

**Checkpoint**: SC-006, SC-007 documentable

---

## Phase 7: Polish & Cross-Cutting

**Purpose**: Suíte verde, privacidade, checklist de qualidade

- [x] T037 [P] Full shell test suite for touched files: `cd apps/desktop-shell && npm test -- --run`
- [x] T038 [P] Rust prefs unit test default/isolation for new field if `assistant_prefs.rs` has `#[cfg(test)]` — extend in `apps/desktop-shell/src-tauri/src/assistant_prefs.rs`
- [x] T039 Verify no log path dumps full model output for this feature (spot-check shell invoke path) — FR-020
- [x] T040 Mark domain checklist items in `specs/028-issue-61-live-answer-interview-mode/checklists/interview-mode.md` after self-review of requirements vs implementation readiness
- [x] T041 Summarize diff + residual risks for G3 (no merge)

---

## Dependencies

```text
Phase 1 Setup
    ↓
Phase 2 Foundational (prefs field + recentFinals.sourceType)
    ↓
Phase 3 US1 (builder mixed context) ──► MVP value
    ↓
Phase 4 US3 (UI toggle)  [can start after T004–T006; ideally after US1 builder]
    ↓
Phase 5 US2 (instruction + detector)  [needs builder signature stable from US1]
    ↓
Phase 6 US4 (docs + regressions)
    ↓
Phase 7 Polish
```

**Story independence**:
- US1 is MVP alone (API-level builder + tests without UI).
- US3 needs prefs field (Phase 2) + optional US1 for end-to-end meaning.
- US2 needs builder hook point (US1 signature).
- US4 is mostly docs + regressions; can parallelize docs with US2 after Phase 2.

## Parallel examples

```bash
# After Phase 2:
# Parallel US1 test scaffolding:
T009 T010 T011 T012 T013

# After US1 implementation:
# Parallel US3 tests + US2 tests:
T018 T019 T024 T025

# Docs parallel:
T033 T034
```

## Implementation strategy

1. **MVP**: Phase 1–3 → mixed context + no trigger regression (issue P0 half).
2. **Ship-quality interview**: Phase 4–5 → toggle + 1ª pessoa instruction.
3. **Ops clarity**: Phase 6–7 → latency docs + full green.

## Task count summary

| Phase | Tasks | Story |
|-------|-------|-------|
| 1 Setup | T001–T003 | — |
| 2 Foundational | T004–T008 | — |
| 3 US1 | T009–T017 | US1 |
| 4 US3 | T018–T023 | US3 |
| 5 US2 | T024–T030 | US2 |
| 6 US4 | T031–T036 | US4 |
| 7 Polish | T037–T041 | — |
| **Total** | **41** | |

**Suggested MVP scope**: T001–T017 (through US1 checkpoint).

## Format validation

- All tasks use `- [ ] Tnnn` checklist form
- Story phases include `[USn]` labels
- Setup/Foundational/Polish omit story labels
- File paths present on implementation/test tasks
