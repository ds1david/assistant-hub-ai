# Research: Sessão — seleção na lista e alinhar agent

**Feature**: `specs/021-issue-49-session-list-select`  
**Date**: 2026-07-25

## Decision 1 — Onde vive a lógica de seleção / reconcile

**Decision**: Funções **puras TypeScript** (módulo dedicado, ex. `session-selection.ts`, ou extensão de `agent-session-actions.ts`) para:

- `onSessionSelected` (já existe — só seta id ativo; **sem** agent stop/start);
- `reconcileActiveSessionAfterList(activeId, sessions) -> string | null` — preserva se id ∈ lista; senão `null`;
- opcional: guard `isSelectableSessionId(id)`.

Wiring em `main.ts` (`selectSession`, `createAndSelectSession`, `refreshSessionList`).

**Rationale**: Issue #49 é bug/comportamento de UI state; testável em vitest sem Tauri; alinha a 020 (helpers puras).

**Alternatives considered**:
- Só corrigir `main.ts` ad-hoc — mais difícil de cobrir FR-013.
- Persistir activeSessionId em disco — rejeitado no clarify (não nesta fatia).

## Decision 2 — Orphan após refresh (clarify)

**Decision**: Se após `listSessions` o `activeSessionId` **não** está na lista → setar `activeSessionId = null` e pintar estado «Nenhuma sessão selecionada». NÃO manter id órfão com badge “inválida”.

**Rationale**: FR-006 + clarify; evita feed/status contra sessão inexistente no core.

**Alternatives considered**:
- Manter id + warning — ambíguo para Assistente/start.
- Auto-selecionar outro item da lista — rejeitado (no auto-select).

## Decision 3 — Sem auto-select do primeiro item (clarify)

**Decision**: Bootstrap e refresh **nunca** escolhem o primeiro item só porque a lista tem entradas e active é null. Ativação somente: (1) clique/select explícito, (2) create bem-sucedido.

**Rationale**: Issue pede seleção confiável, não default implícito; evita sessão errada em multi-sessão.

**Alternatives considered**:
- Auto-pick mais recente — UX surpresa e fora da issue.

## Decision 4 — Display do id (clarify)

**Decision**:

- Rótulo `session-active-id`: **id completo** sempre.
- Botões da lista: MAY truncar visualmente (`slice(0,8)…` atual OK) **desde que** `data-session-id` = id canônico completo e `onSelect` receba esse valor.
- Classe `session-selected` no item cujo `id === activeSessionId`.

**Rationale**: Densidade da lista + verificabilidade do id usado na captura.

**Alternatives considered**:
- Sempre full UUID em cada linha — ruidoso; opcional polish futuro.

## Decision 5 — Reuso da 020 para agent

**Decision**: Não reimplementar parse de cmdline, mismatch banner, CTA restart, empty states. US3 desta feature = **garantir / regressão** de que start/restart/guidance usam `activeSessionId` do picker e que id `session-YYYYMMDD-…` no agent gera mismatch (já coberto se `agentSessionId` ≠ active UUID). Gaps só se testes FR-013(e)(f) falharem.

**Rationale**: 020 entregou o alinhamento agent; 021 fecha o pré-requisito “active id realmente setado e estável”.

**Alternatives considered**:
- Duplicar FRs de mismatch na implementação — desperdício.

## Decision 6 — list-sessions vs id só STT

**Decision**: `listSessions` / session-core é a **única** fonte da lista UI. Nunca append de ids detectados na cmdline do agent. Docs explicam que `session-YYYYMMDD-HHMMSS` sozinho não cria entrada na lista.

**Rationale**: FR-007 / FR-015 / out of scope issue #49.

**Alternatives considered**:
- “Importar” id do agent para o core — exige create no core + ADR; fora de escopo.

## Decision 7 — Create → active

**Decision**: Manter fluxo: `createSession` → `refreshSessionList` → `selectSession(created.id)`. Em falha de create: erro legível, **não** setar active inventado. Em falha de refresh após create OK: ainda setar active com `created.id` se o create retornou id (operador pode trabalhar; próximo refresh bem-sucedido reconcilia).

**Rationale**: US2 / FR-005; create response já traz id canônico.

**Alternatives considered**:
- Só active se aparecer na lista — frágil se list eventual consistente.

## Decision 8 — Stack e testes

**Decision**: Vitest no `apps/desktop-shell`; reusar padrões de `session-picker.test.ts` e `agent-session-actions.test.ts`. Sem `cargo test` obrigatório nesta fatia salvo mudança no client Rust (não prevista).

**Rationale**: P10; lógica 100% TS no webview.

## Decision 9 — Docs

**Decision**: Atualizar `docs/development/running.md` e `docs/release/min-flow.md` com:

1. mesmo sessionId UI↔agent↔STT (já parcialmente na 020);
2. list-sessions = session-core only;
3. `session-YYYYMMDD-…` não lista sozinho;
4. select ≠ reconfig agent em execução.

**Rationale**: US4 / FR-014 / issue P1 docs.
