# Validação SF-022 — janela adaptativa de áudio com base em métricas

Evidência automatizada da política de ajuste de janela de captura/segmentação por canal, sem GPU,
Docker, WASAPI ou download de modelo. O evento `transcript-event.v2` não muda.

## Arquitetura

- `app/adaptive_window.py` define `AdaptiveWindowState` (estado por canal), `AdaptiveWindowChannel`
  (decisão, instanciada uma vez por conexão WebSocket — nunca persiste entre reconexões) e
  `AdaptiveWindowRegistry` (espelho por app, thread-safe, só para observabilidade HTTP);
- a decisão usa exclusivamente o `p95Ms` já exposto por `LatencyMetricsRegistry` (SF-016) como sinal;
  `p50Ms`/`sampleCount` só servem para observabilidade e para a checagem de amostras mínimas —
  `LatencyMetricsRegistry` não é alterado por esta feature;
- a avaliação é orientada a evento: uma chamada a `evaluate()` por transcrição concluída do canal, em
  `app/main.py::audio_stream`, logo após `metrics.record_transcription(...)`;
- o teto de crescimento/recuperação é o próprio `whisper_window_seconds` configurado (não existe um
  máximo separado maior que o padrão); o piso é `adaptive_window_min_seconds`, sempre estritamente
  maior que `whisper_overlap_seconds` (validado no construtor de `AdaptiveWindowChannel`);
- com a flag `adaptive_window_enabled` desabilitada (padrão), nenhum `AdaptiveWindowChannel` é
  instanciado — o comportamento é idêntico ao pré-SF-022 (janela estática).

## Algoritmo de histerese

A cada avaliação, calcula-se um `desired` a partir do `p95Ms` e dos limites configurados:

- `"down"` se `p95Ms > adaptive_window_latency_high_ms` e a janela ainda está acima do piso;
- `"up"` se `p95Ms < adaptive_window_latency_low_ms` e a janela ainda está abaixo do teto;
- `"stable"` caso contrário (inclui `sampleCount` insuficiente ou `p95Ms` ausente).

Se `desired` for igual à direção já em vigor (`active_direction`), aplica-se um passo
(`adaptive_window_step_seconds`) imediatamente — continuar na mesma direção não exige nova
confirmação. Se `desired` divergir da direção em vigor (ativação a partir de repouso, ou reversão),
a mudança só é aplicada depois de `adaptive_window_stable_evaluations` avaliações consecutivas
concordando com o novo `desired`; uma avaliação com dado insuficiente zera essa confirmação pendente.

### Número máximo de avaliações para atingir o piso/teto (SC-001/SC-002)

Com os valores padrão (`adaptive_window_min_seconds=1.6`, `whisper_window_seconds=3.2`,
`adaptive_window_step_seconds=0.4`, `adaptive_window_stable_evaluations=3`): a distância entre piso e
teto é `(3.2 - 1.6) / 0.4 = 4` passos. Partindo do repouso, com o sinal sustentado (todas as avaliações
concordando), a primeira ativação consome `adaptive_window_stable_evaluations` avaliações (3) — a
terceira já aplica o primeiro passo — e cada passo seguinte consome exatamente uma avaliação (sem
reconfirmação). Portanto, o número máximo de avaliações para ir do teto ao piso (ou vice-versa) sob
sinal sustentado é **3 + (4 − 1) = 6 avaliações**, nunca mais que isso.

## Onde

- Política e registry: `services/transcription-service/app/adaptive_window.py`
- Configuração (7 campos `adaptive_window_*`): `services/transcription-service/app/config.py`
- Capacidade de trocar a janela em runtime: `StreamingTranscriber.set_window_seconds` em
  `services/transcription-service/app/transcriber.py`
- Wiring e campo `windowMs`: `services/transcription-service/app/main.py`
- Testes de unidade da política: `services/transcription-service/tests/test_adaptive_window.py`
- Testes de integração (ponta a ponta, isolamento, contrato, observabilidade):
  `services/transcription-service/tests/test_adaptive_window_endpoint.py`

## O que é coberto

- janela permanece parada com `p95Ms` saudável (dentro da faixa) e com um único pico isolado;
- encolhimento em passo controlado após confirmação sustentada, nunca abaixo do piso;
- estado "no piso" observável (`AdaptiveWindowChannel.at_floor`), sem redução adicional;
- amostras insuficientes ou `p95Ms` ausente não disparam ajuste e zeram a confirmação pendente;
- recuperação em passo controlado após confirmação sustentada de latência saudável, nunca acima do
  teto (`whisper_window_seconds`);
- oscilação de `p95Ms` entre avaliações consecutivas não reverte a direção a cada avaliação
  (histerese);
- validação de que o piso configurado precisa ficar estritamente acima do overlap;
- ponta a ponta via WebSocket: janela realmente aplicada por `StreamingTranscriber` muda quando a
  flag está habilitada, e permanece estática quando desabilitada (SC-007);
- dois canais da mesma sessão com perfis de latência opostos convergem para janelas independentes,
  sem vazamento de estado entre canais;
- evento `transcript.partial.v2`/`transcript.final.v2` publicado com janela ajustada continua
  validando contra `contracts/transcript-event.v2.schema.json`, sem nenhum campo novo relacionado ao
  tamanho de janela;
- `GET /v1/sessions/{sessionId}/metrics` reporta `windowMs` por canal, refletindo o valor realmente
  aplicado; `null` quando a flag está desabilitada ou o canal ainda não avaliou nenhuma vez.

## Como executar

```bash
PYTHONPATH=services/transcription-service .venv-transcription/bin/python -m pytest -q \
  services/transcription-service/tests -k "adaptive_window"
```

Validado também em Python 3.10 e 3.11 via `uv` (sem CI no repositório), como já feito na SF-017:

```bash
PYTHONPATH=services/transcription-service uv run --no-project --python 3.10 \
  --with-requirements services/transcription-service/requirements-dev.txt -- \
  pytest -q services/transcription-service/tests -k "adaptive_window"
```

Resultado: 17/17 testes de `adaptive_window` passam em 3.10, 3.11 e 3.12 (venv de desenvolvimento);
78/78 testes da suíte completa do `transcription-service` passam sem regressão.
