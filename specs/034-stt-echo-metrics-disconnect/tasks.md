# Tasks: STT — finalização no disconnect e métricas de eco confiáveis

**Input**: Design documents from `/specs/034-stt-echo-metrics-disconnect/`  
**Prerequisites**: plan.md, spec.md (clarified), research.md, data-model.md, contracts/session-metrics-disconnect.md, quickstart.md  
**Tests**: Explicit in spec (FR-009, SC-001–SC-005) — include test tasks  
**Note**: Implementation largely exists on `fix/stt-echo-metrics-disconnect-final`. Tasks remain executable: implement if missing, verify/adjust if present, then mark complete.

**Status (2026-07-27)**: All T001–T033 completed/verified. Suite 126 passed; echo stress 60/60; residual: metrics recorded before prosody await; docs note in `docs/development/running.md`.  
**Analyze remediação (2026-07-27)**: I1/I2/C1/U1 aplicados em spec/plan/research/contract/tasks (docs only; sem mudança de código).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: [US1]…[US4] for user-story phases only

## Path Conventions

- Service: `services/transcription-service/app/`, `services/transcription-service/tests/`
- Spec docs: `specs/034-stt-echo-metrics-disconnect/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align branch, docs pointer, and test baseline

- [x] T001 Confirm active feature dir in `.specify/feature.json` is `specs/034-stt-echo-metrics-disconnect` and branch tracks disconnect/metrics work
- [x] T002 [P] Inventory current disconnect/metrics code paths in `services/transcription-service/app/main.py`, `broadcast.py`, `metrics.py`, `utterance.py`, `echo_suppression.py` against plan.md
- [x] T003 [P] Run baseline suite: `PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests/test_session_metrics_endpoint.py` and capture pass/fail

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core disconnect emit + metrics-first pipeline shared by all stories

**⚠️ CRITICAL**: Complete before story polish/verification claims

- [x] T004 Ensure audio channel processing is **sequential** (`await emit` on the connection task; no worker queue that can drop disconnect ticks) in `services/transcription-service/app/main.py` (FR-011)
- [x] T005 Implement `publish_transcript` to call `metrics.record_transcription(...)` **before any await** on the publish path (prosody `to_thread`, audio WS send, feed fan-out) in `services/transcription-service/app/main.py` (FR-003 / U1)
- [x] T006 Implement disconnect residual path `finalize_disconnect` (flush + `emit(..., disconnect=True)`) in `services/transcription-service/app/main.py` (FR-001)
- [x] T007 Protect disconnect finalization against teardown cancellation (`asyncio.shield` + best-effort sync metrics if still open with text) in `services/transcription-service/app/main.py` (FR-001, research R5)
- [x] T008 Bound feed fan-out: per-subscriber send timeout **1.0s** in `services/transcription-service/app/broadcast.py` and producer publish cap **0.5s** in `services/transcription-service/app/main.py` (FR-012)
- [x] T009 Confirm `LatencyMetricsRegistry.record_transcription` remains sync/thread-safe and counts once per call in `services/transcription-service/app/metrics.py` (FR-002)

**Checkpoint**: Disconnect residual + metrics-first + timeouts in place; single-channel path ready for US1 validation

---

## Phase 3: User Story 1 - Métricas corretas após desligar um canal (Priority: P1) 🎯 MVP

**Goal**: After one delivered partial and channel disconnect, session metrics show partial + disconnect final (sampleCount/totalEvents coherent); feed fan-out does not multiply

**Independent Test**: `test_delivered_event_is_measured_once`, `test_feed_subscribers_do_not_duplicate_samples` in `test_session_metrics_endpoint.py`

### Tests for User Story 1

- [x] T010 [P] [US1] Assert partial + disconnect final → `sampleCount == 2` / `totalEvents == 2` in `services/transcription-service/tests/test_session_metrics_endpoint.py` (`test_delivered_event_is_measured_once`)
- [x] T011 [P] [US1] Assert feed subscribers do not duplicate samples in `services/transcription-service/tests/test_session_metrics_endpoint.py` (`test_feed_subscribers_do_not_duplicate_samples`)

### Implementation for User Story 1

- [x] T012 [US1] Skip direct audio-WS send for finals with reason `disconnect` (`skip_direct_send`) while still recording metrics and fan-out in `services/transcription-service/app/main.py` (FR-004)
- [x] T013 [US1] Ensure identity fields on disconnect finals match channel partials (sessionId/channelId/sourceType/label) in `services/transcription-service/app/main.py` (FR-004, P5)
- [x] T014 [US1] Log disconnect completion with session/channel/dropped_windows/finals counters only (no PCM) in `services/transcription-service/app/main.py` (FR-010)

**Checkpoint**: US1 green — single-channel metrics stable after disconnect

---

## Phase 4: User Story 2 - Eco suprimido não infla métricas do microfone (Priority: P1)

**Goal**: Nested system+mic: suppressed echo not counted; local mic speech + disconnect final counted; both channels stabilize

**Independent Test**: `test_suppressed_echo_is_not_counted_as_delivered` (+ stress ≥ 60)

### Tests for User Story 2

- [x] T015 [P] [US2] Echo multi-channel test with scripted system/mic texts and expected mic/system counts == 2 in `services/transcription-service/tests/test_session_metrics_endpoint.py`
- [x] T016 [US2] Add `wait_metrics` poll helper (≤ 2.0s, min_sample_count, expected_channels) in `services/transcription-service/tests/test_session_metrics_endpoint.py` (SC-002)
- [x] T017 [US2] Harden FakeTranscriptionEngine against concurrent script access if needed in `services/transcription-service/tests/conftest.py`

### Implementation for User Story 2

- [x] T018 [US2] Keep echo-suppressed path from calling `publish_transcript` / `record_transcription` in `services/transcription-service/app/main.py` + `echo_suppression.py` (FR-005)
- [x] T019 [US2] On disconnect after suppressed window, still run finalizer disconnect without counting suppressed text as delivered in `services/transcription-service/app/main.py`
- [x] T020 [US2] Run stress ≥ 60× of suppressed_echo scenario per `specs/034-stt-echo-metrics-disconnect/quickstart.md` (SC-005 / FR-009)

**Checkpoint**: US2 green — eco + nested teardown stable

---

## Phase 5: User Story 3 - Isolamento de sessão e de canal (Priority: P2)

**Goal**: Metrics isolated by sessionId and channelId with independent counts

**Independent Test**: `test_sessions_are_isolated_over_http`, `test_channels_are_isolated_over_http`

### Tests for User Story 3

- [x] T021 [P] [US3] Session isolation assertions in `services/transcription-service/tests/test_session_metrics_endpoint.py`
- [x] T022 [P] [US3] Channel isolation assertions (two channels, each sampleCount == 2 after disconnect) in `services/transcription-service/tests/test_session_metrics_endpoint.py`

### Implementation for User Story 3

- [x] T023 [US3] Confirm registry keys `(session_id, channel_id)` and `session_snapshot` filter in `services/transcription-service/app/metrics.py` (FR-006)
- [x] T024 [US3] Confirm HTTP metrics endpoint returns only requested session channels in `services/transcription-service/app/main.py` (FR-007)

**Checkpoint**: US3 green — no cross-session/channel bleed

---

## Phase 6: User Story 4 - Operador e CI confiam no endpoint (Priority: P3)

**Goal**: Docs/quickstart explain partial + disconnect final and eco not counted; suite reliable

**Independent Test**: quickstart commands + full service tests

### Implementation for User Story 4

- [x] T025 [P] [US4] Keep/align operational notes in `specs/034-stt-echo-metrics-disconnect/quickstart.md` (partial+disconnect, eco, poll, stress)
- [x] T026 [P] [US4] Optional one-line note in `docs/development/running.md` if metrics interpretation is missing (partial + disconnect final; eco not counted)
- [x] T027 [US4] Ensure comments in `services/transcription-service/tests/test_session_metrics_endpoint.py` document expected counts (partial + disconnect final; suppressed not counted)
- [x] T028 [US4] Run full service suite: `PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests` (SC-005 gate)

**Checkpoint**: US4 green — CI/docs path clear

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Regression, contract alignment, G3 evidence

- [x] T029 [P] Regression: disconnect after idle does not double-final — `services/transcription-service/tests/test_ws_utterance_final.py` + `test_utterance_finalizer.py`
- [x] T030 [P] Regression: transcript endpoint totalEvents still coherent with finals in `services/transcription-service/tests/test_transcript_endpoint.py`
- [x] T031 Confirm no schema change to `contracts/transcript-event.v2.schema.json` and metrics JSON shape matches `specs/034-stt-echo-metrics-disconnect/contracts/session-metrics-disconnect.md`
- [x] T032 Walk G2 checklist `specs/034-stt-echo-metrics-disconnect/checklists/disconnect-metrics.md` (requirements quality) and mark items
- [x] T033 Summarize residual risks (TestClient cancel races, slow subscribers) for PR description; no force-push/merge (P8)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: immediate
- **Foundational (Phase 2)**: after Setup — **blocks** US1–US4 implementation claims
- **US1 (Phase 3)**: after Foundational — MVP
- **US2 (Phase 4)**: after Foundational; benefits from US1 metrics-first path
- **US3 (Phase 5)**: after Foundational; independent of US2 logic but shares suite
- **US4 (Phase 6)**: after US1–US3 tests exist
- **Polish (Phase 7)**: after desired stories complete

### User Story Dependencies

- **US1 (P1)**: no story deps — MVP
- **US2 (P1)**: uses same publish/metrics path as US1; adds echo + poll
- **US3 (P2)**: registry isolation; parallelizable with US2 after T004–T009
- **US4 (P3)**: docs + full suite after stories green

### Parallel Opportunities

- T002/T003; T010/T011; T015/T017; T021/T022; T025/T026; T029/T030
- After Phase 2: US1 tests and US3 tests can proceed in parallel if staffed

---

## Parallel Example: User Story 1

```bash
# Tests in parallel (same file — usually sequential in practice):
Task: T010 sampleCount==2 single channel
Task: T011 feed non-multiplication

# Then implementation wiring in main.py:
Task: T012 skip_direct_send disconnect
Task: T013 identity on finals
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1–2 (sequential emit, metrics-first, shield, timeouts)
2. Phase 3 US1 tests green
3. **STOP and VALIDATE** with T010/T011

### Incremental Delivery

1. US1 → reliable single-channel disconnect metrics  
2. US2 → eco multi-canal + stress  
3. US3 → isolation asserts  
4. US4 → docs + full suite  
5. Polish regressions + checklist

### Suggested MVP scope

**T001–T014** (Setup + Foundational + US1) delivers the primary product fix for `sampleCount` after disconnect.

---

## Notes

- Prefer verifying existing branch code against tasks over rewrites
- Do not reintroduce per-channel worker queues
- Do not change transcript-event.v2 schema
- Privacy: no PCM or full transcript dumps in INFO logs beyond existing echo debug patterns already constrained by P9
