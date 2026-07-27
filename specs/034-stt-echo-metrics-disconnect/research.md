# Research: STT disconnect final + echo metrics reliability

**Feature**: `specs/034-stt-echo-metrics-disconnect`  
**Date**: 2026-07-27

## R1 — Causa do flake `sampleCount` 1 vs 2

**Decision**: Tratar como **race de finalização no teardown**, não como bug da política de eco em si.

**Rationale**:
- Cenário de eco: system partial + mic (eco suprimido) + mic partial local + disconnect → esperado mic `sampleCount == 2` (partial local + disconnect final).
- PR #73: fila `asyncio.Queue(maxsize=2)` + worker podia dropar ou atrasar o tick de disconnect sob nest de WS system+mic.
- Follow-up na branch atual: mesmo com `join()` + “nunca dropar disconnect tick”, o **Starlette TestClient** envia `websocket.disconnect` e em seguida **cancela a tarefa ASGI** (`CancelScope`), abortando `finally` antes de `record_transcription` do final.

**Alternatives considered**:
- Só sleep arbitrário nos testes → mascara race, não corrige produtor.
- Só poll de métricas sem shield → aceita race no servidor se cancel vencer.
- Reintroduzir fila maior → não resolve CancelScope.

## R2 — Modelo de concorrência: sequencial vs worker queue

**Decision**: **Emit sequencial** na tarefa da conexão de áudio (`await emit` no loop de receive).

**Rationale**:
- Backpressure natural: próximo frame só após transcrever o atual.
- Disconnect residual roda no `finally` da mesma task (ou shielded child) sem competir por `task_done`/slots da fila.
- Simplifica raciocínio de “disconnect nunca dropado”.

**Alternatives considered**:
- Worker dedicado + prioridade disconnect → mais estado, já falhou com maxsize=2.
- Thread pool por janela → viola ordenação e complica métricas.

## R3 — Ordem: métrica antes de **qualquer** await no publish path

**Decision**: Chamar `metrics.record_transcription(...)` **antes** de:
1. prosódia (`asyncio.to_thread(estimate_prosody, …)` quando final + habilitada),
2. `websocket.send_json`,
3. `broadcaster.publish`.

**Rationale**:
- `LatencyMetricsRegistry` é síncrono e thread-safe (lock, sem await) — seguro no event loop.
- CancelScope no teardown pode abortar **qualquer** await (não só send): prosódia em final de disconnect era um gap se métrica viesse depois.
- “Entregue” para **`totalEvents`** = decisão de publicar o evento (ou metrics-only residual sob cancel extremo), não sucesso de todos os sockets.

**Alternatives considered**:
- Contar só após send OK → regressão no disconnect (cliente já morto).
- Contar após prosódia → flake se cancel durante `to_thread` no teardown.
- Contar no broadcaster por cliente → multiplica por N assinantes (viola FR-002).

## R4 — skip_direct_send em final de disconnect

**Decision**: Finais com `reason == "disconnect"` **não** enviam no WS de áudio; ainda fan-out no feed com timeout.

**Rationale**:
- Cliente de áudio está no teardown; send falha ou atrasa sem valor.
- Idle/max-open finals precisam do socket vivo para testes WS e para consumidores na mesma conexão.
- Feed `/ws/transcripts` e session-core (quando conectados) ainda podem observar o final.

**Alternatives considered**:
- Sempre try/send e ignorar erro → ok, mas skip evita ruído e latência no caminho crítico.
- Não fan-out disconnect finals → piora observabilidade.

## R5 — shield + fallback síncrono (metrics-only)

**Decision**: `await asyncio.shield(finalize_disconnect())` no `finally`; em `CancelledError` residual, se utterance ainda `open` com texto útil, `record_transcription` + `on_disconnect` best-effort **síncrono** — **sem** fan-out/async publish nesse ramo (spec Edge Cases / contract C7).

**Rationale**:
- Shield permite completar finalização sob cancel do TestClient/ASGI no caminho normal (contagem + feed).
- Fallback cobre o caso extremo em que o cancel atinge antes do shield agendar o trabalho útil: **preserva `totalEvents`**, não inventa I/O em cancel path.
- Aceita inconsistência rare “métrica sem evento no feed” em troca de não regredir o flake de contagem.

**Alternatives considered**:
- Background task fire-and-forget sem shield → pode morrer com o processo de request.
- Só aumentar timeouts de teste → flake residual em CI carregado.
- Forçar fan-out no cancel residual → exige criar task pós-cancel, mais frágil no TestClient.

## R6 — Timeouts de fan-out

**Decision**: **1,0 s** por `send_json` de assinante; **0,5 s** teto em `wait_for(broadcaster.publish(...))` no produtor.

**Rationale**:
- Um assinante travado não deve prender finalização/métricas do canal (edge case da spec).
- Valores alinhados à implementação atual e suficientes para loopback local de testes.

**Alternatives considered**:
- Sem timeout → hang sob subscriber lento.
- Timeout global só no publish sem per-client → um cliente ainda pode consumir quase o teto inteiro; per-client + teto é defesa em profundidade.

## R7 — Observação de métricas pós-teardown

**Decision**: Aceitar **poll até 2,0 s** (`wait_metrics`) em testes multi-canal; contagem final deve estabilizar sem perda permanente.

**Rationale**:
- Mesmo com shield, o contexto `with websocket` do TestClient pode retornar **antes** do ASGI `finally` terminar sob carga.
- Poll é contrato de teste/observador (SC-002), não desculpa para perda permanente.

## R8 — Eco e métricas

**Decision**: Manter ADR-0008: `echo.suppressed` → **return sem** `on_text` / sem `publish_transcript` / sem `record_transcription`. Residual no disconnect não reintroduz eco contado além da política de finalizer.

**Rationale**: Já correto semanticamente; flake era contagem do **final**, não do eco.

## R9 — Schema e API

**Decision**: **Nenhuma** mudança em `transcript-event.v2` nem no shape de `GET /v1/sessions/{sessionId}/metrics`.

**Rationale**: Problema é comportamento e race, não contrato de dados.

## Open items deferred to implement

- Confirmar stress ≥ 60× no quickstart local se CI não rodar stress por padrão.
- Opcional: uma linha em `docs/development/running.md` se o quickstart da feature não for suficiente (US4).
