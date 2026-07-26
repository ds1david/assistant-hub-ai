# Research: 026 R6 circuit breaker + streaming

## Decision 1 — Circuit breaker algorithm

**Decision**: Contador de falhas **consecutivas** por `providerId`; limiar default 5 → OPEN por 30s; depois HALF_OPEN com 1 tentativa; sucesso → CLOSED; falha → OPEN de novo.

**Rationale**: Simples, testável, adequado a single-process session-core. Sliding window adiciona complexidade sem ganho nesta fatia.

**Alternatives**: sliding window / failure rate — deferido.

## Decision 2 — O que conta como falha

**Decision**: Conta: TIMEOUT, RATE_LIMITED, AUTHENTICATION, MODEL_NOT_FOUND, GENERIC, e falha de stream.  
**Não conta**: CAPABILITY_MISMATCH, CIRCUIT_OPEN (skip sem chamar), provider disabled/ausente.

## Decision 3 — Novo error type

**Decision**: `InvocationErrorType.CIRCUIT_OPEN` quando o candidato seria chamado mas está OPEN e não há (ou esgotaram) fallbacks, ou quando se registra o skip na cadeia.

## Decision 4 — Streaming transport

**Decision**: `POST /api/ai-providers/invoke/stream` com `text/event-stream` (SSE).  
Eventos: `event: chunk` data JSON `{ "text": "..." }`; `event: done` data = `InvocationResult`-like; `event: error` data = resultado de falha.

**Rationale**: Amplamente suportado; Spring MVC suporta `SseEmitter`.

## Decision 5 — OpenAI stream parse

**Decision**: `stream: true` no body; ler linhas `data: {...}` até `[DONE]`; acumular `choices[0].delta.content`.

## Decision 6 — Cancel

**Decision**: `SseEmitter` onCompletion/onTimeout/onError + `AtomicBoolean cancelled`; adapter checa cancel entre chunks / interrupt HTTP.

## Decision 7 — Config

**Decision**: `AiProviderHubProperties` estendido (ou nested) com `circuitFailureThreshold`, `circuitOpenMs` — sem quebrar schema YAML de provedores (FR-013).
