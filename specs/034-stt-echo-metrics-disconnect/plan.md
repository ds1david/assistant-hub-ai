# Implementation Plan: STT — finalização no disconnect e métricas de eco confiáveis

**Branch**: `fix/stt-echo-metrics-disconnect-final`  
**Feature dir**: `specs/034-stt-echo-metrics-disconnect` (nome **independente** do branch git — intencional)  
**Spec**: `specs/034-stt-echo-metrics-disconnect/spec.md`  
**Date**: 2026-07-27  
**Input**: Feature specification from `/specs/034-stt-echo-metrics-disconnect/spec.md`  
**Related**: PR [#73](https://github.com/ds1david/assistant-hub-ai/pull/73); `specs/024-issue-55-stt-final-utterance`; ADR-0008

## Summary

O STT já emite `transcript.final.v2` por idle/max-open e no residual de disconnect (024), conta latência por canal em `GET /v1/sessions/{sessionId}/metrics`, e suprime eco de microfone (ADR-0008). Sob teardown multi-canal (system + mic) e sob cancelamento do ASGI/TestClient após `websocket.disconnect`, a finalização residual e o `record_transcription` do final de disconnect podiam **não completar** → `totalEvents`/`sampleCount` 1 em vez de 2 (flake do teste de eco).

Esta feature **endurece o caminho de disconnect e a contagem de métricas**:

1. Emissão **sequencial** na tarefa da conexão de áudio (elimina race de fila `maxsize=2` / worker).
2. **Métrica antes de qualquer await no caminho de publicação** — incluindo **prosódia** (`to_thread`), envio ao WS de áudio e fan-out do feed; final `disconnect` **pula** send direto no WS de áudio, mantém fan-out com timeout no caminho normal.
3. `asyncio.shield` (ou equivalente) na finalização residual + fallback síncrono **metrics-only** se cancelamento vencer o shield (fan-out best-effort; contagem não se perde).
4. Fan-out do feed com **timeout por assinante (1,0 s)** e teto no publish do produtor (**0,5 s**).
5. Testes: `wait_metrics` (poll ≤ 2,0 s), eco multi-canal estável, stress ≥ 60×; asserts de produto preferem **`totalEvents`**.

**Sem** mudança de schema `transcript-event.v2` nem do JSON do endpoint de métricas. Escopo só `services/transcription-service` (+ docs/quickstart desta pasta).

## Technical Context

**Language/Version**: Python 3.11+ (transcription-service)

**Primary Dependencies**: FastAPI / Starlette WebSocket; asyncio; `LatencyMetricsRegistry`; `UtteranceFinalizer` (024); `echo_suppressor` (ADR-0008); pytest + FakeTranscriptionEngine

**Storage**: Métricas e estado de utterance **em memória** por sessão/canal; sem persistência nova

**Testing**: pytest no WSL (`services/transcription-service/tests`); sem GPU/WASAPI; stress opcional local do cenário de eco

**Target Platform**: STT em WSL/Docker; agent Windows e session-core **inalterados**

**Project Type**: monorepo reliability slice — STT disconnect path + metrics tests

**Performance Goals**: finalização residual completa sob teardown; contagens finais observáveis em ≤ 2 s de poll; fan-out não bloqueia produtor além dos timeouts

**Constraints**: P5 identidade; P9 logs sem PCM/texto sensível em excesso; P10 CI sem GPU; zero schema break; não redesenhar idle/max-open (024)

**Scale/Scope**: 1 operador local; tipicamente 2 canais (mic + system); 4 user stories; 1 serviço

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Notas |
|-----------|--------|-------|
| P1 Spec antes de domínio | Pass | Spec clarified + plan + tasks nesta pasta |
| P2 Core independente de fornecedor | Pass | Só STT local; sem LLM/provedor |
| P3 WSL-first / Windows só captura | Pass | Mudança só transcription-service (Linux) |
| P4 Contratos versionados | Pass | Sem alteração de schema v2; contrato de comportamento documentado em `contracts/` |
| P5 Canal/origem ponta a ponta | Pass | Final/métricas herdam session/channel/sourceType/label |
| P6 Isolamento endpoint | Pass | Estado por conexão de canal |
| P7 endpointId | N/A | Fora de escopo |
| P8 Automação com autorização | Pass | Sem merge/force-push |
| P9 Privacidade | Pass* | FR-010 no caminho disconnect/métricas (ids/contadores, sem PCM). *Logs INFO preexistentes de eco (`text`/`matched`) ficam **fora de escopo** desta fatia — ver spec Out of Scope. |
| P10 Testes determinísticos | Pass | Fake engine + poll helper; sem GPU |

**Post-design re-check**: Pass — sem serviço novo, sem captura WASAPI, sem schema break, métricas sincronas thread-safe. Analyze remediação 2026-07-27 (I1/I2/C1/U1) alinhou plan/spec/contract.

## Project Structure

### Documentation (this feature)

```text
specs/034-stt-echo-metrics-disconnect/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── session-metrics-disconnect.md
├── checklists/
│   ├── requirements.md
│   └── disconnect-metrics.md
└── tasks.md
```

### Source Code (repository root)

```text
services/transcription-service/
├── app/
│   ├── main.py              # sequential emit; publish_transcript metrics-first;
│   │                        # skip_direct_send on disconnect; shield finalize_disconnect
│   ├── broadcast.py         # wait_for per-subscriber send (1.0s)
│   ├── metrics.py           # LatencyMetricsRegistry (inalterado semanticamente)
│   ├── utterance.py         # on_disconnect (024; sem redesenho)
│   └── echo_suppression.py  # suppressed → no record (inalterado semanticamente)
└── tests/
    ├── test_session_metrics_endpoint.py  # wait_metrics; eco multi-canal; contagens
    ├── conftest.py                       # FakeTranscriptionEngine thread-safe se necessário
    ├── test_ws_utterance_final.py        # regressão: no double final on disconnect after idle
    └── test_transcript_endpoint.py       # regressão totalEvents com finals

# Opcional (US4):
docs/development/running.md   # uma linha: partial + disconnect final nas métricas
```

**Structure Decision**: Toda a lógica permanece no **transcription-service**. Não tocar agent, session-core nem desktop-shell. Não reintroduzir worker queue por canal.

## Complexity Tracking

> Nenhuma violação constitucional a justificar.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
