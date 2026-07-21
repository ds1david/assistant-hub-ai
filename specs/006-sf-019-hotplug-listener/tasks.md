---

description: "Task list for SF-019 — Listener de hot-plug nativo MMDevice"
---

# Tasks: Listener de hot-plug nativo MMDevice (SF-019)

**Input**: Design documents from `/specs/006-sf-019-hotplug-listener/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md (all present; no `contracts/` — feature is internal to the worker process, per plan.md)

**Tests**: Included — the feature spec requires full testability without hardware/COM (FR-007, constitution P10) and every success criterion (SC-001..SC-005) is defined in terms of automated tests with a fake provider.

**Organization**: Tasks are grouped by user story (US1/US2/US3 from spec.md), in priority order (P1 → P2 → P3).

## Path Conventions

Single existing project, no new top-level directory:

- Source: `agents/windows-audio-agent/src/assistant_hub_audio/`
- Tests: `agents/windows-audio-agent/tests/`
- Manual validation record: `docs/validation/sf-019-windows.md`

---

## Phase 1: Setup

**Purpose**: Confirm the baseline before touching any file — no new dependencies are added (plan.md: `pycaw`/`comtypes` are already `win32`-only dependencies).

- [X] T001 Establish baseline: run `cd agents/windows-audio-agent && python3 -m compileall -q src && PYTHONPATH=src python3 -m pytest -q tests` per `specs/006-sf-019-hotplug-listener/quickstart.md` §1 and confirm the existing suite passes before any change

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core `hotplug.py` entities and test doubles that every user story builds on (event shape, provider protocol, degrade path, per-channel signal with filtering/debounce). Mirrors the existing `endpoints.py`/`mmdevice.py` Protocol + null-provider + lazy-import pattern.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Create `HotplugEvent` dataclass (`endpoint_id: str`, `event_type: Literal["arrived", "removed", "state_changed"]`, `timestamp: float`) with non-empty `endpoint_id` validation in `agents/windows-audio-agent/src/assistant_hub_audio/hotplug.py`
- [X] T003 Create `NotificationProvider` Protocol (`subscribe(on_event: Callable[[HotplugEvent], None]) -> None`, `close() -> None`) in `agents/windows-audio-agent/src/assistant_hub_audio/hotplug.py` (depends on T002)
- [X] T004 Create `NullNotificationProvider` (no-op `subscribe`/`close`, never emits) in `agents/windows-audio-agent/src/assistant_hub_audio/hotplug.py` (depends on T003)
- [X] T005 Create `get_notification_provider()` factory: non-Windows platform or any registration failure returns `NullNotificationProvider` (never raises), Windows lazily imports `MMDeviceNotificationProvider` from `mmdevice_notifications.py` — same shape as `endpoints.get_endpoint_provider` — in `agents/windows-audio-agent/src/assistant_hub_audio/hotplug.py` (depends on T004)
- [X] T006 Create `ChannelHotplugSignal` (`configured_endpoint_id: str | None`, `removed: threading.Event`, `arrived: threading.Event`, per-event-type `last_event_at` monotonic timestamp) with a `handle_event(event: HotplugEvent) -> None` method that: ignores events whose `endpoint_id` doesn't case-insensitively match `configured_endpoint_id` (FR-004); maps `state_changed`→non-active as `removed` and `state_changed`→`active` as `arrived` (data-model.md); sets the matching `Event` only when outside the short debounce window since the last event of that type (FR-005) in `agents/windows-audio-agent/src/assistant_hub_audio/hotplug.py` (depends on T002)
- [X] T007 Create `HotplugListener`: takes a `NotificationProvider` and a `ChannelHotplugSignal`, calls `subscribe(signal.handle_event)` on construction, exposes `close()` delegating to the provider in `agents/windows-audio-agent/src/assistant_hub_audio/hotplug.py` (depends on T005, T006)
- [X] T008 [P] Create `FakeNotificationProvider` test double (`subscribe`, `close`, `emit(endpoint_id, event_type)` calling the registered callback synchronously) — same pattern as `FakeEndpointProvider` in `tests/test_endpoints.py` — in `agents/windows-audio-agent/tests/test_hotplug.py` (depends on T003)
- [X] T009 Unit tests for `ChannelHotplugSignal.handle_event`: own-endpoint filtering (FR-004), debounce within the short window using an injectable/monkeypatched clock (FR-005), and the `state_changed`→active/non-active mapping, in `agents/windows-audio-agent/tests/test_hotplug.py` (depends on T006, T008)
- [X] T010 Unit test: `get_notification_provider()` returns `NullNotificationProvider` and never raises on the current (non-Windows) platform (FR-006) in `agents/windows-audio-agent/tests/test_hotplug.py` (depends on T005)

**Checkpoint**: `hotplug.py` core entities exist and are covered by tests with a fake provider — user story implementation can begin.

---

## Phase 3: User Story 1 - Falha imediata e explícita quando o endpoint some durante a captura (Priority: P1) 🎯 MVP

**Goal**: A channel capturing a configured `endpointId` reacts to a native removal notification by ending the current capture attempt immediately with a distinct "endpoint removed" error, instead of waiting for the next stream-read failure and reconnect backoff cycle.

**Independent Test**: With `FakeNotificationProvider`, emit a `removed` event for the `endpointId` of a channel mid-capture and verify the worker reacts to the notification itself (not the stream read failure) with a distinct "endpoint removed" message.

- [X] T011 [P] [US1] Test: `HotplugListener` dispatches an event to the `ChannelHotplugSignal` whose `configured_endpoint_id` matches, leaving other channels' signals untouched (US1 Acceptance Scenario 2, FR-004) in `agents/windows-audio-agent/tests/test_hotplug.py`
- [X] T012 [P] [US1] Add a distinct `EndpointRemovedError` exception (sibling of `EndpointResolutionError`, not retried the same way — see FR-002) in `agents/windows-audio-agent/src/assistant_hub_audio/capture.py`
- [X] T013 [US1] In `capture_channel`, before the retry loop begins, create **one** `ChannelHotplugSignal(configured_endpoint_id=channel.selector.endpoint_id)` and **one** `HotplugListener` via `get_notification_provider()` — scoped to the whole worker lifetime, not a single attempt — and call `listener.close()` exactly once in a `finally` block when `capture_channel` returns, regardless of outcome (FR-001; the signal must survive the reconnect-backoff wait for T022 to work) in `agents/windows-audio-agent/src/assistant_hub_audio/capture.py` (depends on T007, T012)
- [X] T014 [US1] In `_capture_once`, accept the shared `signal: ChannelHotplugSignal` created by `capture_channel` as a new parameter (do not construct it locally) and check `signal.removed.is_set()` on every iteration of the stream-read loop alongside `stop_event`, raising `EndpointRemovedError` immediately when set (FR-002) in `agents/windows-audio-agent/src/assistant_hub_audio/capture.py` (depends on T013)
- [X] T015 [US1] In `capture_channel`, catch `EndpointRemovedError` distinctly: log the specific "endpoint removido" message, then wait out the normal reconnect backoff like any other transient failure — not the permanent-exit path used by `EndpointResolutionError` — via the shared `_wait_for_reconnect` helper (FR-002; implementation note: skipping the wait entirely was rejected — the endpoint is still gone immediately after removal, so an instant retry would hit `EndpointResolutionError` and kill the worker, defeating FR-003/US2's resume) in `agents/windows-audio-agent/src/assistant_hub_audio/capture.py` (depends on T014)
- [X] T016 [P] [US1] Test: with `FakeNotificationProvider`, a `removed` event mid-loop makes `_capture_once`/`capture_channel` raise/log the removed-specific error without waiting for a `stream.read` failure (US1 Acceptance Scenario 1, SC-001) in `agents/windows-audio-agent/tests/test_capture_channel.py`
- [X] T017 [US1] Test: a `removed` event for an `endpointId` that doesn't belong to the active channel leaves it capturing normally (US1 Acceptance Scenario 2) in `agents/windows-audio-agent/tests/test_capture_channel.py`
- [X] T018 [P] [US1] Test: a channel whose `selector.endpoint_id` is `None` (index/nameRegex/default selector) gets an inert `ChannelHotplugSignal` — `removed`/`arrived` never set regardless of injected events — and is unaffected by hot-plug notifications in `agents/windows-audio-agent/tests/test_hotplug.py`
- [X] T019 [P] [US1] Implement `MMDeviceNotificationProvider`: `IMMNotificationClient` via `comtypes`, registered on the `IMMDeviceEnumerator` from `pycaw.utils.AudioUtilities.GetDeviceEnumerator()` via `RegisterEndpointNotificationCallback`, translating `OnDeviceStateChanged`/`OnDeviceAdded`/`OnDeviceRemoved` into `HotplugEvent` (research.md §1) in `agents/windows-audio-agent/src/assistant_hub_audio/mmdevice_notifications.py` (depends on T002, T003)

**Checkpoint**: User Story 1 is fully functional and testable independently — removal of a captured endpoint ends the attempt immediately with a distinct error.

---

## Phase 4: User Story 2 - Retomada automática quando o endpoint volta (Priority: P2)

**Goal**: After a User Story 1 removal, an arrival notification for the same `endpointId` re-resolves the device and resumes capture automatically, without a manual process restart and without waiting out the backoff ceiling; a still-failing re-resolution falls back to the generic backoff, and a deliberately stopped channel is never restarted.

**Independent Test**: With `FakeNotificationProvider`, emit `removed` then `arrived` for the same `endpointId` and verify the channel resumes capturing on that same `endpointId` without external intervention.

- [X] T020 [P] [US2] Test: `HotplugListener` sets `arrived` only on the `ChannelHotplugSignal` whose `configured_endpoint_id` matches, ignoring a different `endpointId` (US2 Acceptance Scenario 2, FR-004) in `agents/windows-audio-agent/tests/test_hotplug.py`
- [X] T021 [US2] In `capture_channel`, replace the plain `stop_event.wait(reconnect_delay)` backoff wait with one that also wakes on the shared `signal.arrived` (created in T013), clearing the flag once consumed (research.md §3) in `agents/windows-audio-agent/src/assistant_hub_audio/capture.py` (depends on T015)
- [X] T022 [US2] On an arrival wake-up, retry `_capture_once` immediately — re-invoking `resolve_device`/`find_device_for_endpoint` through the existing `devices.resolve_device`, passing the same `channel` — instead of waiting out the remaining backoff (FR-003) in `agents/windows-audio-agent/src/assistant_hub_audio/capture.py` (depends on T021)
- [X] T023 [US2] If re-resolution still fails right after an arrival wake-up, fall back to the generic backoff loop unchanged — no dedicated retry, no permanent termination (FR-003 / Clarifications Q3) in `agents/windows-audio-agent/src/assistant_hub_audio/capture.py` (depends on T022)
- [X] T024 [US2] Ignore `signal.arrived` once `stop_event` is already set — a deliberately stopped channel MUST NOT be restarted by an arrival notification (FR-008) in `agents/windows-audio-agent/src/assistant_hub_audio/capture.py` (depends on T021)
- [X] T025 [P] [US2] Test: `removed` then `arrived` for the same `endpointId` resumes capture on that same endpoint without a process restart, and assert `resolve_device`/`_capture_once` is invoked with the identical `channel`/`endpoint_id` — never substituted (US2 Acceptance Scenario 1, SC-002, SC-004) in `agents/windows-audio-agent/tests/test_capture_channel.py`
- [X] T026 [US2] Test: an `arrived` event for a different `endpointId` than configured leaves the channel's state unchanged (US2 Acceptance Scenario 2) in `agents/windows-audio-agent/tests/test_capture_channel.py`
- [X] T027 [US2] Test: a burst of duplicate `arrived`/`removed` events for the same `endpointId` triggers at most one reaction, verified by call count on `FakeNotificationProvider`/mocked `_capture_once` (US2 Acceptance Scenario 3, FR-005, SC-005) in `agents/windows-audio-agent/tests/test_capture_channel.py`
- [X] T028 [US2] Test: an `arrived` event delivered after `stop_event` is set does not restart the channel (Edge case, FR-008) in `agents/windows-audio-agent/tests/test_capture_channel.py`
- [X] T029 [US2] Test: an `arrived` event whose re-resolution still fails falls back to the generic backoff without permanent termination, and asserts the fallback keeps retrying the same `endpoint_id` rather than any other device (Edge case, FR-003/Clarifications Q3, SC-004) in `agents/windows-audio-agent/tests/test_capture_channel.py`

**Checkpoint**: User Stories 1 and 2 both work independently — remove-then-resume is fully automatic on the same `endpointId`.

---

## Phase 5: User Story 3 - Testável e portátil sem hardware ou COM real (Priority: P3)

**Goal**: The listener is verifiably isolated from `endpoints.py`'s correlation logic and degrades to a null implementation off Windows, so the whole suite (US1 + US2) runs in CI without `pywin32`/COM.

**Independent Test**: Run the listener test suite on Linux/CI with the fake provider, confirm no `pywin32`/COM dependency is loaded, and confirm it covers removal, arrival and debounce.

- [X] T030 [P] [US3] Test: on a non-Windows platform (and when forcing a COM registration failure), `get_notification_provider()`/`HotplugListener` never import `comtypes`/`pycaw` and never raise (FR-006, US3 Acceptance Scenario 1) in `agents/windows-audio-agent/tests/test_hotplug.py`
- [X] T031 [US3] Test/static assertion: `hotplug.py` does not define or duplicate `correlate_devices`/`find_device_for_endpoint` — it only imports and calls them from `endpoints.py`/`devices.py` (US3 Acceptance Scenario 3) in `agents/windows-audio-agent/tests/test_hotplug.py`

**Checkpoint**: All three user stories are independently functional; the full listener suite is CI-portable (SC-003).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Full-suite regression check and the mandatory manual Windows evidence (constitution P10, SC-006).

- [X] T032 [P] Run the full regression suite — `cd agents/windows-audio-agent && python3 -m compileall -q src && PYTHONPATH=src python3 -m pytest -q tests` (not just `-k "hotplug or capture"`) — confirming `test_capture.py`, `test_endpoints.py`, `test_profiles.py` and `test_run_agent.py` still pass after the `capture.py` changes, per `specs/006-sf-019-hotplug-listener/quickstart.md` §1
- [ ] T033 Perform the manual Windows hot-plug validation from `specs/006-sf-019-hotplug-listener/quickstart.md` §2 (real USB/Bluetooth replug) and record environment, commit, steps and PASS/FAIL result in `docs/validation/sf-019-windows.md`, following the format of `docs/validation/sf-018-windows.md` (SC-006)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup. BLOCKS all user stories (T002→T003→T004→T005 and T002→T006 are sequential edits to `hotplug.py`; T007 needs both T005 and T006; T008 is a separate test file and only needs T003; T009 needs T006+T008; T010 needs T005).
- **User Story 1 (Phase 3)**: Depends on Foundational only. MVP. T013 creates the per-worker `ChannelHotplugSignal`/`HotplugListener` once in `capture_channel` (not per attempt) so it survives the reconnect-backoff wait; T014's `_capture_once` receives it as a parameter.
- **User Story 2 (Phase 4)**: Depends on Foundational; also depends on US1's `capture.py` changes (T013's shared `signal`, T015) since both stories edit the same reconnect loop sequentially — not independently mergeable ahead of US1, but independently testable once merged.
- **User Story 3 (Phase 5)**: Depends on Foundational only; independent of US1/US2 code (it tests properties of the shared `hotplug.py` module).
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### Within Each User Story

- Tests are written alongside/after the behavior they cover per task order above (this feature does not use strict TDD ordering, but no story is "done" until its tests pass).
- `capture.py` tasks within a story are sequential (same file); `hotplug.py`/`mmdevice_notifications.py`/test-file tasks that touch different files are parallelizable.

### Parallel Opportunities

- Foundational: T008 (`tests/test_hotplug.py`) can run in parallel with the `hotplug.py` chain (T002–T007).
- US1: T011 and T018 (`test_hotplug.py`), T012 (`capture.py` exception), and T019 (`mmdevice_notifications.py`) can run in parallel; T013 needs T007+T012; T016 starts once T015 lands.
- US2: T020 (`test_hotplug.py`) and T025 (`test_capture_channel.py`, once T023/T024 land) can run in parallel with each other.
- US3: T030 can start as soon as Foundational is done, in parallel with US1/US2 work.

---

## Parallel Example: User Story 1

```bash
# After Foundational (T002-T010) is done, these can start together:
Task: "Test HotplugListener dispatch filtering in agents/windows-audio-agent/tests/test_hotplug.py"       # T011
Task: "Add EndpointRemovedError in agents/windows-audio-agent/src/assistant_hub_audio/capture.py"          # T012
Task: "Test inert signal for channels without endpointId in agents/windows-audio-agent/tests/test_hotplug.py"  # T018
Task: "Implement MMDeviceNotificationProvider in agents/windows-audio-agent/src/assistant_hub_audio/mmdevice_notifications.py"  # T019
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (baseline test run).
2. Complete Phase 2: Foundational (`hotplug.py` core entities + fakes — CRITICAL, blocks everything).
3. Complete Phase 3: User Story 1 — immediate, distinct "endpoint removed" error.
4. **STOP and VALIDATE**: `pytest -k "hotplug or capture"` per quickstart.md §1; SC-001 satisfied.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. User Story 1 → validate independently → MVP: explicit removal detection.
3. User Story 2 → validate independently → automatic resume on the same endpoint.
4. User Story 3 → validate CI-portability (mostly already true by construction; this phase proves it).
5. Polish → full regression + mandatory manual Windows evidence (SC-006) before merge.

---

## Notes

- No `contracts/` phase: this feature introduces no external API, event schema or CLI surface (plan.md).
- No new dependencies: `pycaw`/`comtypes` are already `win32`-only dependencies used by `mmdevice.py`.
- `[P]` tasks touch different files and have no unmet dependency within their phase.
- `[US1]`/`[US2]`/`[US3]` label maps each task to its owning user story for traceability; Setup/Foundational/Polish tasks carry no story label by convention.
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
