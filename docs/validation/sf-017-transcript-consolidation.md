# Validação SF-017 — texto consolidado sem duplicações de overlap

Evidência automatizada da consolidação de texto por sessão e canal sem GPU, Docker, WASAPI ou download de modelo. O evento `transcript-event.v2` não mudou: os eventos parciais continuam brutos e a consolidação é um read-model separado, lido por um endpoint novo.

## Problema

Cada janela do Whisper reprocessa os últimos `WHISPER_OVERLAP_SECONDS` (0.8 s) da janela anterior, então as palavras faladas na borda aparecem no fim do texto de uma janela e de novo no início da seguinte. O flush de desconexão re-transcreve a cauda de overlap. A única defesa anterior era descartar janelas com texto integralmente idêntico ao anterior.

## Algoritmo

Determinístico e conservador, sem fuzzy, sem LLM, apenas stdlib:

- normaliza somente para comparação: minúsculas e separação por espaços; o texto original é preservado para exibição;
- procura a maior sequência de palavras no fim do texto consolidado do canal igual ao início do texto novo e anexa apenas a parte não repetida;
- texto novo integralmente contido no fim do canal (duplicata completa, típico do flush final) é ignorado;
- sem casamento na borda (janela perdida por descarte de fila), o texto novo é anexado inteiro — na dúvida, preservar em vez de apagar;
- acentos e pontuação contam na comparação: "dez." ≠ "dez" não corta;
- canais nunca são comparados entre si; a chave de estado é `(sessionId, channelId)`.

## Arquitetura

- `app/consolidation.py` define `TranscriptConsolidationRegistry` (mutável, protegido por lock de thread) e os snapshots imutáveis `ChannelTranscriptSnapshot` e `SessionTranscriptSnapshot`;
- segmentos por `(sessionId, channelId)` em `deque(maxlen=TRANSCRIPT_MAX_SEGMENTS_PER_CHANNEL)`; canais limitados por `TRANSCRIPT_MAX_CHANNELS` com evicção do menos recentemente tocado; a cauda de comparação guarda as últimas `TRANSCRIPT_OVERLAP_TAIL_WORDS` palavras normalizadas;
- a ingestão acontece no mesmo ponto único de `app/main.py` usado pelas métricas da SF-016, após a entrega do evento — eco suprimido e o fan-out do feed não entram no consolidado;
- `create_app(..., consolidator=None)` injeta o consolidador; sem argumento, cada app cria a própria instância (nenhum estado global);
- `GET /v1/sessions/{sessionId}/transcript` responde `sessionId`, `generatedAt`, `maxSegmentsPerChannel` e `channels[]` com `text`, `segmentCount`, `totalEvents`, `duplicateWordsRemoved`, `droppedSegments`, `truncated`, `firstEventAt` e `lastEventAt`; sessão desconhecida responde 200 com `channels: []`;
- reinício do serviço zera o estado — persistência em banco continua fora de escopo.

## Onde

- Consolidador: `services/transcription-service/app/consolidation.py`
- Testes de unidade: `services/transcription-service/tests/test_transcript_consolidation.py`
- Testes HTTP: `services/transcription-service/tests/test_transcript_endpoint.py`
- Configuração: `TRANSCRIPT_MAX_SEGMENTS_PER_CHANNEL`, `TRANSCRIPT_MAX_CHANNELS` e `TRANSCRIPT_OVERLAP_TAIL_WORDS` em `.env.example` e `infra/compose/docker-compose.yml`

## O que é coberto

- overlap de borda anexa só a parte não repetida ("vamos revisar a arquitetura do serviço" + "arquitetura do serviço antes da implementação");
- casos literais da issue #6: "olá mundo" duplicado é ignorado; "vamos revisar a arquitetura" + "a arquitetura antes da implementação" consolida sem repetição; "o serviço iniciou" + "o serviço encerrou" preserva os dois textos (prefixo compartilhado fora da borda não é overlap);
- duplicata completa e sufixo do flush final são ignorados;
- janela sem casamento (descartada na fila) é anexada inteira, sem falso corte;
- repetição legítima no meio da fala é preservada;
- comparação insensível a maiúsculas, mantendo o texto original; acentos e pontuação não são normalizados (conservador por decisão);
- cauda de comparação limitada por configuração;
- rotação de segmentos com `droppedSegments`/`truncated`; `totalEvents` sobrevive à rotação;
- isolamento entre sessões e entre canais, em unidade e via HTTP; canais nunca se comparam;
- evicção do canal menos recentemente tocado ao exceder `TRANSCRIPT_MAX_CHANNELS`;
- ingestões concorrentes de múltiplas threads sem perda;
- eventos v2 permanecem brutos e válidos contra o schema; eco suprimido não entra no consolidado; métricas da SF-016 inalteradas;
- o engine fake nunca carrega modelo (sem GPU).

## Como executar

```bash
PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests
```
