# Tasks: Consistência de origem (`sourceType`) em resultados de invocação de IA

**Input**: Design documents from `/specs/017-issue-40-invocation-sourcetype/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídos — FR-008 / SC-001–SC-003 e clarificações exigem suíte automatizada do contrato de origem.

**Organization**: Tasks grouped by user story (US1 → US2 → US3) after shared foundation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3 maps to spec user stories
- Paths are repo-relative from monorepo root

## Path Conventions

- Java domain: `services/session-core/src/main/java/ai/assistanthub/core/`
- Java tests: `services/session-core/src/test/java/ai/assistanthub/core/`
- Desktop: `apps/desktop-shell/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar fixtures e inventário sem nova stack; monorepo já existe.

- [x] T001 Review design docs in `specs/017-issue-40-invocation-sourcetype/` (spec clarifications Q1–Q5, plan.md, research.md Decisions 1–6, data-model.md, contracts/invocation-result-sourcetype.md) and list compile-break sites for `InvocationResult` constructors under `services/session-core/`
- [x] T002 [P] Add HubEvent/session fixture helpers in `services/session-core/src/test/java/ai/assistanthub/core/provider/ProviderTestSupport.java`: create real `ConversationSession` + `SessionRepository` via `MemoryHubTestSupport`; append `HubEvent` with `correlation.channelId`/`sourceType`; return **`session.id().toString()` (UUID)** for use as `InvocationRequest.sessionId` whenever a test uses non-null `channelId` (analyze U1)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelo aditivo + resolvedor + wiring mínimo para qualquer story invocar com origem.

**⚠️ CRITICAL**: Nenhuma user story completa sem esta fase.

- [x] T003 Add nullable `sourceType` field to `services/session-core/src/main/java/ai/assistanthub/core/provider/InvocationResult.java` and update all constructors/call sites in `services/session-core/src/main/java/ai/assistanthub/core/provider/`
- [x] T004 [P] Create `ChannelOriginUnresolvedException` in `services/session-core/src/main/java/ai/assistanthub/core/provider/ChannelOriginUnresolvedException.java` (session-context failure; not `InvocationErrorType`)
- [x] T005 Implement `ChannelOriginResolver` in `services/session-core/src/main/java/ai/assistanthub/core/provider/ChannelOriginResolver.java`: accept `String sessionId` + `String channelId`; when resolving, **parse `sessionId` as `UUID`** — if invalid UUID, throw `ChannelOriginUnresolvedException` (never raw `IllegalArgumentException` to the client); then `SessionRepository.events(uuid)`, filter `correlation.channelId`, accept only canonical `microphone`|`system`, reject empty / non-canonical / multi-value conflict (research Decision 4–5 / data-model.md; analyze U1)
- [x] T006 Wire `ChannelOriginResolver` into `InvocationService` constructor and `invoke` in `services/session-core/src/main/java/ai/assistanthub/core/provider/InvocationService.java`: blank `channelId` → `sourceType=null` and **do not** require UUID/`SessionRepository` lookup; non-blank `channelId` → resolve before provider loop or throw (`ChannelOriginUnresolvedException` for bad UUID, missing session/events, non-canonical, conflict); pass `sourceType` into all `InvocationResult` builds (`attempt`, `failureResult`, empty-providers path)
- [x] T007 Map `ChannelOriginUnresolvedException` to HTTP 422 in `services/session-core/src/main/java/ai/assistanthub/core/provider/AiProviderController.java` (including invalid `sessionId` UUID when `channelId` present); ensure `InvokeRequest` does **not** accept caller `sourceType` as authority
- [x] T008 Update `ProviderTestSupport.newInvocationService` (and any Spring wiring if present) in `services/session-core/src/test/java/ai/assistanthub/core/provider/ProviderTestSupport.java` to inject `ChannelOriginResolver` + `SessionRepository` so existing provider tests still construct the service
- [x] T009 Repair compile/green baseline for existing provider tests under `services/session-core/src/test/java/ai/assistanthub/core/provider/` (`FakeProviderInvocationTest.java`, `InvocationErrorTaxonomyTest.java`, `SecretMaskingTest.java`, `OpenAiCompatibleAdapterContractTest.java`, `AiProviderControllerTest.java`): **provider-only** tests MUST use `channelId=null` (may keep non-UUID `sessionId` strings); any test that keeps a non-null `channelId` MUST use T002 fixtures with real session UUID + seeded HubEvent — run `mvn test` in `services/session-core`

**Checkpoint**: Foundation ready — `InvocationResult` has `sourceType`; resolver works; invoke resolves or 422; suite existing green.

---

## Phase 3: User Story 1 - Atribuir resposta de IA à origem correta do canal (Priority: P1) 🎯 MVP

**Goal**: Resultado de invoke com canal ecoa `microphone` ou `system` resolvido no servidor (sucesso e falha de provedor).

**Independent Test**: Invocar hub com sessão+canal de origem conhecida (fixture de evento); resultado inclui `sourceType` canônico correto sem o chamador enviar origem; repetir para microfone e sistema; falha tipada de provedor ainda carrega origem.

### Tests for User Story 1

> After Phase 2 foundation is in place, these are contract/regression tests (not a strict fail-first gate).

- [x] T010 [P] [US1] Unit tests for resolver happy paths (`microphone`, `system`) using UUID session fixtures in `services/session-core/src/test/java/ai/assistanthub/core/provider/ChannelOriginResolverTest.java`
- [x] T011 [P] [US1] Contract tests: invoke success with channel → `result.sourceType()` matches session event; invoke provider failure after resolve still has `sourceType` in `services/session-core/src/test/java/ai/assistanthub/core/provider/InvocationSourceTypeContractTest.java` (FR-001, FR-003, SC-001); use UUID `sessionId` from T002

### Implementation for User Story 1

- [x] T012 [US1] Ensure success and failure paths in `services/session-core/src/main/java/ai/assistanthub/core/provider/InvocationService.java` always copy the pre-resolved `sourceType` into `InvocationResult` (including fallback-last-failure and no-enabled-provider branches)
- [x] T013 [US1] Confirm `InvocationRequest` / javadoc in `services/session-core/src/main/java/ai/assistanthub/core/provider/InvocationRequest.java` state that `sourceType` is server-resolved only (FR-010)
- [x] T014 [US1] Run focused suite for US1: `mvn test -Dtest=ChannelOriginResolverTest,InvocationSourceTypeContractTest,FakeProviderInvocationTest` in `services/session-core` and fix gaps until SC-001 holds for mic+system

**Checkpoint**: US1 independently demonstrable — canal com evento → origem correta no resultado.

---

## Phase 4: User Story 2 - Consumir o contrato de resultado sem surpresas (Priority: P1)

**Goal**: Contrato documentado + testes para N/A, rejeições e logs; comportamento inequívoco para integradores.

**Independent Test**: Suíte cobre sucesso/falha com canal, sem canal (`sourceType` null), 422 sem eventos / não canônico / conflito; revisor confirma contrato em `contracts/invocation-result-sourcetype.md`.

### Tests for User Story 2

- [x] T015 [P] [US2] Extend `services/session-core/src/test/java/ai/assistanthub/core/provider/InvocationSourceTypeContractTest.java`: no `channelId` → `sourceType` null and invoke may succeed (non-UUID `sessionId` allowed); `channelId` without events → `ChannelOriginUnresolvedException` (no provider call); invalid UUID `sessionId` with non-null `channelId` → same exception family (analyze U1)
- [x] T016 [P] [US2] Extend `services/session-core/src/test/java/ai/assistanthub/core/provider/ChannelOriginResolverTest.java`: non-canonical origin rejects; conflicting origins on same `channelId` reject; invalid UUID sessionId rejects (FR-011, FR-013)
- [x] T017 [P] [US2] Controller/API test for HTTP 422 on unresolved origin (and invalid session UUID with channel) in `services/session-core/src/test/java/ai/assistanthub/core/provider/AiProviderControllerTest.java` (or new focused test class under same package)

### Implementation for User Story 2

- [x] T018 [US2] Add `sourceType` to structured log line in `logInvocation` of `services/session-core/src/main/java/ai/assistanthub/core/provider/InvocationService.java` (value or null; never log `output`/`message`/secrets) — FR-012, SC-006
- [x] T032 [P] [US2] Automated log assertion for SC-006 in `services/session-core/src/test/java/ai/assistanthub/core/provider/InvocationSourceTypeLogTest.java` (or extend `InvocationSourceTypeContractTest.java`): with channel resolved, capture SLF4J/`ai-provider-invocation` log and assert it contains the same `sourceType` as `InvocationResult`; without channel, assert log does not invent a non-null origin (ListAppender or project-equivalent; no GPU) — analyze C1
- [x] T019 [US2] Align error messages in `ChannelOriginUnresolvedException` / resolver with distinct reasons (invalid UUID, no events, non-canonical, conflict) usable by T015–T017 in `services/session-core/src/main/java/ai/assistanthub/core/provider/`
- [x] T020 [US2] Verify contract doc still matches implementation: `specs/017-issue-40-invocation-sourcetype/contracts/invocation-result-sourcetype.md` (update only if wire names/status codes differ; keep FR-007 reviewer path; document invalid UUID → 422 when channel present)
- [x] T021 [US2] Run `mvn test` in `services/session-core` covering US2 scenarios from `specs/017-issue-40-invocation-sourcetype/quickstart.md` table rows for N/A and 422 cases (include T032)

**Checkpoint**: US2 — contrato testável e documentado; logs com origem; fail-closed coberto.

---

## Phase 5: User Story 3 - Não misturar origens entre canais da mesma sessão (Priority: P2)

**Goal**: Isolamento por `channelId` na mesma sessão (sequencial e concorrente).

**Independent Test**: Sessão com canal A (mic) e B (system); invokes por canal devolvem apenas a origem daquele canal; zero contaminação (SC-002).

### Tests for User Story 3

- [x] T022 [P] [US3] Multi-channel sequential isolation test in `services/session-core/src/test/java/ai/assistanthub/core/provider/InvocationSourceTypeContractTest.java` (or `InvocationSourceTypeIsolationTest.java`): same `sessionId`, `mic-1`→`microphone`, `sys-1`→`system`
- [x] T023 [P] [US3] Concurrent invokes on two channels in same session assert each `InvocationResult.sourceType` matches its channel in `services/session-core/src/test/java/ai/assistanthub/core/provider/InvocationSourceTypeContractTest.java` (FR-004)

### Implementation for User Story 3

- [x] T024 [US3] Review `ChannelOriginResolver` filtering in `services/session-core/src/main/java/ai/assistanthub/core/provider/ChannelOriginResolver.java` to ensure only events for the requested `channelId` contribute (no session-wide default / first-channel leak) — fix if T022/T023 fail
- [x] T025 [US3] Run focused isolation tests + full `mvn test` in `services/session-core` until SC-002 holds

**Checkpoint**: US3 — multi-canal isolado; todas as stories cobertas no core.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Clientes desktop, débito tracking, validação quickstart.

- [x] T026 [P] Add optional `sourceType` to `InvocationResult` in `apps/desktop-shell/src/api-client.ts` (no request field)
- [x] T027 [P] Add optional `source_type` / wire `sourceType` on `InvocationResult` in `apps/desktop-shell/src-tauri/src/ai_provider_client.rs` (serde skip if none; `InvokeRequest` unchanged)
- [x] T028 [P] Run desktop type checks if available: `npm test` in `apps/desktop-shell` and/or `cargo test` in `apps/desktop-shell/src-tauri` (non-blocking for core MVP if environment missing — note in PR)
- [x] T029 Note debt resolution for `InvocationResult-sourceType` in `CHANGELOG.md` (or next-release notes section) linking issue #40 — FR-009; do **not** auto-close issue / tag product (P8)
- [x] T030 Execute quickstart validation checklist in `specs/017-issue-40-invocation-sourcetype/quickstart.md` (table scenarios + `mvn test` in `services/session-core`) and record results in PR description
- [x] T031 Final scan: no `sourceType` on invoke **request** DTOs; no secrets/output in logs; grep constructors of `InvocationResult` under `services/session-core` for missing `sourceType` argument

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: immediate
- **Phase 2 (Foundational)**: after Setup — **blocks** US1–US3
- **Phase 3 (US1)**: after Foundational — **MVP**
- **Phase 4 (US2)**: after Foundational; ideally after US1 result field is stable (shares `InvocationSourceTypeContractTest`)
- **Phase 5 (US3)**: after Foundational; benefits from US1 contract test file existing
- **Phase 6 (Polish)**: after desired stories (desktop can start after T003 API shape stable)

### User Story Dependencies

| Story | Depends on | Notes |
|-------|------------|-------|
| US1 | Phase 2 | MVP; no dependency on US2/US3 |
| US2 | Phase 2 (+ US1 file patterns helpful) | Contract/N/A/422/logs |
| US3 | Phase 2 | Isolation; uses same resolver as US1 |

### Within Each Story

- Prefer tests (T010–T011, T015–T017, T022–T023) before or with implementation verification
- Resolver before invoke wiring (already in Phase 2)
- Story checkpoint before next priority when sequential

### Parallel Opportunities

- T002 ∥ T001 (setup)
- T004 ∥ T003 (exception vs result field)
- T010 ∥ T011 (US1 tests)
- T015 ∥ T016 ∥ T017 (US2 tests)
- T022 ∥ T023 (US3 tests)
- T026 ∥ T027 ∥ T029 (polish types/docs)
- After Phase 2, US2 log work (T018) can proceed while US1 tests finish if staffed carefully (same `InvocationService.java` — **serialize** edits to that file)

---

## Parallel Example: User Story 1

```bash
# After Phase 2 complete, in parallel:
# - ChannelOriginResolverTest happy paths
# - InvocationSourceTypeContractTest success + provider failure preserve sourceType
Task: T010 [US1] ChannelOriginResolverTest.java
Task: T011 [US1] InvocationSourceTypeContractTest.java

# Then sequential verification:
Task: T012–T014 [US1] InvocationService branches + mvn test
```

## Parallel Example: User Story 2

```bash
Task: T015 no-channel + unresolved + invalid UUID invoke tests
Task: T016 non-canonical + conflict + invalid UUID resolver tests
Task: T017 controller 422 tests
# Then T018 log (InvocationService) — exclusive file lock with other InvocationService tasks
# Then T032 log assertion (can run after T018; parallel with T019–T020 if different files)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup (T001–T002)  
2. Phase 2 Foundational (T003–T009) — critical  
3. Phase 3 US1 (T010–T014)  
4. **STOP**: validate mic/system on `InvocationResult`  
5. Demo/PR draft possible for #40 core debt  

### Incremental Delivery

1. MVP US1 → origin on successful/failed invoke with channel  
2. US2 → contract completeness (N/A, 422, logs, docs)  
3. US3 → multi-channel isolation  
4. Polish → desktop types + changelog + quickstart evidence  

### Parallel Team Strategy

1. Together: Phase 1–2  
2. Dev A: US1 tests/impl  
3. Dev B: US2 tests + controller (avoid simultaneous `InvocationService` edits)  
4. Dev C: desktop T026–T027 after T003 shape known  
5. One owner: T030–T031  

---

## Notes

- [P] = different files / no incomplete deps  
- Do not add `sourceType` to invoke **request**  
- Failures of origin are **422**, not provider fallback  
- Canonical set fixed: `microphone`, `system`  
- **U1:** With non-null `channelId`, `sessionId` MUST be a valid UUID string; invalid UUID → `ChannelOriginUnresolvedException` / HTTP 422 (never uncaught parse errors). Without channel, non-UUID `sessionId` remains allowed for provider-only tests.  
- **C1:** SC-006 requires automated log assertion (T032), not only T018 implementation.  
- Close issue #40 only via human process after merge (P8)  
- Suggested MVP: **T001–T014** (Phases 1–3)

---

## Task Summary

| Phase | Task IDs | Count |
|-------|----------|-------|
| Setup | T001–T002 | 2 |
| Foundational | T003–T009 | 7 |
| US1 | T010–T014 | 5 |
| US2 | T015–T021, T032 | 8 |
| US3 | T022–T025 | 4 |
| Polish | T026–T031 | 6 |
| **Total** | T001–T032 (T032 after T018) | **32** |

| Story | Tasks | Count |
|-------|-------|-------|
| US1 | T010–T014 | 5 |
| US2 | T015–T021, T032 | 8 |
| US3 | T022–T025 | 4 |
| (shared/setup/polish) | T001–T009, T026–T031 | 15 |
