# Implementation Plan: Qualidade de detecção de pergunta

**Branch**: `feature/023-question-detection-quality`  
**Issue**: [#52](https://github.com/ds1david/assistant-hub-ai/issues/52)  
**Spec**: `specs/023-question-detection-quality/spec.md`  
**Date**: 2026-07-25

## Goal

Fazer o Assistente disparar de forma confiável em **simulação de entrevista** (imperativos, vocativo, áudio remoto), documentar **onde** a resposta aparece, melhorar **input STT** (modelo/hotwords), e preparar **prosódia opcional** + gate multimodal — sem colocar chat no dashboard STT.

## Not doing

- Resposta do LLM no `index.html` do STT
- AEC completo / redesenho de eco
- Default `autoEnabled=true`
- Modelo Whisper default ≠ `small`
- Classificador neural de speech-act
- Diarização multi-speaker

## Current state (verified)

| Item | Estado |
|------|--------|
| Painel Assistente + live-answer | Existe (019) |
| FR-004 original (prefixos curtos) | Superseded em código por expansão 2026-07-25; **spec 019 ainda antiga** |
| `looksLikeQuestion` expandido | `apps/desktop-shell/src/assistant-auto.ts` + testes |
| interviewMode / useProsody | **Não** existem |
| prosody no evento | **Não**; schema v2 `additionalProperties: false` |
| WHISPER_MODEL env | Existe; default small |
| Docs “resposta ≠ STT” | Parcial em running.md; reforçar |

## Phases

### Phase A — Lexical + docs + prefs modo entrevista (P1/P2) — ship first

Alinhar contrato/docs à heurística já no código; adicionar `interviewMode`; UI toggle; testes; quickstart operador.

### Phase B — STT ops quality (P2)

Hotwords sample entrevista; docs A/B medium; health mostra model (se faltar).

### Phase C — Prosódia + schema + gate (P3)

Schema aditivo; extrator no STT sob flag; prefs `useProsody`/`prosodyThreshold`; feed tipado no shell; testes fixture.

## Steps (execução)

### Step 1: Formalizar FR-002 no shell e testes de regressão
Files: `assistant-auto.ts`, `assistant-auto.test.ts`, referência cruzada em `specs/019-…` (nota superseded)  
Do: garantir export estável; tabela de frases da sessão real; word boundary  
Done when: `npm test -- --run tests/assistant-auto.test.ts` verde; frases *Me conte* / *David, me descreva* / *Em que sistema* true  
Status: largely done (verify + gap tests)

### Step 2: Prefs + UI `interviewMode`
Files: `assistant-prefs.ts`, Rust prefs se houver, `assistant-panel.ts`, `assistant-auto.ts`, testes  
Do: defaults false; normalização; toggle “modo entrevista (todo final system)”  
Done when: vitest prefs + extractNewQuestions com interviewMode  
Status: pending

### Step 3: Gate unificado `isQuestionCandidate`
Files: `assistant-auto.ts`, testes  
Do: FR-006; `shouldAutoAnswerFromEntry` usa o gate  
Done when: tabela de verdade do research coberta  
Status: pending

### Step 4: Docs operador (SC-005)
Files: `docs/development/running.md`, `docs/release/min-flow.md` (link), quickstart desta feature  
Do: seção “Onde ver resposta do ChatGPT”; checklist automático/origem/sessionId; A/B whisper  
Done when: greppável e no quickstart  
Status: pending

### Step 5: Hotwords + ops Whisper
Files: `config/whisper-hotwords.txt` ou sample + docs; `.env.example` comentário medium  
Do: termos entrevista; não mudar default model  
Done when: doc + sample commitáveis  
Status: pending

### Step 6: Schema prosody
Files: `contracts/transcript-event.v2.schema.json` (ou v2.1), testes de schema se existirem  
Do: objeto opcional `prosody`  
Done when: evento sem prosody valida; com prosody valida  
Status: pending

### Step 7: Extrator prosody no STT
Files: `services/transcription-service/app/*`, settings, tests com wav fixture sintético  
Do: `PROSODY_ENABLED`; anexar só em final; falha → omitir  
Done when: pytest unitário score shape; final sem flag idêntico ao baseline  
Status: pending

### Step 8: Shell consome prosody
Files: `api-client.ts` feed types, `assistant-auto.ts`, prefs UI useProsody  
Do: FR-006 ramo prosody  
Done when: teste com entry.prosody.questionScore ≥ T dispara  
Status: pending

### Step 9: Quickstart manual E2E
Files: `quickstart.md`  
Do: fluxo conference-cam + auto on + system + 1 pergunta + ver Assistente; opcional medium  
Done when: checklist assinalável  
Status: pending

## Risks

| Risco | Tripwire | Plan B |
|-------|----------|--------|
| Modo entrevista gera spam de invokes | muitos turns/min em system | min length maior; debounce; só lexical |
| Prosódia deps pesadas no container | build/image explode | flag off; extrator pure-python mínimo; adiar Phase C |
| Schema v2 break | consumers fail validation | v2.1 dual-read |
| medium OOM GPU | container restart loop | documentar fallback small |

## Open questions

*(fechadas com defaults da spec)*

- Onde prosódia: **STT** (R4).  
- Default auto: **continua off**.  
- interviewMode em mic: **não** nesta fatia.
