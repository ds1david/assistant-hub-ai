# Implementation Plan: Alinhar sessionId UI↔agent e disparo só em transcript final (live-answer)

**Branch**: `020-issue-47-sessionid-align` | **Date**: 2026-07-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/020-issue-47-sessionid-align/spec.md` (clarify 2026-07-25, 5 decisões)

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Corrigir o desalinhamento operacional que impede o Assistente automático (019) de reagir ao transcript: o shell passa a **resolver e exibir** a sessão do agent (cmdline `--session` → último start gerenciado → desconhecida), comparar com a **sessão ativa da UI**, mostrar **banner de mismatch** e CTA **Reiniciar agent com sessão ativa** (modo Direct, sem confirm, sem force-kill de processo externo). O start/guidance sempre usa o UUID da sessão ativa. O painel Assistente ganha **estados vazios distintos** (precedência: mismatch → prefs off → feed vazio → aguardando final → sem pergunta elegível). Documentação operacional (`running.md` / `min-flow.md`) registra a regra do sessionId único. **Sem** mudança de contrato transcript v2, session-core ou agent Python.

Detalhes: [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/session-align-shell.md](./contracts/session-align-shell.md) · [quickstart.md](./quickstart.md).

## Technical Context

**Language/Version**: TypeScript 5 + Vite (webview); Rust (lib `desktop_shell` + comandos Tauri, mesmo padrão 014/019). Sem Java nesta fatia.

**Primary Dependencies**: `sysinfo` 0.32 (já em `apps/desktop-shell/src-tauri` — `Process::cmd()` para linha de comando); `@tauri-apps/api` no TS. Reuso de `start_agent` / `stop_agent` / `get_agent_status`. Sem SDK novo, sem mudança no `assistant-hub-audio` Python.

**Storage**: N/A além do estado em memória do processo shell (`managed_agent` + `last_managed_session_id`). Sem preferências novas; prefs do Assistente permanecem as da 019.

**Testing**: Vitest + jsdom (agent-panel, empty states, wiring de start com session ativa). `cargo test` na lib Rust (`agent_control`: parse de `--session`, resolução de prioridade, sem kill externo). Sem GPU/WASAPI (P10). E2E Windows opcional documentado no quickstart.

**Target Platform**: Shell validado em Windows com WebView2; lib Rust e vitest no WSL. Parsing de cmdline de processos Windows é o caminho de produção; testes de parse com fixtures de `OsString`/`Vec` no WSL.

**Project Type**: Extensão de `apps/desktop-shell` (+ docs). Nenhum serviço novo.

**Performance Goals**: Resolução de sessão do agent e paint de mismatch no mesmo ciclo de poll do agent (ordem de segundos, alinhado ao poll existente); parsing de cmdline O(processos agent) desprezível.

**Constraints**: P1/G1 antes de implement oficial; P5 sessionId ponta a ponta; P6 não tocar PyAudio/WASAPI no shell; P9 sem logar áudio/tokens/output do modelo; clarify: **sem force-kill** de agent externo; **sem confirm** no restart Direct; select de sessão **não** reinicia sozinho; só finais disparam live-answer (019 FR-003).

**Scale/Scope**: Estender `AgentStatus` + resolução de session; UI agent (ids, mismatch, CTA); empty states do Assistente; docs; testes. MVP = US1 + US2 (alinhar + mismatch/restart). US3 empty states e US4 docs na mesma fatia (baixo risco). Fora: multi-agent, auto-start STT, kill externo, contrato transcript, classificador R2.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|-----------|-----------|
| P1 — Spec antes de código | PASS. Spec + 5 clarificações + checklist 16/16. G1 humano antes de Implement. |
| P2 — Core independente de fornecedores | PASS. Nenhuma integração de LLM/STT nova; só UI/controle de processo. |
| P3 — WSL-first | PASS. vitest/cargo test lib no WSL; spawn real do agent só E2E Windows. |
| P4 — Contratos versionados | PASS. Sem schema transcript/provedores/session-core; contrato feature-local de status UI documentado. |
| P5 — Canal/origem | PASS. Reforça o mesmo `sessionId` entre UI, agent e STT; não mistura canais. |
| P6 — Isolamento áudio | PASS. Shell só gerencia processo; não compartilha PyAudio. |
| P7 — Identidade dispositivo | N/A. |
| P8 — Automação com autorização | PASS. Plano não propõe merge/force-push. |
| P9 — Privacidade | PASS. UI pode mostrar UUIDs de sessão; sem áudio/tokens/output de modelo em log. |
| P10 — Qualidade determinística | PASS. Parse de cmdline e UI com fakes/fixtures; sem hardware. |

Nenhuma violação → Complexity Tracking vazio.

### Post-design re-check (Phase 1)

Gates permanecem PASS. research/data-model/contracts/quickstart:
- não alteram transcript-event.v2 nem session-core;
- resolução de sessão do agent é observabilidade de processo + estado local (não inventa id);
- Guided sem force-kill (clarify Q2);
- empty states de produto sem mudar regra “só Final dispara”;
- docs operacionais como entregável de US4.

### Pós-analyze (2026-07-25) — remediações em tasks/contracts/data-model

- **I1**: `controlMode=Direct` quando `!running` para o botão Iniciar não sumir.
- **I2**: helper de restart exportável + teste stop→start com session ativa.
- **I3**: T021 exige assert (select não chama stop/start).
- **I4**: feed vazio ≠ `awaiting_final`.
- Gates de constituição inalterados (PASS).

## Project Structure

### Documentation (this feature)

```text
specs/020-issue-47-sessionid-align/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── session-align-shell.md
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md                 # /speckit-tasks (não criado por /speckit-plan)
```

### Source Code (repository root) — arquivos prováveis

```text
apps/desktop-shell/src-tauri/src/
├── agent_control.rs         # + parse --session de cmdline; resolve agent_session_id; last managed id
├── lib.rs                   # reexports se necessário
└── main.rs                  # AppState.last_managed_session_id; get/start/stop preenchem AgentStatus

apps/desktop-shell/src/
├── api-client.ts            # AgentStatus + agentSessionId / resolution
├── agent-panel.ts           # ids UI vs agent, mismatch banner, CTA restart, guided recovery
├── session-alignment.ts     # (novo) pure: AlignmentState, compare ids, empty-state precedence helpers
├── assistant-panel.ts       # empty states distintos (data-testid por kind)
├── assistant-auto.ts        # opcional: expor sinais de feed (partials/finals) para empty state
├── main.ts                  # start com activeSessionId; restart CTA; guidance com sessão ativa;
│                            # bloquear start sem sessão; poll → paint alignment
└── ...

apps/desktop-shell/tests/
├── agent-panel.test.ts      # mismatch, CTA, guided, sem start sem sessão (via callbacks)
├── session-alignment.test.ts
├── assistant-panel.test.ts  # empty states FR-010
└── assistant-auto.test.ts   # final elegível ainda dispara (regressão 019)

docs/development/running.md
docs/release/min-flow.md
```

**Structure Decision**: Somente `apps/desktop-shell` + docs. Reutilizar `agent_control` / painel agent / Assistente da 014–019. Nenhum crate ou serviço novo. Funções puras de alinhamento e empty state em TS para vitest; parse de cmdline em Rust com testes unitários.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
