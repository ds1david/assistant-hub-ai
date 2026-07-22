# Data Model: Janela adaptativa de áudio com base em métricas (SF-022)

Nenhuma persistência durável é introduzida (sem banco, sem schema de contrato de evento novo — FR-006).
As entidades abaixo são estruturas em memória, dentro do processo do `transcription-service`.

## AdaptiveWindowState

Estado de decisão de um canal, interno a `AdaptiveWindowChannel` — vive e morre com a conexão
WebSocket daquele canal (mesmo ciclo de vida do `StreamingTranscriber` da conexão); nunca persiste
entre reconexões (Edge Case da spec, incluindo hot-plug SF-019).

| Campo | Tipo | Notas |
|---|---|---|
| `window_seconds` | `float` | Janela atualmente aplicada; inicia em `whisper_window_seconds` (padrão/teto — ver Clarifications). |
| `active_direction` | `Literal["down", "up", "stable"]` | Direção confirmada e em vigor; `"stable"` = nenhum ajuste em curso. |
| `pending_direction` | `Literal["down", "up"] \| None` | Direção candidata ainda não confirmada (ativação a partir de `stable`, ou reversão). |
| `pending_count` | `int` | Avaliações consecutivas concordando com `pending_direction`; zerado quando o sinal muda ou fica saudável. |

**Regras de transição** (ver `research.md` §3 para o algoritmo completo):

- Amostras insuficientes (`sample_count < adaptive_window_min_samples`) ou `p95Ms` ausente → nenhuma mudança; `pending_count` zera.
- Sinal dentro da faixa saudável (`adaptive_window_latency_low_ms <= p95Ms <= adaptive_window_latency_high_ms`, ou já no limite do lado relevante) → `active_direction = "stable"`; `pending_count` zera; janela não muda.
- Sinal concorda com `active_direction` já em vigor → aplica um passo (`± adaptive_window_step_seconds`) imediatamente, recortado em `[adaptive_window_min_seconds, whisper_window_seconds]`.
- Sinal diverge de `active_direction` (ativação inicial ou reversão) → acumula `pending_count`; só muda `active_direction` e aplica o primeiro passo quando `pending_count >= adaptive_window_stable_evaluations`.

## AdaptiveWindowRegistry (observabilidade)

Registro por app (não por conexão), injetável em `create_app` como `metrics_registry`/`consolidator`
já são hoje. Guarda apenas o último valor de janela aplicado por canal, para leitura via HTTP —
nenhuma lógica de decisão vive aqui.

| Campo | Tipo | Notas |
|---|---|---|
| `(session_id, channel_id)` → `window_ms` | `dict[tuple[str, str], int]` | Espelha o `window_seconds` mais recente de `AdaptiveWindowState`, em milissegundos, protegido por lock (mesmo padrão de `LatencyMetricsRegistry`). |

Sem eviction dedicada nova: usa o mesmo teto (`metrics_max_channels`) já configurado para a SF-016,
já que ambos os registries crescem com o mesmo universo de canais ativos por sessão.

## Configuração (`app/config.py::Settings`, campos novos)

| Campo | Tipo | Padrão | Notas |
|---|---|---|---|
| `adaptive_window_enabled` | `bool` | `False` | FR-011 — opt-in; ver Clarifications Q4. |
| `adaptive_window_min_seconds` | `float` | `1.6` | FR-002 — piso; deve ficar estritamente acima de `whisper_overlap_seconds`. |
| `adaptive_window_latency_high_ms` | `int` | `1600` | Limite de `p95Ms` que inicia/mantém o encolhimento. |
| `adaptive_window_latency_low_ms` | `int` | `600` | Limite de `p95Ms` que inicia/mantém a recuperação. |
| `adaptive_window_step_seconds` | `float` | `0.4` | FR-004 — passo controlado por avaliação. |
| `adaptive_window_stable_evaluations` | `int` | `3` | FR-003 — período mínimo de confirmação (ativação e reversão). |
| `adaptive_window_min_samples` | `int` | `5` | FR-008 — amostras mínimas de `sampleCount` antes de confiar no sinal. |

**Relação com entidades já existentes (sem alteração)**:

- **Snapshot de latência (SF-016)** — `ChannelLatencySnapshot`/`SessionMetricsSnapshot` em `app/metrics.py`; `AdaptiveWindowChannel.evaluate` consome `p95_ms`/`sample_count` de um `ChannelLatencySnapshot` obtido via `LatencyMetricsRegistry.session_snapshot(session_id)` (método já existente, sem alteração — ver research.md §1).
- **`StreamingTranscriber`** (`app/transcriber.py`) — ganha o método aditivo `set_window_seconds(seconds: float) -> None` (research.md §2); nenhum outro membro muda.
- **Evento `transcript-event.v2`** (`contracts/transcript-event.v2.schema.json`) — inalterado (FR-006); nenhuma entidade nova desta feature aparece no payload do evento.
