# Quickstart: validar disconnect final + métricas de eco

**Feature**: `specs/034-stt-echo-metrics-disconnect`  
**Date**: 2026-07-27

## Prerequisites

- WSL com Python 3 do projeto
- Dependências do `services/transcription-service` instaladas (venv do serviço)
- **Sem** GPU e **sem** Windows/WASAPI

## 1. Suite de métricas de sessão

```bash
cd /home/david/workspace/assistant-hub-ai
PYTHONPATH=services/transcription-service pytest -q \
  services/transcription-service/tests/test_session_metrics_endpoint.py
```

**Esperado**: todos passam, incluindo:

| Teste | Aceite |
|-------|--------|
| `test_delivered_event_is_measured_once` | `totalEvents == 2` e `sampleCount == 2` (partial + disconnect final) |
| `test_feed_subscribers_do_not_duplicate_samples` | fan-out não multiplica |
| `test_sessions_are_isolated_over_http` | sessões isoladas |
| `test_channels_are_isolated_over_http` | canais isolados, cada um `totalEvents`/`sampleCount` == 2 |
| `test_suppressed_echo_is_not_counted_as_delivered` | mic e system `totalEvents`/`sampleCount` == 2; eco não eleva mic |

## 2. Stress do cenário de eco (SC-005)

```bash
PYTHONPATH=services/transcription-service pytest -q \
  services/transcription-service/tests/test_session_metrics_endpoint.py \
  -k suppressed_echo --count=60
```

Se o plugin `pytest-repeat` / `--count` não estiver disponível:

```bash
for i in $(seq 1 60); do
  PYTHONPATH=services/transcription-service pytest -q \
    services/transcription-service/tests/test_session_metrics_endpoint.py \
    -k suppressed_echo || exit 1
done
echo "60/60 ok"
```

**Esperado**: 0 falhas de assert em `sampleCount`.

## 3. Regressão de utterance final (024)

```bash
PYTHONPATH=services/transcription-service pytest -q \
  services/transcription-service/tests/test_ws_utterance_final.py \
  services/transcription-service/tests/test_utterance_finalizer.py
```

**Esperado**: disconnect após idle **não** duplica final; disconnect com open emite um final.

## 4. Suite completa do serviço (gate local)

```bash
PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests
```

## 5. Observação manual do endpoint (opcional)

Com STT no ar e agent enviando áudio para `SESSION`:

```bash
curl -s "http://127.0.0.1:8001/v1/sessions/${SESSION}/metrics" | jq .
```

Após parar o agent (disconnect dos canais), reconsultar se necessário (≤ 2 s): cada canal com fala útil deve refletir partials + final residual; eco de mic não deve inflar contagem além da fala local.

## Interpretação rápida

| Contagem | Significado |
|----------|-------------|
| partial only, disconnect sem final | utterance já idle sem residual **ou** nunca houve texto útil |
| `totalEvents == 2` (e `sampleCount == 2` se ring folgado) após 1 partial + stop | partial + disconnect final (caso típico dos testes) |
| mic `totalEvents == 2` com eco no meio | eco suprimido não contou; partial local + final |
| `totalEvents > sampleCount` | retenção do ring cortou amostras de latência; contagem cumulativa prevalece |

Ver contrato: `contracts/session-metrics-disconnect.md`.
