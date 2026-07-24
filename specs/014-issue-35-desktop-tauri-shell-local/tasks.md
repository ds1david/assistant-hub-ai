---

description: "Task list for Desktop Tauri — shell local do Assistant Hub (R5)"
---

# Tasks: Desktop Tauri — shell local do Assistant Hub (R5)

**Input**: Design documents from `/specs/014-issue-35-desktop-tauri-shell-local/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Incluídos — `plan.md` (Technical Context, Project Structure) já projeta arquivos de teste específicos (`session_core_client_tests.rs`, `agent_control_tests.rs`, `transcript-feed.test.ts`), referenciados por nome em `quickstart.md`, e SC-006 exige explicitamente que os testes automatizados desta feature rodem sem GPU/hardware físico (P10).

**Organization**: Tarefas agrupadas por user story (US1–US4, prioridades de `spec.md`) para permitir implementação e teste independentes de cada uma.

**Nota de execução (esta rodada)**: implementado em WSL sem GTK/WebView2 instalado. A lib Rust (`config`/`session_core_client`/`agent_control`) foi separada do binário Tauri via feature Cargo `gui` (`dep:tauri` opcional) especificamente para poder compilar e rodar `cargo test` de verdade neste ambiente — todos os testes Rust (23) e frontend (10, vitest) citados abaixo foram executados e passam. `main.rs`/`tauri.conf.json` (tudo que depende do crate `tauri`) foi escrito seguindo a spec, mas **não compila neste ambiente** (`cargo build --features gui` falha por falta de `pkg-config`/`glib`/`webkit2gtk`, confirmando `research.md` Decisão 7) — build/execução reais ficam para a máquina Windows de referência (`docs/desktop-shell/packaging.md`). Tarefas marcadas `[X]` com essa ressalva estão com o código escrito e revisado, não com o binário Tauri executado.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: A qual user story a tarefa pertence (US1, US2, US3, US4)
- Caminhos de arquivo são sempre relativos à raiz do monorepo

## Path Conventions

Aplicativo novo (Tauri 2), sem tocar módulos existentes: `apps/desktop-shell/src-tauri/` (núcleo Rust + testes Rust) e `apps/desktop-shell/src/` (frontend TypeScript/Vite + testes vitest), conforme `plan.md` § Project Structure. Documentação de packaging em `docs/desktop-shell/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicializar o novo aplicativo `apps/desktop-shell/` (Tauri 2 + frontend), sem tocar nenhum módulo existente

- [X] T001 Criar o esqueleto do núcleo Tauri 2 em `apps/desktop-shell/src-tauri/` — `Cargo.toml`, `tauri.conf.json` inicial, `src/main.rs` de entrada, conforme `plan.md` § Project Structure. `Cargo.toml` usa `tauri` como dependência **opcional** atrás da feature `gui` (`[[bin]] required-features = ["gui"]`) para permitir `cargo test` da lib sem GTK — decisão tomada nesta rodada, não estava em `research.md` originalmente
- [X] T002 Criar o esqueleto do frontend (TypeScript + Vite, sem framework de UI — decisão registrada em `research.md` §2) em `apps/desktop-shell/` — `package.json`, `vite.config.ts`, `index.html`, `src/main.ts` inicial. Verificado: `npm install`, `npx tsc -b` e `npx vite build` rodam com sucesso
- [X] T003 [P] Configurar lint/format Rust (`rustfmt`, `clippy`) em `apps/desktop-shell/src-tauri/rustfmt.toml`. Verificado: `cargo fmt -- --check` e `cargo clippy --all-targets -- -D warnings` limpos
- [X] T004 [P] Configurar lint/format do frontend em `apps/desktop-shell/eslint.config.js` e `apps/desktop-shell/.prettierrc`. **Ajuste em relação ao planejado**: ESLint 9 exige config flat (`eslint.config.js`), não mais `.eslintrc.json` — descoberto ao rodar `npx eslint` de verdade; `.eslintrc.json` foi removido. Verificado: `npx eslint .` e `npx prettier --check` limpos

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura que todas as user stories consomem — config local, ponte Tauri↔webview e chamadas cruas ao `session-core`

**⚠️ CRITICAL**: Nenhuma user story pode ser implementada antes desta fase estar completa

- [X] T005 Adicionar as dependências `reqwest` (`blocking`+`json`+`rustls-tls`) e `sysinfo` ao `apps/desktop-shell/src-tauri/Cargo.toml` (depende de T001). Verificado: `cargo build`/`cargo test` resolvem e compilam as dependências
- [X] T006 Implementar `ShellConfig` (struct + load/save em JSON) em `apps/desktop-shell/src-tauri/src/config.rs` — `sessionCoreBaseUrl` (padrão `http://localhost:8080`) e `windowState`, sem segredo (FR-013) (depende de T001, T005). Verificado: 4 testes unitários passam, incluindo trava de regressão anti-segredo
- [X] T007 [P] Implementar `api-client.ts` — wrappers tipados em torno de `invoke` do Tauri, nunca `fetch` direto no webview — em `apps/desktop-shell/src/api-client.ts` (depende de T002). Verificado: `tsc -b` e `eslint` limpos
- [X] T008 Implementar as chamadas HTTP cruas ao `session-core` — `get_session(id)`, `get_events(id)`, `get_health()` — em `apps/desktop-shell/src-tauri/src/session_core_client.rs` (depende de T005, T006). Verificado por 6 testes de integração contra um servidor HTTP fake local (`tests/session_core_client_tests.rs`)
- [X] T009 Registrar os comandos Tauri de `config` e `session_core_client` em `apps/desktop-shell/src-tauri/src/main.rs` (depende de T006, T008). **Escrito, não compilado neste ambiente** (feature `gui`, requer WebView2/GTK — ver nota de execução acima)
- [X] T010 [P] Criar o esqueleto do módulo `agent_control` em `apps/desktop-shell/src-tauri/src/agent_control.rs` (depende de T005). Evoluído diretamente para a implementação completa em T026/T027 nesta mesma rodada
- [X] T011 [P] Configurar o harness de testes — `cargo test` em `apps/desktop-shell/src-tauri/tests/` e `vitest` via `vite.config.ts` (`test.environment = "jsdom"`) (depende de T001, T002). Verificado: 23 testes Rust + 10 testes vitest passam

**Checkpoint**: Config local, ponte Tauri↔webview e acesso HTTP cru ao `session-core` prontos — implementação das user stories pode começar

---

## Phase 3: User Story 1 - Acompanhar sessão e canais sem terminal (Priority: P1) 🎯 MVP

**Goal**: O shell mostra status da sessão atual (ativa/encerrada/ausente) e os canais conhecidos (`channelId`/`sourceType`/`label`) sem exigir CLI, e informa claramente quando não consegue conectar ao `session-core`.

**Independent Test**: Com `session-core` rodando e uma sessão com eventos em 2 canais (via API já existente), abrir o shell e confirmar que a sessão aparece com status correto e os dois canais aparecem distintos com seus metadados; repetir sem sessão ativa e com `session-core` fora do ar.

### Tests for User Story 1 ⚠️

- [X] T012 [P] [US1] Teste Rust em `apps/desktop-shell/src-tauri/tests/session_core_client_tests.rs` — sessão encontrada → `connectivity = Connected`; sessão inexistente (404) → `Connected` com `session = None`; `GET /actuator/health` indisponível/inalcançável → `Disconnected`, nunca dado obsoleto (FR-001/FR-009). 4 testes, todos passando
- [X] T013 [P] [US1] Teste Rust — agrega eventos sintéticos de 2 canais em `ChannelStatusView[]`, confirma agrupamento por `channelId` (nunca só por `label`) e preservação de `sourceType`/`label`/`device` (FR-002). Passando (unitário + integração HTTP)

### Implementation for User Story 1

- [X] T014 [US1] Implementar `SessionStatusView`/`session_status_view()` em `session_core_client.rs` (depende de T008; T012 passa)
- [X] T015 [US1] Implementar `channel_status_views()` a partir de `get_events` em `session_core_client.rs` (depende de T008; T013 passa)
- [X] T016 [US1] Registrar o comando Tauri `get_session_status` em `main.rs` (depende de T014, T015). **Escrito, não compilado neste ambiente** (ver nota de execução)
- [X] T017 [P] [US1] Implementar `session-status.ts` — estados ativo/vazio/desconectado/erro + lista de canais, com escape de HTML (`dom-utils.ts`) — em `apps/desktop-shell/src/session-status.ts` (depende de T007, T016). Verificado por 3 testes vitest (`tests/session-status.test.ts`)
- [X] T018 [US1] Ligar `session-status.ts` a `apps/desktop-shell/src/main.ts` com loop de polling (~5s) (depende de T017). `tsc -b`/`vite build` confirmam que compila; execução real do polling depende do runtime Tauri (não disponível aqui)

**Checkpoint**: User Story 1 completa e testável de forma independente — status de sessão/canais visível sem CLI.

---

## Phase 4: User Story 2 - Ler o feed de transcript da sessão em tempo real (Priority: P1)

**Goal**: O feed de transcript aparece no shell à medida que eventos chegam, identificado por canal, em ordem cronológica, sem misturar canais; ao reconectar, recarrega o histórico já persistido.

**Independent Test**: Com eventos `transcript-event.v2` sintéticos chegando em mais de um canal, abrir o shell e confirmar que os trechos aparecem na ordem de chegada, cada um identificado com o canal de origem, e que reabrir o shell recarrega o histórico já persistido.

### Tests for User Story 2 ⚠️

- [X] T019 [P] [US2] Teste Rust — fixtures de `HubEvent` fora de ordem e de canais distintos, confirma `TranscriptFeedEntry[]` ordenado por `occurredAt` e sem mistura de canal (FR-004/FR-005), incluindo dedup por `eventId`. Passando (unitário + integração HTTP)
- [X] T020 [P] [US2] Vitest em `apps/desktop-shell/tests/transcript-feed.test.ts` — ordem cronológica, não mistura de canal, escape de HTML e estado vazio (SC-002). 4 testes passando

### Implementation for User Story 2

- [X] T021 [US2] Implementar `transcript_feed_entries()` em `session_core_client.rs` — filtra `transcript.partial.v2`/`transcript.final.v2`, ordena, deduplica por `eventId` (depende de T008; T019 passa)
- [X] T022 [US2] Registrar o comando Tauri `get_transcript_feed` em `main.rs` (depende de T021). **Escrito, não compilado neste ambiente** (ver nota de execução)
- [X] T023 [P] [US2] Implementar `transcript-feed.ts` em `apps/desktop-shell/src/transcript-feed.ts` (depende de T007, T022; T020 passa)
- [X] T024 [US2] Ligar `transcript-feed.ts` a `apps/desktop-shell/src/main.ts` com loop de polling (~2s) (depende de T023). Compila; execução real depende do runtime Tauri

**Checkpoint**: User Stories 1 e 2 funcionam de forma independente — MVP funcional do shell (status + feed, sem CLI).

---

## Phase 5: User Story 3 - Controlar ou ser orientado sobre o agent de áudio Windows (Priority: P2)

**Goal**: O shell mostra se `assistant-hub-audio` está ativo/parado e permite iniciar/parar diretamente quando o shell controla o processo, ou mostra uma instrução textual exata quando não controla.

**Independent Test**: Com o agent parado, abrir o shell e confirmar status "parado" com uma ação clara disponível; com o agent ativo, confirmar status "ativo"; simular falha de start e confirmar mensagem específica do motivo.

### Tests for User Story 3 ⚠️

- [X] T025 [P] [US3] Teste Rust em `apps/desktop-shell/src-tauri/tests/agent_control_tests.rs` — executável fake (`sleep` renomeado) para `assistant-hub-audio`: detecção via `sysinfo` de processo iniciado externamente; `start()` retorna `AlreadyRunning` quando já detectado; binário ausente produz mensagem específica (FR-006/FR-007/FR-008). 3 testes passando, mais 3 testes unitários inline em `agent_control.rs` (binário ausente / saída imediata / start-stop direto)

### Implementation for User Story 3

- [X] T026 [US3] Implementar detecção de `AgentStatus` via `sysinfo` em `agent_control.rs` (depende de T010; T025 passa). **Achado real durante os testes**: o `comm` do Linux trunca nomes de processo em 15 caracteres (`TASK_COMM_LEN`), cortando "assistant-hub-audio" — `detect_running()` foi ajustado para também checar `Process::exe()` (nome de arquivo, sem truncamento); documentado no próprio código
- [X] T027 [US3] Implementar start/stop direto e `guidance_command()` em `agent_control.rs` (depende de T026; T025 passa)
- [X] T028 [US3] Registrar os comandos Tauri `get_agent_status`, `start_agent`, `stop_agent` em `main.rs` (depende de T027). **Escrito, não compilado neste ambiente** (ver nota de execução)
- [X] T029 [P] [US3] Implementar `agent-panel.ts` em `apps/desktop-shell/src/agent-panel.ts` (depende de T007, T028). Verificado por 3 testes vitest (`tests/agent-panel.test.ts`)
- [X] T030 [US3] Ligar `agent-panel.ts` a `apps/desktop-shell/src/main.ts` (depende de T029). Compila; execução real depende do runtime Tauri

**Checkpoint**: User Stories 1, 2 e 3 funcionam de forma independente — operação completa (status, feed, agent) sem CLI.

---

## Phase 6: User Story 4 - Instalar e rodar o shell de forma reproduzível (Priority: P3)

**Goal**: Um desenvolvedor consegue, seguindo apenas a documentação, empacotar/instalar e abrir o shell funcional na máquina Windows de referência.

**Independent Test**: Em uma máquina Windows de referência limpa, seguir apenas os passos documentados e confirmar que o resultado é o shell funcional descrito nas demais user stories.

### Implementation for User Story 4

- [X] T031 [US4] Configurar o bundler do Tauri (MSI/NSIS, sem assinatura/auto-update) em `apps/desktop-shell/src-tauri/tauri.conf.json` (depende de T001). **Escrito conforme a documentação do schema do Tauri 2, não validado por `cargo tauri build` neste ambiente**; nenhum ícone versionado ainda (`docs/desktop-shell/packaging.md` documenta `cargo tauri icon` como passo pendente antes de um release real)
- [X] T032 [P] [US4] Escrever `docs/desktop-shell/packaging.md` (FR-011, SC-004) (depende de T031)
- [ ] T033 [US4] Executar a validação manual descrita em `quickstart.md` § Passo 3 na máquina Windows de referência e registrar o resultado em `docs/validation/` (depende de T032, e de US1/US2/US3 completas). **Não executado nesta rodada** — exige a máquina Windows de referência (WebView2), indisponível neste ambiente WSL

**Checkpoint**: US1–US3 completas e testadas nesta rodada; packaging documentado, mas validação manual no Windows real (T033) ainda pendente.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Garantias que atravessam todas as user stories

- [X] T034 [P] Confirmar que fechar a janela do shell não encerra `session-core` nem o agent Windows por padrão (edge case de `spec.md`). Confirmado por revisão de código: `main.rs` não registra `on_window_event`/`CloseRequested`/`prevent_close` que encerre processos externos (comentário inline no código). Cobertura por teste automatizado do evento de fechamento de janela em si não é possível sem o runtime Tauri real (GUI) — fica para validação manual (T033)
- [X] T035 [P] Revisar `apps/desktop-shell/src-tauri/src/*.rs` e `apps/desktop-shell/src/*.ts` para confirmar ausência de log de texto de transcript/token (P9). Confirmado via `grep` — nenhum `println!`/`eprintln!`/`log::`/`tracing::` no código de produção Rust; `console.error` do frontend loga apenas o objeto `Error`, nunca payload/texto
- [X] T036 Rodar as suítes já existentes de `services/session-core` e `services/transcription-service` e confirmar ausência de regressão (FR-012/SC-005). **Executado de verdade**: `mvn -pl services/session-core -am test` → 18/18 passando; `pytest services/transcription-service/tests` → 78/78 passando
- [ ] T037 Executar o roteiro completo de `specs/014-issue-35-desktop-tauri-shell-local/quickstart.md` (Passos 1–4). **Parcial**: Passo 2 (suíte Rust+frontend) e Passo 4 (regressão) executados de verdade nesta rodada; Passo 1 (session-core real + `curl`) e Passo 3 (validação manual no Windows) não executados nesta sessão — Passo 3 depende de T033
- [X] T038 [P] Revisar `session_core_client.rs`/`agent_control.rs` para confirmar que nenhuma tarefa escreveu de volta em sessão/eventos além dos endpoints REST já existentes, nem reimplementou lógica de domínio do `session-core` (FR-010). Confirmado via `grep` — nenhuma chamada `.post()`/`.put()`/`.delete()`/`.patch()` no cliente, só `GET`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: Depende da conclusão do Setup — BLOQUEIA todas as user stories
- **User Story 1 (Phase 3)**: Depende do Foundational — sem dependência de outras stories
- **User Story 2 (Phase 4)**: Depende do Foundational; reaproveita `get_events` cru (T008) de US1, mas é testável de forma independente assim que Foundational estiver completo
- **User Story 3 (Phase 5)**: Depende do Foundational (T010); independente de US1/US2 — pode ser implementada em paralelo a elas
- **User Story 4 (Phase 6)**: Depende de US1, US2 e US3 estarem completas para a validação manual (T033) ter o que validar; a configuração do bundler (T031) e a documentação (T032) podem começar antes
- **Polish (Phase 7)**: Depende de todas as user stories desejadas estarem completas

### Within Each User Story

- Testes escritos e falhando antes da implementação
- Chamadas cruas ao `session-core`/agent (Foundational) antes de qualquer lógica de agregação/domínio por story
- Comando Tauri registrado antes do painel de frontend que o consome
- Story completa antes de avançar para a próxima prioridade

### Parallel Opportunities

- T003 e T004 (Setup) podem rodar em paralelo
- T007, T010 e T011 (Foundational) podem rodar em paralelo entre si
- T012 e T013 (testes de US1) podem rodar em paralelo entre si
- T019 e T020 (testes de US2) podem rodar em paralelo entre si e com os testes de US1, já que exercitam arquivos diferentes
- Uma vez o Foundational completo, US1, US2 e US3 podem ser implementadas em paralelo por pessoas/threads diferentes (T012–T018, T019–T024, T025–T030 não compartilham arquivo de implementação além de `main.rs`/`main.ts`, que exigem merge sequencial dos registros de comando)
- T034, T035 e T038 (Polish) podem rodar em paralelo

---

## Parallel Example: User Story 1

```bash
# Testes de User Story 1 em paralelo:
Task: "Teste Rust (status/conectividade) em apps/desktop-shell/src-tauri/tests/session_core_client_tests.rs"
Task: "Teste Rust (agregação de canais) em apps/desktop-shell/src-tauri/tests/session_core_client_tests.rs"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRÍTICO — bloqueia todas as stories)
3. Completar Phase 3: User Story 1
4. Completar Phase 4: User Story 2
5. **PARAR e VALIDAR**: testar US1+US2 de forma independente (status de sessão/canais + feed ao vivo, sem CLI)
6. Já entrega o valor central da issue #35: operar sessão e acompanhar transcript sem depender só de CLI

### Incremental Delivery

1. Setup + Foundational → base pronta
2. User Story 1 → validar independentemente → status de sessão/canais visível
3. User Story 2 → validar independentemente → MVP do shell (status + feed)
4. User Story 3 → validar independentemente → controle/orientação do agent Windows
5. User Story 4 → validar na máquina Windows de referência → packaging documentado e reproduzível
6. Cada story agrega valor sem quebrar as anteriores

### Parallel Team Strategy

Com múltiplos desenvolvedores, após Setup + Foundational:

- Desenvolvedor A: User Story 1
- Desenvolvedor B: User Story 2
- Desenvolvedor C: User Story 3
- User Story 4 começa (T031/T032) em paralelo, mas sua validação final (T033) espera US1–US3

---

## Notes

- [P] tasks = arquivos diferentes, sem dependência entre si
- Rótulo [Story] mapeia a tarefa à user story correspondente para rastreabilidade
- Verificar que os testes falham antes de implementar
- Fazer commit após cada tarefa ou grupo lógico
- Parar em cada checkpoint para validar a story de forma independente
- Nenhuma tarefa altera `services/session-core`, `services/transcription-service` ou `agents/windows-audio-agent` — o shell é estritamente um cliente (FR-010)
- Nenhum `contracts/` é alterado — o shell consome `transcript-event.v2` (via `HubEvent`) e a API REST do `session-core` como já publicadas
- **Pendências reais após esta rodada**: T033 (validação manual Windows) e a parte de T037 que depende dela; gerar ícones do app (`cargo tauri icon`) antes de um release real (ver `docs/desktop-shell/packaging.md`)
