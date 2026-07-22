# Research: Janela adaptativa de áudio com base em métricas (SF-022)

## 1. Onde a janela adaptativa se conecta ao pipeline existente

**Decision**: Um novo módulo `app/adaptive_window.py` com duas peças pequenas e independentes:

- `AdaptiveWindowChannel` — objeto **por conexão** (instanciado junto com `StreamingTranscriber` dentro do handler `audio_stream`, uma vez por canal/sessão), estado puro em memória (janela atual, direção em vigor, contador de confirmação). Método `evaluate(p95_ms, sample_count) -> float` decide e retorna a janela (segundos) a aplicar.
- `AdaptiveWindowRegistry` — registro **por app** (injetável em `create_app`, como já ocorre com `metrics_registry`/`consolidator`), guarda só o último valor de janela aplicado por `(sessionId, channelId)` para observabilidade via HTTP. Não recalcula nada, apenas espelha o que `AdaptiveWindowChannel` decidiu.

Em `main.py::audio_stream`, logo após a linha existente `metrics.record_transcription(...)`: se `settings.adaptive_window_enabled`, obter `metrics.session_snapshot(session_id)` (método já existente, sem alteração), localizar o canal (`channel_id`) no `snapshot.channels`, chamar `adaptive_window.evaluate(p95_ms=channel.p95_ms, sample_count=channel.sample_count)`, aplicar o resultado via `transcriber.set_window_seconds(...)` (novo método, ver §2) e replicar o valor no `AdaptiveWindowRegistry`.

**Rationale**: `StreamingTranscriber` já é instanciado uma vez por conexão WebSocket (uma por canal) — reaproveitar essa mesma vida útil para o estado de ajuste dá isolamento por canal (FR-005) de graça, sem precisar de um dicionário chaveado por `(sessionId, channelId)` para a decisão em si, e sem lock adicional (cada `AdaptiveWindowChannel` só é tocado pela mesma task assíncrona do seu canal). Isso também casa com o Edge Case já definido na spec: um canal reconectado (inclusive hot-plug) não herda estado — como o objeto morre com a conexão, isso é automático, não uma regra a mais para implementar.

**Alternatives considered**:
- **Guardar o estado de decisão em um registry único chaveado por `(sessionId, channelId)`, análogo ao `LatencyMetricsRegistry`**: rejeitado para a *decisão* — adicionaria lock e gestão de ciclo de vida (quando apagar a entrada?) para resolver um problema que o próprio ciclo de vida do WebSocket já resolve. Mantido, porém, para a parte de *observabilidade* (ver §4), que precisa sobreviver fora do escopo da própria conexão (consultada por um GET HTTP separado).
- **Alterar `LatencyMetricsRegistry` (SF-016) para incluir um método de leitura por canal único**: rejeitado — a spec já assume explicitamente que a SF-016 não é alterada; `session_snapshot(session_id)` já existe e o custo de recalcular percentis para todos os canais da sessão a cada transcrição concluída é limitado por `metrics_max_channels` (64 por padrão) e ocorre só uma vez por evento entregue, não por chunk de áudio — aceitável e mais simples que abrir uma exceção à assunção da spec.

## 2. Aplicar uma nova janela em um `StreamingTranscriber` já em uso

**Decision**: adicionar `StreamingTranscriber.set_window_seconds(seconds: float) -> None`, que recalcula `_window_bytes` a partir do novo valor (mantendo `_overlap_bytes` fixo, vindo de `settings.whisper_overlap_seconds`) e levanta `ValueError` se o novo valor não ficar estritamente acima do overlap — mesma invariante já validada em `__init__` hoje.

**Rationale**: `append()` já lê `self._window_bytes` a cada chamada (não captura o valor uma vúnica vez no fechamento), então mudar esse atributo entre chamadas já é seguro pelo desenho atual: se o buffer acumulado já for maior que a nova janela (menor), a próxima transcrição dispara imediatamente com o novo tamanho; se for menor (maior), a acumulação continua normalmente até atingir o novo alvo. Nenhuma mudança em `append()`/`flush()` é necessária.

**Alternatives considered**:
- **Recriar o `StreamingTranscriber` inteiro a cada ajuste**: rejeitado — descartaria o buffer de áudio já acumulado (perda de contexto/possível corte de fala no meio) sem necessidade, quando um simples ajuste do atributo já é seguro.

## 3. Máquina de estados de histerese (encolher/crescer)

**Decision**: `AdaptiveWindowChannel` mantém `window_seconds` (inicia em `whisper_window_seconds`), `active_direction: "down" | "up" | "stable"` e um par de confirmação `(pending_direction, pending_count)`.

A cada `evaluate(p95_ms, sample_count)`:

1. Se `sample_count < adaptive_window_min_samples` ou `p95_ms is None`: nenhuma mudança (FR-008); confirmação pendente é zerada (dado insuficiente não deve "contar" para nenhuma direção).
2. Calcular o `desired` da avaliação:
   - `"down"` se `p95_ms > adaptive_window_latency_high_ms` **e** `window_seconds > adaptive_window_min_seconds`;
   - `"up"` se `p95_ms < adaptive_window_latency_low_ms` **e** `window_seconds < whisper_window_seconds` (o padrão é o teto, ver Clarifications);
   - `"stable"` caso contrário (zona saudável entre os dois limites, ou já no piso/teto do lado relevante).
3. Se `desired == "stable"`: `active_direction = "stable"`; zera confirmação; janela não muda.
4. Se `desired == active_direction` (continuação de uma direção já confirmada e em vigor): aplica um passo (`± adaptive_window_step_seconds`, sempre recortado para `[min_seconds, whisper_window_seconds]`) **imediatamente**, sem exigir nova confirmação — isto não é "mudança de direção" (FR-003 só exige confirmação para ativar/reverter).
5. Se `desired != active_direction` (primeira ativação a partir de `"stable"`, ou reversão): acumula confirmação —
   - `pending_direction == desired` → `pending_count += 1`; senão reinicia (`pending_direction = desired`, `pending_count = 1`).
   - Quando `pending_count >= adaptive_window_stable_evaluations`: `active_direction = desired`, aplica o primeiro passo, zera a confirmação.
   - Enquanto não atingir o limite: janela não muda (é exatamente o "de forma sustentada, não uma amostra isolada" da US1/AC2 e o "período mínimo de avaliações consecutivas" da US2/AC1).

**Rationale**: cobre as duas exigências textuais da spec — a ativação inicial (encolher ou crescer a partir do repouso) exige N avaliações consecutivas concordantes (evita reagir a um único pico), e uma reversão de direção também exige a mesma confirmação (evita a oscilação que a issue pede para evitar). Uma vez confirmada e em vigor, a continuação no mesmo sentido aplica um passo por avaliação — do contrário, encolher dos 3.2s até o piso de 1.6s exigiria `stable_evaluations × passos` avaliações, tornando a resposta lenta demais para o cenário de latência já claramente degradada que a US1 descreve.

**Alternatives considered**:
- **Exigir reconfirmação de N avaliações a cada passo, inclusive continuando na mesma direção**: rejeitado por ser desnecessariamente lento e não pedido pela spec (que só fala em evitar oscilação/mudança de direção, não em desacelerar a continuação).
- **Não ter estado de "direção em vigor" — decidir a cada avaliação isoladamente a partir só do valor atual vs. limites**: rejeitado — sem histerese de fato, um p95 oscilando em torno de um limite geraria zero estabilidade (violaria FR-003/US2-AC2 diretamente).

## 4. Observabilidade do ajuste aplicado (FR-007)

**Decision**: estender a resposta já existente de `GET /v1/sessions/{sessionId}/metrics` com um campo adicional por canal, `windowMs` (o valor atualmente aplicado, `null` quando o ajuste adaptativo está desabilitado ou o canal ainda não avaliou nenhuma vez). A fonte é o novo `AdaptiveWindowRegistry` (§1), consultado em paralelo ao `metrics.session_snapshot(session_id)` já usado por esse endpoint, casando por `channelId`. Complementar: log estruturado em `INFO` (mesmo logger já usado para conectar/desconectar canal) toda vez que a janela efetivamente muda, incluindo `sessionId`, `channelId`, valor anterior, valor novo e direção.

**Rationale**: `GET /v1/sessions/{sessionId}/metrics` não é um contrato versionado (ao contrário de `transcript-event.v2`) — é um endpoint de observabilidade documentado só em `docs/validation/sf-016-latency-metrics.md`, então adicionar um campo aditivo não quebra nenhum consumidor existente nem exige ADR (P4 só se aplica a contratos de evento). Reaproveitar o mesmo endpoint evita introduzir uma nova rota HTTP só para este propósito.

**Alternatives considered**:
- **Nova rota dedicada `GET /v1/sessions/{sessionId}/adaptive-window`**: rejeitado — duplicaria a busca por sessão/canal já feita pelo endpoint de métricas, para expor um dado que é naturalmente complementar à latência que o motivou.
- **Adicionar o campo ao próprio evento `transcript-event.v2`**: rejeitado explicitamente pela spec (FR-006) — o contrato de evento não pode ganhar nenhum campo novo relacionado a esta feature.

## 5. Validação da invariante mínimo-janela vs. overlap

**Decision**: validar em `AdaptiveWindowChannel.__init__` (levanta `ValueError` se `adaptive_window_min_seconds <= whisper_overlap_seconds`), no mesmo estilo que `StreamingTranscriber.__init__` já valida `overlap_seconds < window_seconds` hoje — falha cedo, na primeira conexão de canal, não em runtime dentro de `evaluate()`.

**Rationale**: mantém consistência com o padrão de validação já estabelecido no módulo (`transcriber.py`), em vez de introduzir um estilo novo (ex.: `pydantic` `model_validator` cruzando campos em `Settings`), que não tem precedente no `config.py` atual.

**Nota sobre `whisper_min_audio_seconds`**: o Edge Case da spec também cita `whisper_min_audio_seconds` como possível fonte de conflito com os novos limites de janela. Revendo `StreamingTranscriber` hoje: `_minimum_bytes` (derivado de `whisper_min_audio_seconds`) só é comparado dentro de `flush()`, para decidir se o restante do buffer no encerramento da conexão vale a pena transcrever — nunca é comparado contra `_window_bytes`/janela em nenhum outro ponto do código. Não existe, portanto, nenhum invariante real de "janela > `whisper_min_audio_seconds`" a proteger hoje, então nenhuma validação adicional é introduzida para essa relação; a única invariante que de fato precisa de guarda é a já implementada acima (`adaptive_window_min_seconds` vs. `whisper_overlap_seconds`).

## 6. Valores padrão dos parâmetros (FR-010)

Parâmetros novos em `Settings` (`app/config.py`), com padrões documentados e ancorados em números já observados/validados no projeto (`docs/validation/sf-015-conference-cam.md`, p95 real ≈ 450ms no setup GPU `small`/`float16`):

| Parâmetro | Padrão | Nota |
|---|---|---|
| `adaptive_window_enabled` | `False` | Opt-in (Clarifications Q4); comportamento idêntico ao atual quando desabilitado (SC-007). |
| `adaptive_window_min_seconds` | `1.6` | Metade do padrão atual (3.2s); estritamente > `whisper_overlap_seconds` (0.8s). |
| `adaptive_window_latency_high_ms` | `1600` | ≈ metade da duração da janela padrão em ms; sinaliza risco de backlog. |
| `adaptive_window_latency_low_ms` | `600` | Acima da baseline real observada (~450ms), com margem para não oscilar perto do valor saudável. |
| `adaptive_window_step_seconds` | `0.4` | 4 passos entre o piso (1.6s) e o teto/padrão (3.2s). |
| `adaptive_window_stable_evaluations` | `3` | Filtra um pico isolado sem atrasar demais a primeira reação. |
| `adaptive_window_min_samples` | `5` | Mesma ordem de grandeza usada para confiar em p95 na validação manual da SF-015. |

**Alternatives considered**: descoberta automática/adaptativa dos próprios limiares (ex.: baseada em desvio padrão histórico): rejeitada pela spec (Assumptions) — "não exigem descoberta automática nem aprendizado de máquina".
