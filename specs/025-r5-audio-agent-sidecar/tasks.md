# Tasks: R5 — Audio Agent como sidecar supervisionado

**Input**: Design documents from `/specs/025-r5-audio-agent-sidecar/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup

- [x] T001 Create `apps/desktop-shell/src-tauri/binaries/.gitkeep` and note in packaging docs
- [x] T002 Add `bundle.externalBin` entry for `binaries/assistant-hub-audio` in `apps/desktop-shell/src-tauri/tauri.conf.json`

## Phase 2: Foundational

- [x] T003 [P] Implement `BinarySource` + `BinaryResolution` + `resolve_audio_agent_binary` in `apps/desktop-shell/src-tauri/src/sidecar.rs` (order: sidecar → env → config → path → missing) per contracts
- [x] T004 [P] Implement `probe_agent_version(path)` via `--version` with timeout in `sidecar.rs`
- [x] T005 Extend `ShellConfig` with optional `audio_agent_bin` in `apps/desktop-shell/src-tauri/src/config.rs` (serde camelCase `audioAgentBin`)
- [x] T006 Wire `pub mod sidecar` in `apps/desktop-shell/src-tauri/src/lib.rs`

## Phase 3: User Story 1 — Start without PATH (P1)

- [x] T007 [US1] Extend `AgentStatus` in `agent_control.rs` with `binary_path`, `binary_source`, `agent_version`, `healthy`
- [x] T008 [US1] Change `start_agent` in `main.rs` to resolve binary via `sidecar::resolve` and `Command::new(path)` instead of hard-coded PATH name only
- [x] T009 [P] [US1] Unit tests for resolution priority in `apps/desktop-shell/src-tauri/tests/sidecar_tests.rs` (or mod tests in sidecar.rs)
- [x] T010 [US1] Map missing binary to existing/extended `StartError::BinaryNotFound` message mentioning sidecar/PATH

## Phase 4: User Story 2 — Health & version (P1)

- [x] T011 [US2] On status/build_status/start success, fill version via probe and healthy from process liveness
- [x] T012 [P] [US2] Test version probe success/failure (fake script) in sidecar tests
- [x] T013 [US2] Clear managed handle when process no longer running in `get_agent_status` (already partial) and set `healthy=false`

## Phase 5: User Story 3 — Coordinated shutdown (P1)

- [x] T014 [US3] On Tauri/normal exit path, stop managed agent in `main.rs` (RunEvent::Exit or Drop/App handle)
- [x] T015 [P] [US3] Test: start fake long-running child via agent_control, simulate shutdown helper, assert child not running
- [x] T016 [US3] Document that Guided/external processes are not killed (packaging + agent panel hint if needed)

## Phase 6: User Story 4 — Docs & UI polish (P2)

- [x] T017 [US4] Add `scripts/windows/build-audio-agent-sidecar.ps1` (venv + copy/build instructions)
- [x] T018 [US4] Update `docs/desktop-shell/packaging.md` with sidecar section
- [x] T019 [US4] Template `docs/validation/r5-audio-agent-sidecar.md`
- [x] T020 [US4] Extend TS `AgentStatus` + agent panel to show source/version/healthy in `api-client.ts` / `agent-panel.ts`
- [x] T021 [P] [US4] Update/add vitest if panel formats new fields

## Phase 7: Polish

- [x] T022 Run `cargo test` in `apps/desktop-shell/src-tauri` and fix regressions on AgentStatus shape
- [x] T023 Update `specs/002-desktop-distribution/tasks.md` checkboxes for sidecar/supervisor if now partial/done
- [x] T024 [P] Ensure no secrets/audio in logs; guidance_command still reproducible

## Dependencies

Setup → Foundational → US1 → US2/US3 (parallel after T008) → US4 → Polish

## MVP

T001–T016 deliver product-critical behavior; T017–T021 packaging/UI; T022–T024 polish.
