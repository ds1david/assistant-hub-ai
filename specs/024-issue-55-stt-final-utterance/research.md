# Research: STT final-on-utterance (issue #55)

**Date**: 2026-07-25  
**Feature**: `specs/024-issue-55-stt-final-utterance`

## R1 — Where does finalization live?

**Decision**: State machine no **transcription-service**, **por conexão WebSocket de canal**.

**Rationale**: É o único lugar que hoje decide `final` vs `partial` (`main.py` `emit`). Session-core só reencaminha; shell só consome Final; agent não tem VAD de utterance exportado.

**Alternatives considered**:
- Agent envia “end-of-speech” → acopla WASAPI/Windows e quebra testes sem hardware.
- Shell infere final a partir de partials → viola 019 (só Final) e inventa política no cliente.
- Whisper segment timestamps only → ainda processamos por janela fixa; segments não fecham utterance de produto sozinhos.

## R2 — Close signal

**Decision**: Após utterance **open** (≥1 texto útil), fechar quando contador de **janelas sem texto novo** ≥ `finalization_idle_windows` (default **1**).

**Rationale**: `StreamingTranscriber.transcribe_pcm` já retorna `None` para vazio ou texto idêntico ao último — silêncio e estabilidade colapsam no mesmo sinal. Contar janelas evita PCM energy/VAD extra e é determinístico em testes com fake engine.

**Alternatives considered**:
- PCM RMS threshold → hardware-dependent, flaky, fora de P10 sem fixtures complexas.
- Só estabilidade de texto entre partials publicados → nunca fecha se silêncio não publica partial (loop infinito awaiting_final).
- Só timeout → finais atrasados demais em diálogos normais.

## R3 — Final text

**Decision**: **Último texto útil** da utterance (último partial aceito / último texto que abriu/atualizou a utterance).

**Rationale**: Simples, alinhado ao partial que o usuário já viu; consolidator (SF-017) continua separado para snapshot de canal. Live-answer usa o campo `text` do Final.

**Alternatives considered**:
- Concatenar todos os partials → risco de duplicar overlap (já resolvido no consolidator, não no evento).
- Snapshot do consolidator no close → acopla finalization a consolidação; mais estado cruzado.

## R4 — Max open timeout

**Decision**: `finalization_max_open_seconds = 45` (default); se open e `(now - opened_at) >= max`, emitir final e resetar.

**Rationale**: Rede de segurança para monólogo/stream contínuo sem idle; 45s equilibra “não spam” vs “não travar Assistente para sempre”.

**Alternatives considered**: 15s (corta frases longas cedo demais); 120s (mau para live-answer).

## R5 — Schema

**Decision**: **Zero** mudança em `transcript-event.v2.schema.json`.

**Rationale**: Tipo e campos já suportam final; consumers existem. Preferência da spec (FR-013).

**Alternatives considered**: Campo `utteranceId` aditivo — útil no futuro para idempotência multi-consumidor; **não** necessário para aceite #55 (shell já dedupe por identidade de trecho).

## R6 — Disconnect vs policy

**Decision**: No disconnect, se residual tem texto e utterance **ainda open**, emitir um final (como hoje). Se utterance **já finalizada** e residual não traz texto **novo**, **não** reemitir. Flag `final_emitted` / estado `idle` após final.

**Rationale**: FR-010 / edge case double-final.

## R7 — Observe every window evaluation

**Decision**: Finalizer recebe eventos em **toda** janela processada: `on_text` (após suppress pass e texto não vazio) ou `on_no_result` (None, empty, ou texto igual).

**Rationale**: Hoje `emit` early-return quando `result is None` — sem observação, idle nunca incrementa. Wire em `main.py` worker **antes** de return silencioso.

## R8 — Echo suppression interaction

**Decision**: Texto de microfone **suprimido** NÃO chama `on_text`. **Não** incrementa idle por suppress sozinho (suppress ocorre após sleep; não equivale a silêncio de fala). Próximas janelas sem texto novo (engine None) avançam idle normalmente.

**Rationale**: Evitar abrir utterance com eco; evitar fechar legítimo por timing de suppress.

## R9 — Adaptive window

**Decision**: Idle em **contagem de janelas**, não segundos fixos de silêncio.

**Rationale**: Com adaptive window, duração real de “1 janela” muda; SC-007 é “~1 janela”, não “exatos 3.2s”.

## R10 — session-core / shell code

**Decision**: **Sem** mudanças de código em session-core ou desktop-shell para MVP, se contrato e feed já aceitam final (confirmado por testes existentes e 019/023).

**Rationale**: Gap é emissão STT. US2 valida path ponta a ponta via quickstart/fixture; se bug de ingest for encontrado, task de fix isolada.

## Open items deferred (non-blocking)

- `utteranceId` no schema (follow-up).
- Idle em segundos de wall-clock independente da janela.
- Expor settings no `/health` (nice-to-have polish).
