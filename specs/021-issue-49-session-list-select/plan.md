# Implementation Plan: Sessão — seleção na lista e alinhar agent ao sessionId ativo

**Branch**: `feature/issue-49-desktop-sess-o-sele-o-na-lista-alinhar-agent-ao` | **Date**: 2026-07-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/021-issue-49-session-list-select/spec.md` (clarify 2026-07-25: orphan→null, no auto-select, in-memory only)

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Corrigir o seletor de sessões do shell desktop para que **clique e criar** definam de forma confiável a **sessão ativa** (id canônico completo do session-core), **preservem** a seleção no refresh quando o id ainda existe, e **limpem** para nulo quando o id some. Garantir que start/restart do agent (já entregue em grande parte pela 020) continue usando **esse** id — nunca um `session-YYYYMMDD-HHMMSS` gerado no lugar do UUID do core — e que docs digam que list-sessions só reflete session-core. Reutilizar mismatch/CTA/guidance da 020 sem reimplementar orquestração do Assistente.

Detalhes: [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/session-picker-shell.md](./contracts/session-picker-shell.md) · [quickstart.md](./quickstart.md).

## Technical Context

**Language/Version**: TypeScript 5 + Vite (webview); Rust só se houver gap no client de session-core (improvável). Sem Java, sem Python agent nesta fatia.

**Primary Dependencies**: Shell existente (`apps/desktop-shell`): `session-picker.ts`, `main.ts`, `api-client.ts` / Tauri `session_core_client`, `agent-session-actions.ts`, `session-alignment.ts` (020). Sem nova crate ou SDK.

**Storage**: Estado em memória do processo do shell (`activeSessionId`, `sessionList`). Preferências do Assistente já por sessionId (019). Sem persistência de sessão ativa entre reinícios (clarify).

**Testing**: Vitest + jsdom (`session-picker`, helpers de reconcile/select, wiring create→active, refresh preserve/orphan, start com id ativo / mismatch fakes). Sem GPU/WASAPI (P10). E2E Windows opcional no quickstart.

**Target Platform**: Shell validado em Windows com WebView2; vitest no WSL.

**Project Type**: Extensão de `apps/desktop-shell` + docs. Nenhum serviço novo; sem mudança de schema session-core ou transcript v2.

**Performance Goals**: Select e paint no mesmo turno de evento de clique; list refresh no mesmo ciclo do botão/poll existente (ordem de segundos).

**Constraints**: P1/G1 antes de Implement; P5 sessionId ponta a ponta; P9 sem áudio/tokens; clarify: **sem** auto-select do primeiro item; orphan → `null`; select **não** reinicia agent (**020 FR-009** / **021 FR-011**); não aceitar ids STT-only na lista sem create no core. Colisão de IDs: **021 FR-009** = restart com sessão ativa (≠ 020 FR-009).

**Scale/Scope**: Seletor + reconcile de active id + testes FR-013 + docs list-sessions vs agent path id. **MVP = US1 + US2 + US3** na mesma entrega (select + create→active + refresh/orphan + agent start/restart/guidance/mismatch; analyze item 4). US3 reusa 020 com regressões obrigatórias (incl. FR-012 guidance). US4 docs + polish.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|-----------|-----------|
| P1 — Spec antes de código | PASS. Spec Clarified + checklist requirements 16/16. G1 humano antes de Implement. |
| P2 — Core independente de fornecedores | PASS. Sem STT/LLM novos. |
| P3 — WSL-first | PASS. vitest no WSL; agent real só E2E Windows. |
| P4 — Contratos versionados | PASS. Sem schema transcript/session-core; contrato feature-local de picker UI. |
| P5 — Canal/origem | PASS. Reforça sessionId do core na UI e no agent. |
| P6 — Isolamento áudio | PASS. Shell não toca PyAudio. |
| P7 — Identidade dispositivo | N/A. |
| P8 — Automação com autorização | PASS. Plano não propõe merge/force-push. |
| P9 — Privacidade | PASS. UUIDs na UI OK; sem áudio/tokens. |
| P10 — Qualidade determinística | PASS. Fakes de lista/create/start; sem hardware. |

Nenhuma violação → Complexity Tracking vazio.

### Post-design re-check (Phase 1)

Gates permanecem PASS. research/data-model/contracts/quickstart:
- não alteram transcript-event.v2 nem aceitam STT-only ids no list;
- orphan clear e no auto-select documentados;
- reuso de 020 para mismatch/start;
- docs como US4.

### Pós-analyze remediação (2026-07-25)

- **I1**: tasks/plan desambiguam 020 FR-009 vs 021 FR-009 / 021 FR-011.
- **C1**: T017 exige assert de guidance com `--session` da sessão ativa (021 FR-012).
- **U1/A1/C2**: `afterCreateSuccess` testável; refresh failure = keep active (sem “unless”); orphan clear → paint FR-003.
- **MVP**: US1+US2+US3 mesma entrega (issue #49 ponta a ponta).

## Project Structure

### Documentation (this feature)

```text
specs/021-issue-49-session-list-select/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── session-picker-shell.md
├── checklists/
│   ├── requirements.md
│   └── session-select.md      # /speckit-checklist
├── spec.md
└── tasks.md                   # /speckit-tasks
```

### Source Code (repository root) — arquivos prováveis

```text
apps/desktop-shell/src/
├── session-picker.ts          # render lista; full id no active; select dispara onSelect com id canônico
├── session-selection.ts       # (novo ou em agent-session-actions) pure: reconcileActiveAfterList, select/create helpers
├── agent-session-actions.ts   # onSessionSelected (já existe); manter sem stop/start
├── main.ts                    # selectSession, createAndSelectSession, refreshSessionList + orphan clear
├── api-client.ts              # listSessions / createSession (existente)
└── ...

apps/desktop-shell/tests/
├── session-picker.test.ts     # select callback, active full id, create button
├── session-selection.test.ts  # (novo) reconcile preserve/orphan; no auto-select
└── agent-session-actions.test.ts  # regressão select ≠ restart

docs/development/running.md
docs/release/min-flow.md
```

**Structure Decision**: Somente `apps/desktop-shell` + docs. Lógica de reconcile/seleção em funções puras TS para vitest; reutilizar 020 para agent. Nenhum serviço ou contrato HTTP novo.

## Complexity Tracking

> Nenhuma violação de constituição a justificar.
