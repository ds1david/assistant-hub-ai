# Quickstart: validar a janela adaptativa de áudio (SF-022)

## Pré-requisitos

- WSL: venv em `.venv-transcription/` na raiz do monorepo (Python 3.12; o `python3` de sistema não
  tem `pytest` instalado).
- Nenhum hardware, GPU ou modelo Whisper real é necessário — toda a suíte roda com
  `FakeTranscriptionEngine` (`tests/conftest.py`) e amostras de latência sintéticas injetadas
  diretamente no `LatencyMetricsRegistry` (mesmo padrão de `tests/test_latency_metrics.py`).

## 1. Validação automatizada (WSL, sem GPU/hardware)

```bash
PYTHONPATH=services/transcription-service .venv-transcription/bin/python -m pytest -q \
  services/transcription-service/tests -k "adaptive_window"
```

**Resultado esperado**: todos os testes passam, cobrindo (ver `spec.md` FR-001..FR-011 e
`data-model.md`):

- **Unidade da política** (`tests/test_adaptive_window.py`, sem FastAPI/engine): encolhimento
  confirmado após N avaliações de `p95Ms` sustentado acima do limite (US1); piso respeitado, sem
  redução adicional além do mínimo (US1/AC3); recuperação gradual até o padrão após N avaliações
  saudáveis, sem ultrapassá-lo (US2); nenhuma reação a um único pico isolado nem a `sampleCount`
  insuficiente (FR-008); nenhuma reação com a flag desabilitada.
- **Integração HTTP/WebSocket** (`tests/test_adaptive_window_endpoint.py`, via
  `create_app(metrics_registry=...)` pré-populado com amostras sintéticas, como em
  `test_session_metrics_endpoint.py`): a janela efetivamente usada por `StreamingTranscriber` muda
  quando o `LatencyMetricsRegistry` já injetado indica degradação (prova de ponta a ponta, não só a
  função pura); dois canais da mesma sessão com perfis opostos convergem para janelas diferentes,
  sem vazamento entre canais (US3/FR-005); o payload do evento `transcript.partial.v2`/`final.v2`
  publicado continua validando contra `contracts/transcript-event.v2.schema.json` independente do
  tamanho de janela usado (US3/FR-006); `GET /v1/sessions/{sessionId}/metrics` reporta o
  `windowMs` atual por canal (FR-007); com a flag desabilitada (padrão), o comportamento é
  byte-a-byte idêntico ao pré-SF-022 (SC-007).

Rodar a suíte completa do serviço para checar ausência de regressão:

```bash
PYTHONPATH=services/transcription-service .venv-transcription/bin/python -m pytest -q \
  services/transcription-service/tests
```

Para confirmar em 3.10/3.11 (sem CI no repositório), usar `uv` com interpretador gerenciado, como já
validado na SF-017:

```bash
PYTHONPATH=services/transcription-service uv run --no-project --python 3.10 \
  --with-requirements services/transcription-service/requirements-dev.txt -- \
  pytest -q services/transcription-service/tests -k "adaptive_window"
```

## 2. Inspeção manual rápida (opcional, ainda sem hardware)

Com o app rodando localmente (`FakeTranscriptionEngine` ou modelo real, a gosto):

```bash
curl -s localhost:8000/v1/sessions/<sessionId>/metrics | jq '.channels[] | {channelId, p95Ms, windowMs}'
```

`windowMs` aparece `null` enquanto `adaptive_window_enabled=false` (padrão) ou antes da primeira
avaliação daquele canal; passa a refletir o valor efetivamente aplicado assim que a flag está ativa
e o canal já processou pelo menos uma transcrição.

## Referências

- Requisitos completos: `spec.md` (FR-001..FR-011, SC-001..SC-007, Clarifications).
- Entidades, estado e configuração: `data-model.md`.
- Decisões técnicas e alternativas rejeitadas: `research.md`.
- Precedente de observabilidade equivalente: `docs/validation/sf-016-latency-metrics.md`.
