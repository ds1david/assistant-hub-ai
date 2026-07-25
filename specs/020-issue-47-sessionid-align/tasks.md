# Tasks: Alinhar sessionId UI↔agent e disparo só em transcript final

**Input**: Design documents from `/specs/020-issue-47-sessionid-align/`

**Prerequisites**: plan.md, spec.md (clarify Q1–Q5), research.md, data-model.md, contracts/session-align-shell.md, quickstart.md

**Tests**: Incluídos — FR-011 / SC-001–SC-004 e plan Testing exigem vitest + `cargo test` (parse cmdline, alignment, empty states, start com sessão ativa, regressão Final elegível).

**Organization**: Tasks grouped by user story (US1 → US2 → US3 → US4) after shared foundation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3 / US4 maps to spec user stories
- Paths are repo-relative from monorepo root

## Path Conventions

- Shell TS: `apps/desktop-shell/src/`, tests: `apps/desktop-shell/tests/`
- Shell Rust: `apps/desktop-shell/src-tauri/src/`
- Docs: `docs/development/running.md`, `docs/release/min-flow.md`
- Feature docs: `specs/020-issue-47-sessionid-align/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inventário e baseline sem nova stack; monorepo e shell já existem.

- [x] T001 Review design docs in `specs/020-issue-47-sessionid-align/` (spec FR-001–FR-016 + clarify Q1–Q5, plan.md, research.md Decisions 1–10, data-model.md, contracts/session-align-shell.md, quickstart.md) and list current gaps in `apps/desktop-shell/src-tauri/src/agent_control.rs`, `apps/desktop-shell/src-tauri/src/main.rs` (`get_agent_status`/`start_agent`/`stop_agent`), `apps/desktop-shell/src/agent-panel.ts`, `apps/desktop-shell/src/main.ts`, `apps/desktop-shell/src/assistant-panel.ts`
- [x] T002 [P] Run baseline green: `npx vitest run` in `apps/desktop-shell` and `cargo test` in `apps/desktop-shell/src-tauri` (lib only, no `gui`); record any pre-existing failures before changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Resolução de sessão do agent + tipos TS + pure alignment/empty helpers — bloqueia US1–US3.

**⚠️ CRITICAL**: Nenhuma user story de UI completa sem esta fase.

- [x] T003 Extend `AgentStatus` in `apps/desktop-shell/src-tauri/src/agent_control.rs` with `agent_session_id: Option<String>` and `agent_session_source: AgentSessionSource` (`Cmdline` | `Managed` | `Unknown`, serde camelCase) per `specs/020-issue-47-sessionid-align/contracts/session-align-shell.md` and `data-model.md`
- [x] T004 Implement pure `parse_session_from_cmd(args: &[OsString]) -> Option<String>` in `apps/desktop-shell/src-tauri/src/agent_control.rs` (support `--session <id>` and defensive `--session=<id>`; empty/missing → None; last wins if repeated)
- [x] T005 Implement `resolve_agent_session(running, cmdline_id, last_managed_id, has_managed_handle) -> (Option<String>, AgentSessionSource)` in `apps/desktop-shell/src-tauri/src/agent_control.rs` with priority cmdline → managed (Direct) → unknown; never invent id
- [x] T006 Add `detect_agent_cmdline_session() -> Option<String>` in `apps/desktop-shell/src-tauri/src/agent_control.rs` using `sysinfo` process match (`process_matches_agent`) + `Process::cmd()` + T004; first match with parseable `--session` wins
- [x] T007 Wire `AppState` in `apps/desktop-shell/src-tauri/src/main.rs`: field `last_managed_session_id: Mutex<Option<String>>`; set on successful `start_agent`; clear on successful `stop_agent`; fill `AgentStatus` in `get_agent_status` / `start_agent` / error paths via T005–T006. **Analyze I1 (obrigatório)**: em `get_agent_status`, se o agent **não** está em execução (`!running`), `control_mode` MUST ser `Direct` (shell pode iniciar) — **não** reportar `Guided` só porque não há handle; `Guided` só quando `running && !has_managed_handle`
- [x] T008 Ensure `start_agent` in `apps/desktop-shell/src-tauri/src/main.rs` still spawns `assistant-hub-audio run --session <session_id> --profile <profile_path>` and returns status with `agent_session_id` = that `session_id` and source `Managed` (or cmdline if immediately visible); **MUST NOT** kill external processes on AlreadyRunning
- [x] T009 [P] Extend TypeScript `AgentStatus` in `apps/desktop-shell/src/api-client.ts` with `agentSessionId: string | null` and `agentSessionSource: "cmdline" | "managed" | "unknown"` (camelCase match serde)
- [x] T010 [P] Create pure module `apps/desktop-shell/src/session-alignment.ts` exporting `AlignmentState`, `resolveAlignment(activeSessionId, agent)`, `AssistantEmptyKind`, `resolveAssistantEmptyKind(...)` per `data-model.md` / FR-010 precedence (mismatch → prefs off / no origin → empty feed → awaiting final → no eligible question). **I4**: feed vazio → `awaiting_transcript` (não `awaiting_final`); `awaiting_final` só com ≥1 Partial e sem Final elegível. Reuse `looksLikeQuestion` from `apps/desktop-shell/src/assistant-auto.ts` for finals eligibility + origin filter
- [x] T011 [P] Unit tests for T004–T005 in `apps/desktop-shell/src-tauri/src/agent_control.rs` (`#[cfg(test)]`): parse vectors; resolution priority; no invent
- [x] T012 [P] Unit tests for T010 in `apps/desktop-shell/tests/session-alignment.test.ts`: all `AlignmentState` cases; empty-kind precedence FR-010 including **empty feed ≠ awaiting_final** (I4)

**Checkpoint**: Foundation ready — Rust resolve + TS pure alignment/empty; `cargo test` + vitest alignment green.

---

## Phase 3: User Story 1 - Iniciar ou reiniciar o agent com a sessão ativa (Priority: P1) 🎯 MVP

**Goal**: Start (e restart controlável) sempre usa o UUID da sessão ativa; sem sessão → bloqueado; guidance usa sessão ativa.

**Independent Test**: Com sessão ativa `S`, start pela UI (ou callback fake) passa `S`; sem sessão não inicia; comando guiado contém `--session S`.

### Tests for User Story 1

- [x] T013 [P] [US1] Extend `apps/desktop-shell/tests/agent-panel.test.ts`: (a) stopped + Direct + activeSession → `agent-start-button` fires `onStart`; (b) **Analyze I1**: stopped + `controlMode` como o status real pós-T007 (Direct quando parado) + activeSession → Start **visível** (nunca só Guided quando parado); guidance com session id
- [x] T014 [P] [US1] Add tests in `apps/desktop-shell/tests/agent-panel.test.ts` (or new `session-start-guards.test.ts`): no active session → start disabled/hidden + orientação para selecionar/criar sessão; assert testids (FR-003)

### Implementation for User Story 1

- [x] T015 [US1] Update `renderAgentPanel` in `apps/desktop-shell/src/agent-panel.ts` to accept `activeSessionId: string | null` (+ alignment props as needed); show UI/agent session ids; **I1**: botão Iniciar quando `!running && activeSessionId` (compatível com status Direct parado de T007); disable/hide start when `activeSessionId` null with clear orientation (FR-003)
- [x] T016 [US1] Wire `refreshAgentPanel` / start handler in `apps/desktop-shell/src/main.ts`: call `startAgent(activeSessionId, DEFAULT_PROFILE_PATH)` only when `activeSessionId` set; always fill `guidanceCommand` on paint as `assistant-hub-audio run --session <active> --profile <DEFAULT_PROFILE_PATH>` when active session set (single source of truth no webview — analyze I6)
- [x] T017 [US1] Implement **exported** `restartAgentWithActiveSession` (or pure helper with injectável `stop`/`start`) in `apps/desktop-shell/src/main.ts` or `apps/desktop-shell/src/agent-session-actions.ts`: if Direct + running + activeSessionId → `stopAgent()` then `startAgent(activeSessionId, DEFAULT_PROFILE_PATH)` **without** confirm (FR-002/FR-016/Q5); Guided → no-op/error path, no kill
- [x] T018 [US1] **Analyze I2**: unit test in `apps/desktop-shell/tests/agent-session-actions.test.ts` (or equivalent): mock stop/start → restart chama stop depois start com o **mesmo** `activeSessionId` (FR-011(g)); then run `npx vitest run tests/agent-panel.test.ts tests/session-alignment.test.ts tests/agent-session-actions.test.ts` in `apps/desktop-shell` and `cargo test` in `apps/desktop-shell/src-tauri` until SC-001 holds

**Checkpoint**: US1 — start/restart Direct usa sessão ativa; bloqueio sem sessão; guidance coerente.

---

## Phase 4: User Story 2 - Ver mismatch de sessão e corrigir (Priority: P1) 🎯 MVP

**Goal**: Banner de mismatch quando ids conhecidos divergem; CTA restart Direct; Guided sem force-kill + orientação manual; select não reinicia sozinho.

**Independent Test**: Fakes: match → sem banner; mismatch → banner + CTA; stopped → sem banner mismatch; Guided externo → manual stop hint; select session only updates feed/alignment not process.

### Tests for User Story 2

- [x] T019 [P] [US2] Extend `apps/desktop-shell/tests/agent-panel.test.ts`: `session-mismatch-banner` present only when mismatched; absent when aligned or agent stopped; `agent-restart-active-button` present when Direct+mismatched and fires `onRestart` without confirm; **I5 opcional**: caso com `agentSessionSource: "cmdline"` + ids divergentes ainda mostra banner (FR-011(b))
- [x] T020 [P] [US2] Extend `apps/desktop-shell/tests/agent-panel.test.ts`: Guided + **running** shows `agent-guidance` / `agent-manual-stop-hint` and does **not** expose restart that implies force-kill (FR-015); stopped never uses this branch for “only Guided” (I1)
- [x] T021 [P] [US2] **Analyze I3 (obrigatório)**: teste automatizado em `apps/desktop-shell/tests/` que prova FR-009/FR-011(f) — extrair helper puro (ex. `onSessionSelected(activeId, agentActions)`) ou exportar lógica de `selectSession` de forma testável: ao trocar sessão **não** invoca `stopAgent`/`startAgent`/`restartAgentWithActiveSession`; apenas troca id ativo / estado de UI. **Proibido** “só documentar” sem assert

### Implementation for User Story 2

- [x] T022 [US2] Render in `apps/desktop-shell/src/agent-panel.ts`: agent session id display (`agent-session-id`), optional `ui-session-id`, `session-mismatch-banner` when `resolveAlignment` → `mismatched`, CTA `agent-restart-active-button` when Direct+mismatched+running → `onRestart` (FR-006/FR-007/FR-008/FR-016)
- [x] T023 [US2] Guided recovery copy in `apps/desktop-shell/src/agent-panel.ts`: when **running**+Guided, show command with **active** session id + explicit manual stop then start (FR-015); never call kill APIs for external
- [x] T024 [US2] Wire poll/`refreshAgentPanel` in `apps/desktop-shell/src/main.ts`: pass `activeSessionId`, full `AgentStatus`, `resolveAlignment`, bind `onRestart` → T017; `selectSession` only changes feed/prefs/alignment (FR-009) and surfaces mismatch after paint — structure so T021 can spy stop/start
- [x] T025 [US2] Confirm `stop_agent` in `apps/desktop-shell/src-tauri/src/main.rs` still errors when no managed handle (no process kill by name); status for external agent may still expose cmdline `agentSessionId` for mismatch
- [x] T026 [US2] Run `npx vitest run tests/agent-panel.test.ts tests/session-alignment.test.ts tests/agent-session-actions.test.ts` (e o teste de T021) and `cargo test` in `apps/desktop-shell/src-tauri` until SC-002 holds

**Checkpoint**: US2 — mismatch visível e corrigível em Direct; Guided seguro; select não auto-restart.

---

## Phase 5: User Story 3 - Estados vazios do Assistente / aguardando final (Priority: P2)

**Goal**: Empty states distintos no painel Assistente; Final elegível ainda dispara (019); mismatch tem prioridade sobre “aguardando final”.

**Independent Test**: Fixtures de feed: só partials → `awaiting_final`; empty feed → `awaiting_transcript`; finals não-pergunta → `no_eligible_question`; auto off → prefs; mismatch → `session_mismatch`; Final pergunta+system → turn criado.

### Tests for User Story 3

- [x] T027 [P] [US3] Extend `apps/desktop-shell/tests/assistant-panel.test.ts` for each `AssistantEmptyKind` via `data-testid="assistant-empty"` + `data-empty-kind` (or `assistant-empty-kind`) per contract
- [x] T028 [P] [US3] Regression in `apps/desktop-shell/tests/assistant-auto.test.ts`: Final sintético pergunta + `sourceType=system` + auto on → cria interação (running/done/error); Partial only → **no** new turn (019 FR-003)

### Implementation for User Story 3

- [x] T029 [US3] Update `renderTurns` / empty rendering in `apps/desktop-shell/src/assistant-panel.ts` to accept `emptyKind: AssistantEmptyKind | null` and render distinct PT copy + `data-empty-kind` (replace single generic empty when kind applies) — FR-010
- [x] T030 [US3] Compute empty kind in `apps/desktop-shell/src/main.ts` (or thin helper): when turns empty, call `resolveAssistantEmptyKind` with alignment from agent status, prefs, and latest transcript feed entries; pass into `renderAssistantPanel`
- [x] T031 [US3] Ensure precedence: if alignment `mismatched`, empty kind is `session_mismatch` even if feed has partials (US3 scenario 4); prefs off wins over awaiting_final
- [x] T032 [US3] Run `npx vitest run tests/assistant-panel.test.ts tests/assistant-auto.test.ts tests/session-alignment.test.ts` until SC-003/SC-004 hold

**Checkpoint**: US3 — diagnóstico de empty states; orquestração 019 intacta em Final elegível.

---

## Phase 6: User Story 4 - Documentação da regra do sessionId único (Priority: P2)

**Goal**: Docs operacionais com regra do mesmo sessionId, select ≠ reconfig agent, exemplo PowerShell/UI restart.

**Independent Test**: Revisor encontra as regras em &lt;2 min (SC-005) em `running.md` e/ou `min-flow.md`.

### Implementation for User Story 4

- [x] T033 [P] [US4] Update `docs/development/running.md` section on shell/agent/Assistente: same `sessionId` UI↔agent↔STT; selecting session in list does **not** reconfigure running agent; prefer UI start/restart (Direct); PowerShell/`run-audio-agent-foreground.ps1` example with UI active UUID; Guided = manual stop + command with UI UUID; note finals vs partials for Assistente (FR-012)
- [x] T034 [P] [US4] Update `docs/release/min-flow.md` with the same sessionId alignment rules (cross-link `running.md` if appropriate) without bloating release checklist
- [x] T035 [US4] Cross-check wording against `specs/020-issue-47-sessionid-align/quickstart.md` manual pass criteria; adjust quickstart only if doc paths/steps diverge

**Checkpoint**: US4 — docs acionáveis para o workaround e o fluxo correto.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Suite completa, privacidade, consistência de testids.

- [x] T036 Run full shell verification: `npx vitest run` in `apps/desktop-shell` and `cargo test` in `apps/desktop-shell/src-tauri`; fix regressions from AgentStatus shape changes in any leftover tests/fixtures
- [x] T037 [P] Audit logs/UI: no secrets, raw audio, or full model output introduced in changed files under `apps/desktop-shell/` (FR-014 / P9)
- [x] T038 [P] Verify testids in `specs/020-issue-47-sessionid-align/contracts/session-align-shell.md` match implementation (`session-mismatch-banner`, `agent-restart-active-button`, `agent-session-id`, empty kinds)
- [x] T039 Confirm FR-013: no edits to `contracts/transcript-event.v2.schema.json` or agent Python CLI contracts in this feature
- [x] T040 Final pass of `specs/020-issue-47-sessionid-align/quickstart.md` automated section; mark any Windows-only rows as manual

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: start immediately
- **Phase 2 (Foundational)**: after Setup — **blocks** US1–US3
- **Phase 3 (US1)**: after Phase 2 — MVP start path
- **Phase 4 (US2)**: after Phase 2; ideally after US1 restart helper (T017) — can start panel tests earlier
- **Phase 5 (US3)**: after Phase 2 (`session-alignment` empty kinds); uses alignment from US2 in main wiring
- **Phase 6 (US4)**: can run in parallel with US3 after product behavior is clear; docs-only
- **Phase 7 (Polish)**: after desired stories complete

### User Story Dependencies

| Story | Depends on | Notes |
|-------|------------|--------|
| US1 | Phase 2 | Start/restart with active id |
| US2 | Phase 2, T017 (restart) | Mismatch UI + CTA |
| US3 | Phase 2; alignment from US2 for full precedence | Empty states |
| US4 | None code-wise | Docs; best after US1–US2 behavior frozen |

### Parallel Opportunities

- T002 ‖ T001 (after T001 list started)
- T009 ‖ T010 ‖ T011 ‖ T012 after T003–T008 shapes stable (T011 needs T004–T005; T012 needs T010)
- T013 ‖ T014 (US1 tests)
- T019 ‖ T020 ‖ T021 (US2 tests)
- T027 ‖ T028 (US3 tests)
- T033 ‖ T034 (US4 docs)
- T037 ‖ T038 ‖ T039 (polish)

---

## Parallel Example: User Story 2

```bash
# After foundation + T017:
# Terminal A
npx vitest run tests/agent-panel.test.ts   # T019–T020 implementations under test

# Terminal B  
# Edit agent-panel.ts mismatch CTA (T022–T023) while main.ts wiring (T024) waits on panel API
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Phase 1 Setup  
2. Phase 2 Foundation (Rust resolve + TS pure)  
3. Phase 3 US1 (start/restart with active session)  
4. Phase 4 US2 (mismatch + CTA)  
5. **STOP and VALIDATE** automated suite + optional Windows quickstart rows for alignment  

### Incremental Delivery

1. MVP (US1+US2) → operator can realign sessions  
2. US3 → empty-state diagnosis for partials  
3. US4 → docs prevent regression of ops knowledge  
4. Polish → full green + contract testids  

### Suggested MVP scope

**US1 + US2 only** (plan MVP). US3 and US4 are small and should ship in the same PR if capacity allows (issue #47 P1 empty-hint + docs).

---

## Notes

- [P] = different files / no incomplete deps  
- Do **not** force-kill external agent processes (clarify Q2 / FR-015)  
- Do **not** confirm-dialog on restart CTA (Q5)  
- Do **not** auto-restart on session select (FR-009)  
- Reuse `DEFAULT_PROFILE_PATH` in `apps/desktop-shell/src/main.ts` — no profile picker in this feature  
- Commit after each task or logical group; G1/G2 human gates per constitution before merge  
- Avoid: transcript schema edits, session-core changes, multi-agent  

### Remediações pós-`/speckit-analyze` (2026-07-25)

| ID | Severidade | Onde | Correção aplicada nos tasks/artefatos |
|----|------------|------|----------------------------------------|
| I1 | HIGH | `controlMode` parado = Guided escondia Start | T007/T013/T015: `!running` → Direct; Start visível |
| I2 | MEDIUM | CTA realinha id sem teste de helper | T017 exportável + T018 unit test stop→start |
| I3 | MEDIUM | T021 podia “só documentar” | T021 exige assert automatizado (sem documentação-only) |
| I4 | MEDIUM | `awaiting_final` vs feed vazio | T010/T012 + data-model alinhados a FR-010 |
| I5 | LOW | FR-011(b) cmdline | T019 caso opcional com `agentSessionSource: "cmdline"` |
| I6 | LOW | guidance duplo caminho | T016: webview preenche guidance no paint |

---

## Task summary

| Phase | Tasks | Count |
|-------|-------|-------|
| Setup | T001–T002 | 2 |
| Foundational | T003–T012 | 10 |
| US1 | T013–T018 | 6 |
| US2 | T019–T026 | 8 |
| US3 | T027–T032 | 6 |
| US4 | T033–T035 | 3 |
| Polish | T036–T040 | 5 |
| **Total** | T001–T040 | **40** (reforçados pós-analyze; IDs estáveis) |
