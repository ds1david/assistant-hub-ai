# Validação SF-016 — métricas de latência p50/p95 por canal

Evidência automatizada das métricas de latência por sessão e canal sem GPU, Docker, WASAPI ou download de modelo. O evento `transcript-event.v2` não mudou.

## Arquitetura

- `app/metrics.py` define `LatencyMetricsRegistry` (mutável, protegido por lock de thread) e os snapshots imutáveis `ChannelLatencySnapshot` e `SessionMetricsSnapshot`;
- amostras por `(sessionId, channelId)` em ring buffer `deque(maxlen=METRICS_MAX_SAMPLES_PER_CHANNEL)`; canais limitados por `METRICS_MAX_CHANNELS` com evicção do menos recentemente tocado;
- p50/p95 por nearest-rank, calculados apenas na leitura do snapshot; escrita é O(1);
- o registro acontece em um único ponto de `app/main.py`, após a entrega do evento (`send_json` + `broadcaster.publish`) — transcrições suprimidas pelo eco e o fan-out por cliente do feed não contam;
- `create_app(settings=None, engine=None, metrics_registry=None)` injeta o registry; sem argumento, cada app cria a própria instância (nenhum estado global);
- `GET /v1/sessions/{sessionId}/metrics` responde `sessionId`, `generatedAt`, `maxSamplesPerChannel` e `channels[]` com `sampleCount`, `p50Ms`, `p95Ms`, `minMs`, `maxMs`, `avgMs`, `totalEvents`, `droppedWindows` e `lastEventAt`; sessão desconhecida responde 200 com `channels: []`.

## Onde

- Registry: `services/transcription-service/app/metrics.py`
- Testes de unidade: `services/transcription-service/tests/test_latency_metrics.py`
- Testes HTTP: `services/transcription-service/tests/test_session_metrics_endpoint.py`
- Dashboard: `services/transcription-service/app/static/index.html` (p50/p95/amostras por painel, polling de 5 s)
- Configuração: `METRICS_MAX_SAMPLES_PER_CHANNEL` e `METRICS_MAX_CHANNELS` em `.env.example` e `infra/compose/docker-compose.yml`

## O que é coberto

- percentis nearest-rank para distribuição uniforme, amostra única e contagem par pequena;
- retenção: só as N amostras mais recentes influenciam os percentis; `totalEvents` sobrevive à rotação;
- isolamento entre sessões e entre canais, em unidade e via HTTP;
- janelas descartadas contam sem criar amostra de latência;
- evicção do canal menos recentemente tocado ao exceder `METRICS_MAX_CHANNELS`;
- gravações concorrentes de múltiplas threads sem perda;
- exatamente uma amostra por evento entregue: assinantes do feed não duplicam contagens e eco suprimido não conta;
- registry injetado nos testes recebe os registros do app.

## Como executar

```bash
PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests
```
