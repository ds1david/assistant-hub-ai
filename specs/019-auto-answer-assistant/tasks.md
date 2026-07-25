---
description: "Task list for Assistente de respostas automáticas no desktop (live-answer)"
---

# Tasks: Assistente de respostas automáticas no desktop (live-answer)

**Input**: Design documents from `/specs/019-auto-answer-assistant/`

**Prerequisites**: plan.md, spec.md (clarify 5 Qs), research.md, data-model.md, contracts/auto-answer-shell.md, quickstart.md

**Tests**: Incluídos — FR-018 / SC-002–005 / SC-008–010 e constituição P10 exigem suíte determinística (vitest + JUnit + cargo test da lib) sem GPU/WASAPI na suíte padrão.

**Organization**: Fases por user story (US1–US4). Orquestração no shell; session-core só ganha `GET /api/sessions`. Protótipo em `apps/desktop-shell/src/assistant-*.ts` deve ser **reconciliado** com a spec (não aceito “como está”).

**Remediação pós-analyze (2026-07-25)**: C1 persist prefs on change · C2 MVP = US1+US2 · C3 estado `queued` na UI · C4 Assistente sem sessão/core down · C5 defaults de create session · C6 ordem de turns mais recente primeiro · C8 T006 sem `[P]` indevido.

**Remediação analyze #2 (2026-07-25)**: A1 FR-004 canônica · A2 FR-028/029 + SC-012 · A3 prefs Rust obrigatório · A4 sessão explícita na US1 · A5 FR-018 + FR-010 · A6 FR-021 fundido em FR-002 · A7 US4 polish gap-only · A8 Status Ready · A9 glossário entidades · A10 SC-006 no quickstart.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: US1–US4 conforme spec.md
- Caminhos relativos à raiz do monorepo

## Path Conventions

- Backend: `services/session-core/src/main/java/ai/assistanthub/core/session/` e `.../src/test/java/...`
- Desktop Rust: `apps/desktop-shell/src-tauri/src/`, testes em `apps/desktop-shell/src-tauri/tests/`
- Desktop TS: `apps/desktop-shell/src/`, testes em `apps/desktop-shell/tests/`

### Constantes de produto (fixas)

| Item | Valor |
|------|--------|
| Rota invoke | `live-answer` |
| Capability | `chat` |
| Create session `title` | `Sessão local` (FR-028) |
| Create session `profileId` | `interview-technical` (FR-028) |
| Ordem dos turns no painel | **mais recente primeiro** (FR-029 / SC-012) |
| Contexto recente | ≤12 trechos finais **ou** ≤4000 chars |
| Prefs defaults | `autoEnabled=false`, `enabledSourceTypes=["system"]`, `inputMode="question-plus-recent-context"` |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Alinhar workspace ao plan e inventariar protótipo vs spec

- [x] T001 Auditar protótipo `apps/desktop-shell/src/assistant-auto.ts`, `assistant-panel.ts` e trechos de `apps/desktop-shell/src/main.ts` contra FR-004 / FR-020–029 / clarify; listar gaps (heurística FR-004, origens, inputMode, prefs por sessão + **save on change**, listagem de sessões, defaults create FR-028, ordem turns FR-029) em comentário de cabeçalho ou nota curta no PR
- [x] T002 [P] Garantir âncora `#assistant-panel` e âncora/contêiner de sessão (ex. `#session-picker`) em `apps/desktop-shell/index.html` alinhados a `contracts/auto-answer-shell.md`
- [x] T003 [P] Confirmar que `config/ai-providers.yaml` (ou sample) define rota `live-answer` com primary/fallbacks utilizáveis; não commitar segredos

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: API de listagem de sessões, clientes Tauri/TS, store de prefs e núcleo puro de orquestração — **bloqueia** todas as user stories

**⚠️ CRITICAL**: Nenhuma user story de UI completa começa antes desta fase

- [x] T004 Expor listagem em `services/session-core/src/main/java/ai/assistanthub/core/session/SessionRepository.java` — método `list()` / `findAll()` reutilizando cache em memória (rehidratado) e/ou `SessionPersistenceStore.findAllSessions()`
- [x] T005 Adicionar `GET /api/sessions` em `services/session-core/src/main/java/ai/assistanthub/core/session/SessionController.java` retornando `List<ConversationSession>` (array vazio ok; ordenação `createdAt` **desc**) — contrato `contracts/auto-answer-shell.md`
- [x] T006 Teste JUnit `services/session-core/src/test/java/ai/assistanthub/core/session/SessionListApiTest.java` (ou nome equivalente) — **após T004–T005**; cria 0/N sessões e valida `GET /api/sessions` (FR-026 / quickstart §2)
- [x] T007 Completar `create_session` e adicionar `list_sessions` em `apps/desktop-shell/src-tauri/src/session_core_client.rs` + registro em `apps/desktop-shell/src-tauri/src/main.rs` (`list_sessions`, `create_session`)
- [x] T008 [P] Testes cargo de list/create em `apps/desktop-shell/src-tauri/tests/` (servidor HTTP fake local, padrão `ai_provider_client_tests.rs`)
- [x] T009 [P] Wrappers TS `listSessions` / `createSession` em `apps/desktop-shell/src/api-client.ts` alinhados ao contrato
- [x] T010 Implementar store de preferências por sessão em `apps/desktop-shell/src-tauri/src/assistant_prefs.rs` (JSON no app config dir; mapa `sessionId → AssistantSessionPreferences` de data-model.md) + comandos Tauri **load e save** (`get_assistant_prefs` / `set_assistant_prefs` ou equivalente); registrar em `lib.rs` / `main.rs`
- [x] T011 [P] Tipos/defaults TS e wrapper em `apps/desktop-shell/src/assistant-prefs.ts` — defaults da tabela acima; API `loadPrefs(sessionId)` / `savePrefs(sessionId, prefs)` usada pela UI
- [x] T012 Núcleo puro em `apps/desktop-shell/src/assistant-auto.ts`: `looksLikeQuestion` conforme **FR-004** (min 8 chars, `?` ou prefixos canônicos pt/en), filtro de origem (origem desconhecida = inelegível; FR-002), `extractNewQuestions`, builder de `input` (`question-only` vs contexto ≤12 finais / 4000 chars), `AssistantAutoController` com generation token e API `ingestTranscript` / `setPrefs` / `getView` / status `queued` — **sem** acoplar DOM; reconciliar protótipo existente
- [x] T013 [P] Testes unitários base em `apps/desktop-shell/tests/assistant-auto.test.ts` — cobertura explícita FR-004 (aceita `?` e prefixos pt/en ≥8 chars; rejeita `"ok"`, `"sim"`, `"entendi"`, sem prefixo, &lt;8 chars), parcial, origem mic com default system-only, origem desconhecida inelegível, idempotência por `eventId`, builder dos dois `inputMode` (FR-004/018/020–024)

**Checkpoint**: `GET /api/sessions` + clientes + prefs load/save + controller puro testáveis sem UI completa

---

## Phase 3: User Story 1 — Respostas automáticas no painel (Priority: P1) 🎯 parte do MVP

**Goal**: Com automático ligado, trecho final elegível dispara `live-answer`/`chat` e o painel Assistente mostra pergunta, estados (incl. fila quando aplicável) e resposta ou erro. Prefs da sessão **persistem** a cada mudança na UI.

**Independent Test**: Sessão ativa + feed com Final pergunta em origem habilitada + invoke fake/real → painel mostra interação sem “testar conexão” (spec US1 / SC-001). Toggle origens/modo/auto → save → reload store mantém valores (FR-025). US1 pode usar `createSession`/`listSessions` via API **ou** botão mínimo de criar; o seletor completo (lista + id visível) permanece US3 (T028–T030).

### Tests for User Story 1

- [x] T014 [P] [US1] Estender `apps/desktop-shell/tests/assistant-auto.test.ts` — disparo idle→running→done com `invoke` mock; automático desligado não invoca (SC-005)
- [x] T015 [P] [US1] Testes de painel em `apps/desktop-shell/tests/assistant-panel.test.ts` — empty state, toggle, origens, modo de entrada, turns com `data-status` em `{running,done,error,queued,cancelled}`, resposta `done` (data-testids do contrato)
- [x] T016 [P] [US1] Em `apps/desktop-shell/tests/assistant-prefs.test.ts` (ou extensão) — após `savePrefs` e novo `loadPrefs` do mesmo `sessionId`, prefs restauradas; simula “toggle → save → reopen” (FR-025 / C1)

### Implementation for User Story 1

- [x] T017 [US1] Completar `apps/desktop-shell/src/assistant-panel.ts` — toggle automático, checkboxes de origem, seletor de inputMode, lista de turns com estados **running | queued | done | error | cancelled**, busy; turns em ordem **mais recente primeiro** (FR-029); `escapeHtml` em textos (FR-001/011/012/013/017/020/022; C3/C6)
- [x] T018 [US1] Integrar em `apps/desktop-shell/src/main.ts`: carregar prefs da sessão ativa; **em todo** callback de toggle/origens/inputMode chamar `savePrefs(sessionId, …)` antes/depois de `setPrefs` no controller (FR-025); no poll de transcript, `markSeen` no prime e `ingestTranscript` depois; `invokeAiProvider(sessionId, "live-answer", "chat", input)` **sem** channelId; `paintAssistant` via `setOnChange`. **Sessão ativa nesta fase (antes da US3):** se ainda não houver session-picker, usar **apenas** (a) `sessionId` já escolhido em estado de UI mínimo (campo/URL/dev helper **explícito**, nunca auto-create silencioso em background), **ou** (b) chamada explícita a `createSession` disparada por ação do operador (botão provisório “Criar sessão” se necessário). MUST NOT fixar sessão sem escolha do operador (FR-026).
- [x] T019 [US1] Em `apps/desktop-shell/src/main.ts` + `assistant-panel.ts`: sem sessão ativa **ou** session-core desconectado — não reportar automático “ativo com sucesso”; desabilitar controles de auto/disparo e mostrar orientação clara (FR-014; C4); desligar automático não inicia novas gerações; erro de invoke no turn sem derrubar feed (FR-011/016; SC-007)
- [x] T020 [US1] Rodar `npx vitest run` e `npx tsc -b` em `apps/desktop-shell/` até verde para US1

**Checkpoint**: US1 completa (painel + prefs persistidas + guardas de sessão/core). MVP de produto **continua na Phase 4 (US2)**.

---

## Phase 4: User Story 2 — Conflito cancelar vs aguardar (Priority: P1) 🎯 parte do MVP

**Goal**: Segunda pergunta durante geração exige escolha explícita; cancelar descarta resposta tardia; aguardar enfileira (**visível** como `queued`) e inicia ao terminar.

**Independent Test**: Mock de invoke lento + segunda candidata → diálogo; ambos os caminhos (spec US2 / SC-002–004).

### Tests for User Story 2

- [x] T021 [P] [US2] Em `apps/desktop-shell/tests/assistant-auto.test.ts` — conflito ao 2º candidato; `resolveConflict("cancel")` marca cancelled e ignora resultado tardio; `resolveConflict("wait")` enfileira e dispara após o 1º; após wait, terceira candidata C reabre conflito (FR-006–010)
- [x] T022 [P] [US2] Em `apps/desktop-shell/tests/assistant-panel.test.ts` — render de `assistant-conflict`, turn `queued` visível após wait, clique cancel/wait chama callbacks

### Implementation for User Story 2

- [x] T023 [US2] Completar lógica de conflito/fila em `apps/desktop-shell/src/assistant-auto.ts` — última pendente prevalece enquanto diálogo aberto; após wait, pergunta C reabre conflito (FR-010); turn `queued` presente em `getView().turns`
- [x] T024 [US2] UI de conflito em `apps/desktop-shell/src/assistant-panel.ts` (`assistant-conflict`, `assistant-conflict-cancel`, `assistant-conflict-wait`) + wire em `apps/desktop-shell/src/main.ts`; garantir fila visível (FR-009; C3)
- [x] T025 [US2] Rodar vitest focado em auto/panel até verde para US2

**Checkpoint**: **MVP de produto** = US1+US2 (automático + conflito). Validar SC-001–005, SC-007–009 com sessão **explícita** (sem auto-select silencioso) antes de US3.

---

## Phase 5: User Story 3 — Listar / criar / selecionar sessão (Priority: P2)

**Goal**: Operador escolhe sessão na lista ou cria nova; id ativo visível; prefs por sessão restauradas na troca.

**Independent Test**: `GET /api/sessions` + UI lista/cria/seleciona; alternar S/T restaura prefs (US3 / SC-010–011).

### Tests for User Story 3

- [x] T026 [P] [US3] Estender `apps/desktop-shell/tests/assistant-prefs.test.ts` — defaults em sessão nova; S≠T sem vazamento após save em ambas (FR-025 / SC-010)
- [x] T027 [P] [US3] Testes de `apps/desktop-shell/tests/session-picker.test.ts` — lista vazia, criar, selecionar, exibir id (`session-active-id`)

### Implementation for User Story 3

- [x] T028 [US3] Implementar `apps/desktop-shell/src/session-picker.ts` (render puro + callbacks onSelect/onCreate) com data-testids `session-list`, `session-create`, `session-active-id`
- [x] T029 [US3] Wire em `apps/desktop-shell/src/main.ts` + `apps/desktop-shell/index.html`: ao bootstrap **não** fixar sessão em silêncio; listar; criar com **`title="Sessão local"`** e **`profileId="interview-technical"`** (FR-028 / C5); selecionar; ao trocar sessão recarregar prefs e resetar estado de orquestração da UI (turns/seen da sessão corrente)
- [x] T030 [US3] Passar `sessionId` ativo para start agent e polls de status/feed; remover auto-create silencioso do protótipo se conflitar com FR-026; reaplicar guardas FR-014 de T019 quando lista falha (core down)
- [x] T031 [US3] Rodar vitest + `mvn -pl services/session-core test` (incl. T006) verdes

**Checkpoint**: Sessão explícita + automático + conflito em fluxo operador completo

---

## Phase 6: User Story 4 — Histórico legível na sessão corrente (Priority: P3)

**Goal**: Operador revisa sequência de interações com estados distintos e texto seguro.

**Independent Test**: ≥2 turns (done + cancelled/error) legíveis no painel, **mais recente primeiro** (US4; C6).

### Tests for User Story 4

- [x] T032 [P] [US4] Em `apps/desktop-shell/tests/assistant-panel.test.ts` — múltiplos turns com `data-status` distintos; ordem DOM = mais recente primeiro (FR-029 / SC-012); texto com `<` escapado

### Implementation for User Story 4

- [x] T033 [US4] Polir listagem de turns em `apps/desktop-shell/src/assistant-panel.ts` **somente se restar gap após T017** — ordem **mais recente primeiro** (FR-029), labels de status, meta provider/latência quando houver (FR-012; C6)
- [x] T034 [US4] Empty state orientando perguntas finais + automático; estados sem captura / sem sessão / core desconectado coerentes com edge cases e FR-014 (C4) — **somente se restar gap após T019**

**Checkpoint**: UX de histórico mínima “tipo chat” na sessão corrente

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validação do quickstart e qualidade transversal

- [x] T035 [P] Atualizar `docs/development/running.md` (ou parágrafo no README desktop) com: painel Assistente, rota `live-answer`, alinhar agent ao session id da UI, defaults de create session
- [x] T036 Executar checklist de `specs/019-auto-answer-assistant/quickstart.md` §1–2 (e §3 se credencial disponível); E2E demo cobre US1+US2 no mínimo; incluir roteiro guiado de **&lt;1 min** (SC-006): onde ver a resposta automática e o que fazer no conflito cancelar/aguardar; registrar falhas conhecidas de provedor (créditos) sem tratar como bug de orquestração
- [x] T037 [P] `npx eslint src tests` em `apps/desktop-shell/`; `cargo test` em `apps/desktop-shell/src-tauri/`; `mvn -pl services/session-core test`
- [x] T038 Revisar P9: nenhum log de `output` completo do modelo no shell; prefs file sem segredos
- [x] T039 Diff resumido + critérios de aceite da spec para G3 (sem merge automático)
- [x] T040 [P] Smoke manual ou nota no quickstart: painel de provedores (`list`/`test`) ainda funciona após Assistente (FR-016; analyze C12)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup** → livre
- **Phase 2 Foundational** → após Setup; **bloqueia** US1–US4
- **Phase 3 US1** → após Foundational
- **Phase 4 US2** → após US1 — **incluída no MVP de produto**
- **Phase 5 US3** → após Foundational; ideal após MVP US1+US2 para E2E operador
- **Phase 6 US4** → após US1 (painel)
- **Phase 7 Polish** → após stories desejadas (mínimo MVP US1+US2)

### User Story Dependencies

| Story | Depende de | Independente para testar? |
|-------|------------|---------------------------|
| US1 | Foundational (invoke + controller + sessionId qualquer) | Sim, com sessionId via API/`createSession` |
| US2 | US1 (geração em curso) | Sim, com mocks |
| US3 | Foundational (list/create/prefs) | Sim, sem automático |
| US4 | US1 painel | Sim, com state fixture |

### Parallel Opportunities

- T002 ∥ T003 (Setup)
- Após T005: T006 (Java test) ∥ T007–T009 ∥ T010–T011 ∥ T012–T013
- T014 ∥ T015 ∥ T016 (testes US1)
- T021 ∥ T022 (testes US2)
- T026 ∥ T027 (testes US3)
- Após Foundational: dev A US1/US2; dev B prefs/session API tests

---

## Parallel Example: User Story 1

```bash
# Testes em paralelo:
# T014 assistant-auto.test.ts
# T015 assistant-panel.test.ts
# T016 assistant-prefs save/load

# Implementação:
# T017 panel → T018 main (save prefs + invoke) → T019 guards → T020
```

## Parallel Example: Foundational

```bash
# Após T004–T005 (API Java):
# T006 SessionListApiTest
# T007–T008 Rust client + tests
# T009 api-client.ts
# T010–T011 prefs load/save
# T012–T013 assistant-auto core + tests
```

---

## Implementation Strategy

### MVP de produto (US1 + US2) — recomendado

1. Phase 1 + Phase 2  
2. Phase 3 US1  
3. Phase 4 US2  
4. **STOP** — validar SC-001–005, SC-007–009 com sessão criada **explicitamente** (curl, botão mínimo ou API; sem auto-select silencioso — FR-026)  
5. Demo: pergunta automática + conflito cancelar/aguardar  

### Incremental Delivery

1. **MVP US1+US2** → “vejo o ChatGPT” + controle de concorrência  
2. US3 → operador não depende de curl para sessão  
3. US4 → histórico polido  
4. Polish / quickstart  

### Suggested MVP scope

**T001–T025** (Setup + Foundational + **US1 + US2**).  
Não entregar só US1 se o requisito de conflito (P1) estiver no aceite da release.

---

## Notes

- Checklist format: `- [ ] Tnnn [P]? [USn]? Description with path`
- Rota fixa `live-answer`, capability `chat`, **sem** `channelId` no invoke (research Decisão 5)
- Cancelamento = descarte lógico; abort HTTP opcional
- **Prefs: load na troca de sessão + save em toda mudança de UI** (analyze C1); Rust prefs obrigatório (A3)
- Heurística de pergunta: **FR-004** (A1); turns mais recente primeiro: **FR-029** (A2)
- Create session defaults: **FR-028**; sessão nunca auto-fixada em silêncio (A4 / FR-026)
- Não commitar `.env` / chaves; não logar output do modelo
- Commit por tarefa ou grupo lógico; merge humano (P8)

---

## Phase 8: Convergence

> Achados de `/speckit-converge` (2026-07-25): implementação cobre US1–US4 e FRs principais; gaps residuais no fluxo de conflito quando a geração termina com o diálogo ainda aberto.

- [x] T041 [US2] Em `apps/desktop-shell/src/assistant-auto.ts`, após `resolveConflict("wait")`, chamar `drainQueue()` (ou iniciar a pendente) quando **não** houver geração ativa — cobre o caso em que A termina com o diálogo de conflito ainda aberto e o operador só então escolhe Aguardar (FR-009 / SC-004) (partial). Incluir teste em `apps/desktop-shell/tests/assistant-auto.test.ts`: A em voo → B conflito → A conclui → `resolveConflict("wait")` → B invoca sem segundo diálogo.
- [x] T042 [P] [US2] Em `apps/desktop-shell/src/assistant-panel.ts` (e/ou estado do controller), quando o diálogo de conflito está aberto e o turn “em execução” já está `done`/`error`/`cancelled`, não apresentar A como se ainda estivesse gerando (rótulo/estado coerente com a realidade) (US2/AC1, FR-007) (partial). Teste de painel opcional em `assistant-panel.test.ts`.
