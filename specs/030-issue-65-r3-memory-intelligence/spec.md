# Feature Specification: R3.2 Memory Hub — busca, decisões e referências

**Feature Branch**: `feature/issue-65-r3-memory-intelligence`  
**GitHub Issue**: [#65](https://github.com/ds1david/assistant-hub-ai/issues/65)  
**Epic**: [#63](https://github.com/ds1david/assistant-hub-ai/issues/63)  
**Created**: 2026-07-26  
**Status**: Implemented (P0)

**Input**: R3.2 sobre Memory Hub 013 — busca textual/temporal, extração heurística de decisões/ações, UI Memory no shell. Embeddings e cite-no-live-answer = P1 fora desta fatia.

## User Stories

### US1 — Buscar trechos da sessão (P1)
Operador busca por texto e filtros de origem/tempo nos eventos da sessão ativa.

### US2 — Ver decisões/ações extraídas (P1)
Itens heurísticos (DECISION / ACTION / COMMITMENT) listados a partir do transcript.

### US3 — Painel Memory no shell (P2)
Superfície UI com busca e lista de memory items da sessão ativa.

## Requirements

- **FR-001**: API `GET /api/sessions/{id}/search` com `q`, opcional `sourceType`, `from`, `to`, `limit` (default 50, max 200).
- **FR-002**: Hits incluem eventId, snippet, sourceType/channelId de correlation, occurredAt; case-insensitive contains em `payload.text`.
- **FR-003**: API `GET /api/sessions/{id}/memory-items` retorna itens extraídos heuristicamente.
- **FR-004**: Extrator determinístico testável (pt/en keywords); sem GPU/LLM nesta fatia.
- **FR-005**: Shell painel Memory: busca + resultados + memory items; sessão ativa.
- **FR-006**: Logs MUST NOT dump transcript completo (P9).
- **FR-007**: Testes JUnit + Vitest sem GPU.

## Out of Scope
Embeddings, live-answer cite, multi-device, R4 visual.
