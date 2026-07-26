# Research: Qualidade de detecção de pergunta

## R1 — Onde o operador vê a resposta

**Decision**: Manter resposta **somente** no desktop shell (painel Assistente). Dashboard STT = operação de captura/transcript/sessionId.

**Rationale**: 019 já define a superfície; confundir STT com chat foi a falha principal de UX da sessão. Issue 51 melhora alinhamento de id no STT, não chat.

## R2 — Heurística lexical expandida vs classificador ML

**Decision**: Expandir regras determinísticas (prefixos + vocativo + sentença) na v1; ML de intent fica fora.

**Rationale**: Testável sem GPU; alinhado P10; cobre o gap real (*Me conte*, *Descreva*). Word boundary evita `qualidade` → `qual`.

**Baseline código**: já parcialmente em `assistant-auto.ts` (2026-07-25); esta feature formaliza e alinha docs/019.

## R3 — Modo entrevista

**Decision**: Preferência por sessão `interviewMode`; quando on, todo Final **system** ≥8 chars é candidato.

**Rationale**: Mock de entrevista usa imperativos e turnos longos; lexical nunca será completo. Limitar a system evita auto-responder a cada fala do candidato no mic.

## R4 — Prosódia: onde extrair

**Decision (default)**: Extrair no **transcription-service** no window que produz `transcript.final.v2`, sob `PROSODY_ENABLED` (default false).

**Alternativa**: agent Windows no fim do utterance — só se o STT não tiver PCM do segmento final de forma estável.

**Rationale**: Final já é autoridade do STT; um único lugar anexa metadado; agent permanece focado em WASAPI/isolamento.

**Algoritmo v1**: F0 (pyin/crepe-lite/parselmouth se deps OK; senão librosa.pyin ou heurística energy-only degradada) nos últimos 300–800 ms; slope em semitons → `questionScore` via mapeamento monotônico documentado; `contour` rising/falling/flat.

**Deps**: Preferir biblioteca já aceitável no container GPU; se peso excessivo, implementaçao mínima numpy + autocrrelação e documentar limite.

## R5 — Schema transcript v2

**Decision**: Revisar `transcript-event.v2.schema.json` de forma aditiva:

- permitir `prosody` opcional; **ou**
- se política do repo exigir freeze estrito de v2, publicar `transcript-event.v2.1.schema.json` e dual-accept no STT.

`additionalProperties: false` hoje força mudança de schema explícita — não usar campos “escondidos”.

## R6 — Whisper medium

**Decision**: Não mudar default de produto (`small`); documentar upgrade e sample hotwords.

**Rationale**: Latência/VRAM; operadores com GPU opt-in. Melhora WER ajuda lexical e LLM, não prosódia.

## R7 — Score multimodal

**Decision**: OR lógico (FR-006), não média ponderada na v1.

**Rationale**: Simples, testável, thresholds independentes. Ponderação fica como evolução se houver falsos positivos do modo entrevista.

## R8 — O que não misturar

- Eco mic↔remoto: outro subsistema; transcript ruim por eco não se “corrige” com large-v3 sozinho.
- Entonação em áudio de Meet/TTS: score menos confiável; por isso `useProsody` default off e modo entrevista existe.

## Tabela de verdade (gate)

| Final | origin enabled | looksLikeQ | interviewMode & system | useProsody & score≥T | candidate? |
|-------|----------------|------------|------------------------|----------------------|------------|
| N | * | * | * | * | N |
| Y | N | * | * | * | N |
| Y | Y | Y | * | * | Y |
| Y | Y | N | Y | * | Y |
| Y | Y | N | N | Y | Y |
| Y | Y | N | N | N | N |
