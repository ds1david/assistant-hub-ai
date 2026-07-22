# Implementation Plan: Janela adaptativa de áudio com base em métricas (SF-022)

**Branch**: `008-sf-022-adaptive-window` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-sf-022-adaptive-window/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

O `transcription-service` passa a ajustar, por canal, o tamanho da janela de captura/segmentação
(`whisper_window_seconds`) com base no `p95Ms` de latência já exposto pela SF-016
(`GET /v1/sessions/{sessionId}/metrics`), atrás de uma flag desabilitada por padrão
(`adaptive_window_enabled`). Tecnicamente: um novo módulo `app/adaptive_window.py` introduz
`AdaptiveWindowChannel` (máquina de estados por conexão/canal, com histerese e passo controlado) e
`AdaptiveWindowRegistry` (espelho por app, só para observabilidade via HTTP); `StreamingTranscriber`
ganha um método aditivo `set_window_seconds`; `main.py` liga as duas peças no handler
`audio_stream`, sem alterar `LatencyMetricsRegistry` (SF-016) nem o contrato
`transcript-event.v2.schema.json` (FR-006). Sem GPU/hardware nos testes — tudo sintético, seguindo o
padrão já usado pela suíte de `transcription-service`.

## Technical Context

**Language/Version**: Python 3.10/3.11 (mesmo suporte já validado da suíte do `transcription-service`; venv de desenvolvimento em `.venv-transcription/` na raiz do monorepo, Python 3.12, mas a suíte também é validada em 3.10/3.11 via `uv run --python 3.10/3.11`).

**Primary Dependencies**: Nenhuma dependência nova. Reaproveita `fastapi`, `pydantic-settings` (`Settings` em `app/config.py`) e `numpy`/`faster-whisper` já presentes em `services/transcription-service/requirements.txt`.

**Storage**: Em memória, no mesmo processo do serviço. Sem banco novo — persistência durável de métricas ou de estado de ajuste está fora de escopo (spec Assumptions).

**Testing**: `pytest` (já configurado em `requirements-dev.txt`), seguindo o padrão existente de `tests/test_latency_metrics.py` (unidade, sem FastAPI) e `tests/test_session_metrics_endpoint.py` (integração via `fastapi.testclient.TestClient` + `create_app(metrics_registry=...)` pré-populado) — nenhum teste depende de GPU, hardware de áudio ou download de modelo (FR-009).

**Target Platform**: Serviço Linux (WSL/Docker, ADR-0005), mesmo ambiente do `transcription-service` hoje; nenhuma mudança de plataforma ou de imagem Docker.

**Project Type**: Extensão de um serviço backend já existente (`services/transcription-service`); nenhum serviço ou módulo novo.

**Performance Goals**: Qualitativo — reduzir o tempo de recuperação de latência sob carga (US1) sem introduzir custo perceptível quando saudável ou quando a flag está desabilitada (SC-007). Nenhum SLA numérico novo além dos limiares configuráveis documentados em `research.md` §6.

**Constraints**: Teto de janela = `whisper_window_seconds` atual, nunca ultrapassado (Clarifications); piso estritamente acima de `whisper_overlap_seconds`; avaliação orientada a evento (uma por transcrição concluída por canal), sem timer novo; decisão baseada só em `p95Ms` (`p50Ms`/`sampleCount` apenas observabilidade/gating de amostras); contrato `transcript-event.v2` inalterado (FR-006); `LatencyMetricsRegistry` (SF-016) não é alterado (spec Assumptions).

**Scale/Scope**: Um módulo novo pequeno (`adaptive_window.py`), um método aditivo em `transcriber.py`, ~7 campos novos de configuração em `config.py`, alterações pontuais em `main.py` (wiring + campo `windowMs` no endpoint de métricas já existente) e os testes correspondentes. Nenhuma UI, nenhum serviço novo, nenhuma persistência nova.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|---|---|
| P1 — Especificação antes de código | PASS. `spec.md` cobre requisitos (FR-001..FR-011), critérios de aceite e fora de escopo, com clarificações resolvidas antes deste plano; gate humano G1 segue pendente de confirmação explícita antes do Implement. |
| P2 — Core independente de fornecedores | PASS. Nenhum SDK de fornecedor de IA é importado; a política consome apenas métricas já internas ao próprio serviço (SF-016). |
| P3 — WSL-first | PASS. Python/pytest continuam rodando no WSL; nada de WASAPI/COM é tocado por esta feature. |
| P4 — Contratos versionados | PASS. `contracts/transcript-event.v2.schema.json` não é alterado (FR-006); o campo aditivo `windowMs` entra num endpoint de observabilidade já não-versionado (`/metrics`, documentado só em `docs/validation/`), não num contrato de evento — nenhum ADR exigido. |
| P5 — Separação por canal e origem | PASS — é o próprio objetivo de isolamento da feature (FR-005). Camada de decisão: cada canal tem seu próprio `AdaptiveWindowChannel`, sem estado compartilhado entre canais. Camada de observabilidade: `AdaptiveWindowRegistry` é um único objeto por app, mas o isolamento vem do chaveamento por `(sessionId, channelId)` — nenhuma leitura/escrita de um canal afeta a entrada de outro (fecha CHK019). |
| P6 — Isolamento de endpoint de áudio | N/A. Esta feature não toca a captura WASAPI nem o processo por endpoint (`windows-audio-agent`); atua inteiramente dentro do `transcription-service`. |
| P7 — Identidade de dispositivo | N/A. Nenhuma resolução de dispositivo é feita ou alterada por esta feature. |
| P8 — Automação com autorização | PASS. Nenhum merge/force-push/fechamento de issue automatizado é proposto por este plano. |
| P9 — Privacidade por padrão | PASS. O log de mudança de janela (research.md §4) registra `sessionId`/`channelId`/valores de janela — nenhum texto transcrito, áudio bruto, segredo ou token é introduzido em log por esta feature. |
| P10 — Qualidade determinística | PASS. Todos os testes planejados (unidade da política + integração via `TestClient`/métricas sintéticas pré-populadas) rodam sem GPU nem hardware de áudio físico (FR-009/SC-005). |

Nenhuma violação exige entrada em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/008-sf-022-adaptive-window/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

Sem `contracts/` nesta feature: nenhum contrato de evento versionado é criado ou alterado
(`transcript-event.v2.schema.json` permanece como está — FR-006); o único artefato de interface
tocado é um endpoint HTTP de observabilidade já não-versionado, documentado em `research.md` §4 e
`quickstart.md`.

### Source Code (repository root)

```text
services/transcription-service/
├── app/
│   ├── config.py            # + 7 campos novos em Settings (adaptive_window_*, ver data-model.md)
│   ├── transcriber.py        # + StreamingTranscriber.set_window_seconds(seconds: float)
│   ├── adaptive_window.py    # novo: AdaptiveWindowChannel (decisão, por conexão/canal)
│   │                          #       AdaptiveWindowRegistry (observabilidade, por app)
│   └── main.py                # wiring em audio_stream (§1 research.md) + campo `windowMs`
│                                # no handler já existente de GET /v1/sessions/{sessionId}/metrics
└── tests/
    ├── test_adaptive_window.py          # unidade: AdaptiveWindowChannel (US1/US2, hysteresis, piso/teto, FR-008)
    └── test_adaptive_window_endpoint.py # integração: wiring completo via TestClient + métricas pré-populadas (US1/US2/US3, SC-003, SC-007)
```

**Structure Decision**: Extensão de um serviço já existente (`services/transcription-service`), sem
novo módulo/serviço no monorepo. Todo o código novo fica num módulo irmão (`adaptive_window.py`) aos
módulos já existentes (`metrics.py`, `consolidation.py`, `echo_suppression.py`) — mesmo padrão
arquitetural: um registry pequeno e injetável por app, mais uma peça de decisão por conexão. O
acoplamento com a SF-016 passa só pela leitura de `session_snapshot()` já existente; nenhuma classe
de `metrics.py` é modificada.

## Complexity Tracking

*Não se aplica — nenhuma violação de Constitution Check identificada.*
