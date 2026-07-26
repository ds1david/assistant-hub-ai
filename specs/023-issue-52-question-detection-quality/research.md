# Research: Qualidade de detecção de pergunta (issue #52)

Phase 0 — todas as decisões fechadas; zero `NEEDS CLARIFICATION` no Technical Context.

## R1 — Onde o operador vê a resposta

**Decision**: Resposta **somente** no desktop shell (painel Assistente). Dashboard STT = captura/transcript/sessionId/header.

**Rationale**: Spec 019 já define a superfície; confusão STT vs chat foi a falha principal de UX da sessão real. Issue #51 melhora alinhamento de id no STT, não chat.

**Alternatives considered**: Chat no `index.html` do STT — rejeitado (fora de escopo; mistura operação e assistência).

## R2 — Heurística lexical expandida vs classificador ML

**Decision**: Regras determinísticas (prefixos pt/en + vocativo + segmentos após `.!` + word boundary) na v1.

**Rationale**: Testável sem GPU (P10); cobre o gap real (*Me conte*, *David, me descreva*, *Em que…*). Word boundary evita `qualidade` → `qual`.

**Baseline**: parcialmente em `apps/desktop-shell/src/assistant-auto.ts` (2026-07-25); esta feature formaliza e alinha docs/019.

**Alternatives considered**: classificador neural de speech-act — rejeitado (peso, GPU, não determinístico na CI).

## R3 — Modo entrevista

**Decision**: Preferência por sessão `interviewMode` (default false). Quando on: todo Final **system** com length ≥ 8 é candidato, **além** do lexical.

**Rationale**: Mock de entrevista usa imperativos e turnos longos; lexical nunca será completo. Limitar a `system` evita auto-responder cada fala do candidato no mic.

**Alternatives considered**: aplicar a mic também — rejeitado nesta fatia (ruído de turns do candidato).

## R4 — Prosódia: onde extrair

**Decision**: Extrair no **transcription-service** no window que produz `transcript.final.v2`, sob `PROSODY_ENABLED` (default false).

**Rationale**: Final já é autoridade do STT; um único lugar anexa metadado; agent permanece focado em WASAPI/isolamento (P3/P6). Clarify + analyze 2026-07-25: spec US5/Problema alinhados — **agent não extrai F0**.

**NFR-002 (budget)**: Soft fixture timing in `services/transcription-service/tests/test_prosody.py` (`test_prosody_budget_rough_fixture_timing`) asserts average &lt; 500 ms per 1s @16kHz synthetic chirp on CI CPU (order of tens of ms expected on a developer machine). Product default remains `PROSODY_ENABLED=false`.

**Algoritmo v1**: F0 (preferir lib já no container; senão numpy + autocorrelação) nos últimos `PROSODY_END_WINDOW_MS` (default 500 ms); slope em semitons → `questionScore` monotônico; `contour` rising|falling|flat|unknown.

**Alternatives considered**: agent Windows no fim do utterance — só se STT não tiver PCM estável do segmento (não é o caso do window final).

## R5 — Schema transcript v2

**Decision**: Atualizar `contracts/transcript-event.v2.schema.json` **in-place** com propriedade opcional `prosody` (objeto com `questionScore` required-if-present, `contour` e `f0EndSlopeSemitones` opcionais).

**Rationale**: `additionalProperties: false` impede campos “escondidos”; declarar `prosody` é extensão aditiva para eventos antigos (sem o campo continuam válidos).

**Fallback**: publicar `transcript-event.v2.1.schema.json` + dual-accept **somente** se testes de contrato de consumidores legados exigirem freeze do arquivo v2.

## R6 — Modelo STT maior (Whisper medium / large-v3)

**Decision**: Não mudar default de produto (`small`); documentar upgrade opt-in + sample hotwords + checklist A/B.

**Rationale**: Latência/VRAM; operadores com GPU opt-in. Melhora WER ajuda lexical e LLM; **não** substitui prosódia nem corrige session mismatch.

## R7 — Score multimodal

**Decision**: OR lógico (FR-006), não média ponderada na v1.

**Rationale**: Simples, testável, thresholds independentes. Ponderação como evolução se houver falsos positivos do modo entrevista.

## R8 — UI de preferências

**Decision**: Toggles `interviewMode` e `useProsody` no painel. `prosodyThreshold` só no store (default 0.65), sem slider na v1.

**Rationale**: Clarify — densidade de UI; threshold testável via prefs/API; valor default documentado.

## R9 — Empty states

**Decision**: Manter mensagem genérica de elegibilidade (019); não ramificar copy por interview/prosody.

**Rationale**: Docs cobrem o “porquê”; UI limpa.

## R10 — O que não misturar

- Eco mic↔remoto: outro subsistema; large-v3 sozinho não resolve eco.
- Entonação em Meet/TTS remoto: score menos confiável → `useProsody` default off; modo entrevista existe como alternativa.

## Tabela de verdade (gate FR-006)

| Final | origin enabled | looksLikeQ | interviewMode & system & len≥8 | useProsody & score≥T | candidate? |
|-------|----------------|------------|--------------------------------|----------------------|------------|
| N | * | * | * | * | N |
| Y | N | * | * | * | N |
| Y | Y | Y | * | * | Y |
| Y | Y | N | Y | * | Y |
| Y | Y | N | N | Y | Y |
| Y | Y | N | N | N | N |
