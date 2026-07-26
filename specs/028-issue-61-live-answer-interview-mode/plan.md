# Implementation Plan: Live-answer — modo entrevista (contexto mic+system, 1ª pessoa, latência)

**Branch**: `feature/issue-61-live-answer-modo-entrevista-contexto-mic-system`  
**Issue**: [#61](https://github.com/ds1david/assistant-hub-ai/issues/61)  
**Spec**: `specs/028-issue-61-live-answer-interview-mode/spec.md`  
**Date**: 2026-07-26  
**Input**: Feature specification from `/specs/028-issue-61-live-answer-interview-mode/spec.md`

## Summary

Refinar o Assistente live-answer para **treino de entrevista**: (1) builder de input com contexto misto **system + microphone** e rótulos de papel, controlado por preferência por sessão `includeMicrophoneInContext` (default ON); (2) com `interviewMode` ligado, prefixar o invoke com bloco de instrução **1ª pessoa / fala oral**; (3) docs de disparo ≠ contexto e knobs de latência. **Sem** novo schema de transcript, **sem** disparar em partial, **sem** TTS. Shell TypeScript + prefs Tauri; STT só documentação/ops.

## Technical Context

**Language/Version**: TypeScript (desktop-shell / Vitest); Rust (Tauri prefs serde); Markdown docs

**Primary Dependencies**: shell Assistente 019/023 (`assistant-auto`, `assistant-prefs`, `assistant-panel`); hub invoke rota `live-answer` / capability `chat`; session feed com `sourceType`

**Storage**: Preferências Assistente por `sessionId` (JSON local Tauri `assistant-prefs.json`) — campo aditivo; buffer de finais **em memória** no controller (já existe; estender com `sourceType`)

**Testing**: Vitest no shell (builder, prefs, estilo, não-disparo mic/partial); cargo test prefs se tipagem Rust; sem GPU/WASAPI

**Target Platform**: Desktop shell Tauri (WSL dev + Windows run); STT/session-core inalterados em código de domínio

**Project Type**: monorepo feature slice — shell UX + prefs + docs

**Performance Goals**: montagem de input O(n) na janela (≤12 trechos / ≤4000 chars, 019); instrução fixa ~poucos KB; sem latência extra de rede além do invoke já existente

**Constraints**: P5 `sourceType` canônico; P9 sem dump de saída do modelo em logs; P10 CI sem GPU; FR-008 disparo ≠ contexto; FR-012b sem reject runtime de estilo; zero schema transcript

**Scale/Scope**: 1 operador local; 2 canais (mic + system); 4 user stories; 1 app tocado (shell) + docs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Notas |
|-----------|--------|-------|
| P1 Spec antes de domínio | Pass | Spec clarified + plan + tasks nesta pasta |
| P2 Core independente de fornecedor | Pass | Rota `live-answer` abstrata; instrução no shell input, não SDK de LLM |
| P3 WSL-first / Windows só captura | Pass | Código no shell; captura/STT intocados (só docs ops) |
| P4 Contratos versionados | Pass | Sem mudança de transcript v2; prefs JSON aditivas com default |
| P5 Canal/origem ponta a ponta | Pass | Buffer e labels usam `sourceType` canônico |
| P6 Isolamento endpoint | N/A | Não toca workers de áudio |
| P7 endpointId | N/A | Fora de escopo |
| P8 Automação com autorização | Pass | Sem merge/force-push |
| P9 Privacidade | Pass | FR-020; texto de resposta só na UI local |
| P10 Testes determinísticos | Pass | Vitest fixtures; sem LLM real |

**Post-design re-check**: Pass — nenhum serviço novo, schema v2 estável, captura intocada, style detector só em testes.

## Project Structure

### Documentation (this feature)

```text
specs/028-issue-61-live-answer-interview-mode/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── interview-live-answer.md
├── checklists/
│   ├── requirements.md
│   └── interview-mode.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/desktop-shell/
├── src/
│   ├── assistant-auto.ts       # recentFinals+sourceType; buildInvokeInput; interview instruction; style detector
│   ├── assistant-prefs.ts      # includeMicrophoneInContext + normalize/default true
│   ├── assistant-panel.ts      # toggle “Incluir minha voz no contexto”; latency already per-turn
│   ├── main.ts                 # wire toggle → prefs save
│   └── session-alignment.ts    # se clonar prefs shape
├── src-tauri/src/
│   └── assistant_prefs.rs      # field + default true + serde
└── tests/
    ├── assistant-auto.test.ts  # mixed context, labels, instruction, style detector, no mic trigger
    ├── assistant-prefs.test.ts # default ON / isolation
    └── assistant-panel.test.ts # checkbox wire

docs/development/running.md     # disparo vs contexto; estilo 1ª pessoa; elos de latência / knobs entrevista
docs/release/min-flow.md        # one-line cross-link se couber
```

**Structure Decision**: Toda lógica de produto fica no **desktop-shell**. Não alterar transcription-service nem session-core. Não alterar contrato transcript v2.

## Complexity Tracking

> Nenhuma violação constitucional a justificar.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Current state (verified 2026-07-26)

| Item | Estado |
|------|--------|
| Live-answer ponta a ponta + Final utterance | OK (019/024) |
| `buildInvokeInput` + `recentFinals` | Existe; **sem** `sourceType` no buffer; **sem** rótulos; inclui todos os finais textuais |
| `enabledSourceTypes` (disparo) | OK; default system |
| `interviewMode` | OK para detecção (023); **não** altera prompt |
| `includeMicrophoneInContext` | **Não existe** |
| `latencyMs` por turn no painel | **Já existe** |
| Docs disparo vs contexto / estilo 1ª pessoa | **Parcial / ausente** |

## Design decisions (see research.md)

| ID | Decision |
|----|----------|
| R1 | Estender `recentFinals` com `sourceType` canônico; filtrar no builder |
| R2 | Labels fixos `Entrevistador:` / `Candidato (eu):` |
| R3 | Prefs `includeMicrophoneInContext` default **true** (missing → true) |
| R4 | Estilo via **prefixo de instrução** no input se `interviewMode` |
| R5 | Detector de estilo **só testes** (sem reject runtime) |
| R6 | Latência: preservar UI existente + docs de elos/knobs |
| R7 | Zero schema transcript; zero mudança STT código |

## Delivery map

| Entrega | Stories | Conteúdo |
|---------|---------|----------|
| **A — MVP** | US1 + prefs base + US3 toggle | Contexto misto + preferência + testes |
| **B — Estilo** | US2 | Instrução entrevista + detector + testes |
| **C — Docs/latência** | US4 | running.md, quickstart, knobs; regressão partial |

> Tasks phases 1–N mapeiam Setup → Foundational → US1–US4 → Polish.
