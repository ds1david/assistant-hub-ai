# Implementation Plan: Qualidade de detecção de pergunta (issue #52)

**Branch**: `feature/issue-52-live-answer-qualidade-de-detec-o-de-pergunta-ent`  
**Issue**: [#52](https://github.com/ds1david/assistant-hub-ai/issues/52)  
**Spec**: `specs/023-issue-52-question-detection-quality/spec.md`  
**Date**: 2026-07-25  
**Updated**: 2026-07-25 (analyze remediation)  
**Input**: Feature specification from `/specs/023-issue-52-question-detection-quality/spec.md`

## Summary

Fazer o Assistente (desktop shell) disparar de forma confiável em **simulação de entrevista**: imperativos/vocativos (lexical expandido), **modo entrevista** (todo Final system ≥ 8), docs inequívocos de **onde** a resposta aparece, ops de qualidade de STT (modelo/hotwords opt-in), e **prosódia opcional** no Final (STT) com gate multimodal OR — sem chat no dashboard STT e sem mudar defaults de privacidade (`autoEnabled=false`, modelo STT default `small`).

## Technical Context

**Language/Version**: TypeScript (desktop-shell / Vitest); Python 3.11+ (transcription-service / pytest); Rust (Tauri prefs commands se tipagem explícita)

**Primary Dependencies**: Tauri shell existente; session-core live-answer (019); Faster-Whisper / STT service; schema JSON draft 2020-12

**Storage**: Preferências Assistente por `sessionId` (store Tauri/JSON já 019); sem DB novo

**Testing**: Vitest (shell, sem GPU); pytest (STT extrator com fixture sintética); testes de schema JSON; quickstart manual E2E

**Target Platform**: WSL (dev/test serviços); Windows (agent capture, inalterado para Phase A/B); desktop shell multiplataforma Tauri

**Project Type**: monorepo feature slice — shell UX + STT metadata + contratos versionados

**Performance Goals**: lexical/gate < 1 ms por final (CPU trivial); prosódia budget documentado ~dezenas de ms por final curto ou flag off (NFR-002)

**Constraints**: P9 sem PCM/tokens em log; P10 CI sem GPU/WASAPI; `additionalProperties: false` no schema v2 → campo `prosody` declarado; Phase A mergeável sem C

**Scale/Scope**: 1 operador local; 2 canais típicos (mic + system); 6 user stories; 3 fases de entrega (A/B/C)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Notas |
|-----------|--------|-------|
| P1 Spec antes de domínio | Pass | Spec + plan + tasks nesta pasta |
| P2 Core independente de fornecedor | Pass | Rota live-answer já abstrata; detecção no shell; STT só metadado |
| P3 WSL-first / Windows só captura | Pass | Prosódia no STT (Linux/container), não no agent WASAPI |
| P4 Contratos versionados | Pass | Extensão aditiva opcional `prosody` no schema v2; contract tests planejados. **Sem ADR**: mudança não é estrutural (campo opcional; eventos legados seguem válidos). Ver research R5. |
| P5 Canal/origem ponta a ponta | Pass | Gate usa `sourceType` canônico; interviewMode só system |
| P6 Isolamento endpoint | Pass | Não altera workers; prosódia por channel window no STT |
| P7 endpointId | N/A | Fora de escopo |
| P8 Automação com autorização | Pass | Sem merge/force-push automatizado |
| P9 Privacidade | Pass | FR-010; scores só; auto default off |
| P10 Testes determinísticos | Pass | Vitest + pytest fixture; E2E manual em quickstart |

**Post-design re-check**: Pass — design não introduz monólito, não move captura para WSL, não loga áudio, Phase C desligável.

## Project Structure

### Documentation (this feature)

```text
specs/023-issue-52-question-detection-quality/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── question-detection.md
├── checklists/
│   ├── requirements.md
│   └── question-detection.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
apps/desktop-shell/
├── src/
│   ├── assistant-auto.ts      # looksLikeQuestion, isQuestionCandidate, extract
│   ├── assistant-prefs.ts     # prefs + normalize + interview/prosody fields
│   ├── assistant-panel.ts     # toggles UI
│   └── api-client.ts          # tipos de feed / prosody opcional
├── src-tauri/                 # get/set_assistant_prefs se tipado
└── tests/
    ├── assistant-auto.test.ts
    ├── assistant-prefs.test.ts
    └── assistant-panel.test.ts

services/transcription-service/
├── app/
│   ├── config.py              # PROSODY_*, WHISPER_MODEL
│   ├── main.py                # /health model + prosodyEnabled
│   ├── transcriber.py         # window final
│   └── prosody.py             # NEW: F0 → questionScore (Phase C)
└── tests/
    └── test_prosody.py        # fixture sintética

contracts/
└── transcript-event.v2.schema.json   # + prosody opcional (Phase C)

config/
└── whisper-hotwords.txt              # sample entrevista

docs/development/running.md           # onde ver resposta; ops modelo
docs/release/min-flow.md              # link se couber
```

**Structure Decision**: Estender o shell e o STT existentes; nenhum serviço novo. Phase A/B só shell+docs+config; Phase C toca STT + schema + shell types.

## Complexity Tracking

> Nenhuma violação constitucional a justificar.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Current state (verified 2026-07-25)

| Item | Estado |
|------|--------|
| Painel Assistente + live-answer | Existe (019) |
| `looksLikeQuestion` expandido (Me conte / vocativo / word boundary) | Código + testes em `assistant-auto.ts` |
| Spec **019 FR-004** (lexical legado) | Ainda descreve lista curta — precisa nota superseded (≠ **FR-004** desta feature = interview mode) |
| `interviewMode` / `useProsody` / `prosodyThreshold` | **Não** em prefs |
| `isQuestionCandidate` unificado | **Não** (só looksLikeQuestion) |
| `prosody` no evento / schema | **Não**; v2 `additionalProperties: false` |
| WHISPER_MODEL / hotwords / health.model | Existem (`/health` já expõe `model`); hotwords sample genérico |
| Docs “resposta ≠ STT” | Parcial — reforçar |

## Delivery phases ↔ tasks.md

| Entrega | Stories / task phases | Conteúdo |
|---------|----------------------|----------|
| **Phase A** (MVP ship) | tasks Phase 1–6 ≈ Setup + Foundational + US1 + US2 + US3 + US6 | FR-002 lexical; FR-004 interview; FR-006 gate; docs SC-005; regressão FR-012 |
| **Phase B** | tasks Phase 7 ≈ US4 | Hotwords; docs A/B modelo STT; health model |
| **Phase C** | tasks Phase 8 ≈ US5 | Schema `prosody`; extrator STT; useProsody UI; pytest; NFR-002 note |

> Não confundir **Phase A/B/C** (entrega) com **Phase 1–9** (numeração de tasks).

### Phase A — Lexical + modo entrevista + gate + docs (P1/P2) — **ship first / MVP**

Formalizar FR-002; prefs `interviewMode`; `isQuestionCandidate` (sem depender de prosódia real); UI toggle entrevista; docs SC-005; testes; regressão session-alignment (FR-012).

### Phase B — STT ops quality (P2)

Hotwords entrevista; docs A/B medium/large-v3; health model documentado; quickstart B.

### Phase C — Prosódia (P3)

Schema `prosody`; extrator **STT only** (não agent); prefs `useProsody` + threshold store; UI toggle useProsody; gate ramo prosody; pytest fixture; budget note (NFR-002).

## Risks

| Risco | Tripwire | Plan B |
|-------|----------|--------|
| Modo entrevista spam de invokes | muitos turns/min em system | min length; debounce futuro; desligar modo |
| Prosódia deps pesadas no container | imagem/build pesa | pure-python mínimo; flag off; adiar C |
| Schema break consumidores | validação falha | campo opcional; dual-accept v2.1 só se necessário |
| medium OOM GPU | restart loop | rollback small documentado |

## Open questions

*(fechadas no clarify 2026-07-25; confirmadas no analyze remediation)*

- Prosódia: **STT** (não agent). Schema: **v2 in-place** (sem ADR). Threshold UI: **não na v1**. Empty state: **genérico**. Ship: **A sozinha**.
- FR IDs: **019 FR-004** = lexical legado; **FR-002** = lexical expandido; **FR-004** (023) = modo entrevista.

## Analyze remediation (2026-07-25)

Aplicado: I1/I2/X1/A1/U1/U2 no spec; C1/C2/O1/D1/T2 no tasks; P4 nota no plan. Ver relatório `/speckit-analyze` na sessão.
