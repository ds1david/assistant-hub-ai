# Tasks: Secure credential store (#64)

**Input**: `specs/029-issue-64-secure-credentials/`  
**Issue**: [#64](https://github.com/ds1david/assistant-hub-ai/issues/64)  
**Tests**: Required (FR-008, SC-001)

## Phase 1: Setup

- [x] T001 Confirm feature dir `specs/029-issue-64-secure-credentials` + branch `feature/issue-64-secure-credential-store`
- [x] T002 [P] Inventory secret paths: `EnvSecretResolver`, provider auth DTO, `ai-provider-panel.ts`, Tauri invoke client
- [x] T003 [P] Baseline: `mvn -pl services/session-core -am test` subset secrets + `cd apps/desktop-shell && npm test -- --run`

## Phase 2: Foundational — store port

- [x] T004 Implement `SecureSecretStore` trait + `MemorySecureSecretStore` in `apps/desktop-shell/src-tauri/src/secure_store.rs`
- [x] T005 [P] Unit tests memory store put/get/delete/list in `secure_store.rs` or `tests/`
- [x] T006 Implement `OsSecureSecretStore` (keyring; cfg windows or graceful Err on unsupported)
- [x] T007 Tauri commands put/delete/list_ids/has (**no get to JS**) in `apps/desktop-shell/src-tauri/src/` + register in `lib.rs`/`main.rs`
- [x] T008 TS wrappers in `apps/desktop-shell/src/api-client.ts` (put/delete/list/has only)

## Phase 3: US1 — Save key in OS store (P1)

- [x] T009 [P] [US1] UI tests: save flow sets secretRef `os:…` and does not retain plaintext in form state (`tests/ai-provider-panel.test.ts` or new)
- [x] T010 [US1] Wire password field → put + save provider with `os:assistant-hub/providers/{id}` in `ai-provider-panel.ts` / `main.ts`
- [x] T011 [US1] Delete secret control when provider deleted or explicit clear

## Phase 4: US2 — Invoke/test with os: (P1)

- [x] T012 [US2] Resolve `os:` in Rust path of `test_ai_provider_connection` / `invoke_ai_provider` (research R2; redaction on errors)
- [x] T013 [P] [US2] Tests with memory store: has secret → invoke path receives resolution; missing → SECRET_NOT_FOUND safe message
- [x] T014 [US2] Ensure live-answer shell invoke path uses same resolver

## Phase 5: US3 — Docs + env regression (P2)

- [x] T015 [P] [US3] Update `docs/security/provider-secrets.md` with put/list/delete flows and Windows notes
- [x] T016 [P] [US3] Cross-link running.md / packaging if needed
- [x] T017 [US3] Confirm session-core `env:` tests still green

## Phase 6: Polish

- [x] T018 Mark 002/003 tasks checkboxes for secrets when done
- [x] T019 Full shell + cargo tests green
- [x] T020 Summarize residual risks (signing not in scope; Linux OS store optional)

## MVP

T001–T014 (store + UI + resolve).
