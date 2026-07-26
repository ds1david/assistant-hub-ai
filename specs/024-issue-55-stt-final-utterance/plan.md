# Implementation Plan: STT — `transcript.final.v2` ao fim de utterance (issue #55)

**Branch**: `feature/issue-55-stt-emitir-transcript-final-v2-ao-fim-de-utteran`  
**Issue**: [#55](https://github.com/ds1david/assistant-hub-ai/issues/55)  
**Spec**: `specs/024-issue-55-stt-final-utterance/spec.md`  
**Date**: 2026-07-25  
**Input**: Feature specification from `/specs/024-issue-55-stt-final-utterance/spec.md`

## Summary

O serviço de transcrição hoje marca `final=True` **somente** no flush residual do **disconnect** do WebSocket de áudio; durante a conversa só saem `transcript.partial.v2`. O Assistente live-answer (019 FR-003) só reage a **Final** → permanece em `awaiting_final`.

Esta feature adiciona uma **state machine de utterance por canal** no STT: após ≥1 texto útil (partial), a **primeira** janela avaliada sem texto novo (idle) emite **um** `transcript.final.v2` com o último texto útil; timeout de 45s força fechamento; disconnect continua finalizando residual **sem duplicar**. Zero mudança de schema v2. Testes determinísticos com fake engine (sem GPU). Docs de running/live-answer atualizados.

## Technical Context

**Language/Version**: Python 3.11+ (transcription-service); docs Markdown; shell/session-core **sem** mudança de código de domínio (já consomem `transcript.final.v2`)

**Primary Dependencies**: FastAPI / Starlette WS (STT); pydantic-settings; pytest + fake engine existente; contrato `contracts/transcript-event.v2.schema.json` (inalterado)

**Storage**: Estado de utterance **em memória por conexão de canal** (não persistir); session-core já persiste HubEvents do feed

**Testing**: pytest no WSL (`services/transcription-service/tests`); unit da state machine pura; WS contract com fake engine; sem GPU/WASAPI

**Target Platform**: STT em WSL/Docker; agent Windows inalterado; session-core Java inalterado para emit path

**Project Type**: monorepo feature slice — STT state machine + docs + testes

**Performance Goals**: final após ~1 janela de idle (SC-007, ~3s com window 3.2s); state machine O(1) por janela; sem work extra em partial path além de contadores

**Constraints**: P9 sem texto/áudio em log; P10 CI sem GPU; P5 identidade de canal; FR-008 não disparar live-answer em partial; zero schema break (FR-013)

**Scale/Scope**: 1 operador local; tipicamente 2 canais (mic + system); 4 user stories; 1 serviço tocado

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Notas |
|-----------|--------|-------|
| P1 Spec antes de domínio | Pass | Spec clarified + plan + tasks nesta pasta |
| P2 Core independente de fornecedor | Pass | Política no STT; não amarra LLM/provedor |
| P3 WSL-first / Windows só captura | Pass | Mudança só no transcription-service (Linux); agent WASAPI intocado |
| P4 Contratos versionados | Pass | Reutiliza `transcript.final.v2`; **sem** alteração de schema |
| P5 Canal/origem ponta a ponta | Pass | Final herda session/channel/sourceType/device do canal |
| P6 Isolamento endpoint | Pass | Estado por conexão de canal; sem shared PyAudio |
| P7 endpointId | N/A | Fora de escopo |
| P8 Automação com autorização | Pass | Sem merge/force-push |
| P9 Privacidade | Pass | FR-014; logs só contadores/tipo, não dump de texto |
| P10 Testes determinísticos | Pass | Fake engine + unit state machine |

**Post-design re-check**: Pass — design não introduz serviço novo, não move captura, não loga áudio, schema estável.

## Project Structure

### Documentation (this feature)

```text
specs/024-issue-55-stt-final-utterance/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── utterance-finalization.md
├── checklists/
│   ├── requirements.md
│   └── utterance-final.md
└── tasks.md
```

### Source Code (repository root)

```text
services/transcription-service/
├── app/
│   ├── config.py                 # + finalization_idle_windows, finalization_max_open_seconds
│   ├── utterance.py              # NEW: pure state machine UtteranceFinalizer
│   ├── main.py                   # wire: observe every window result → partial/final
│   ├── transcriber.py            # (minimal) expose “window evaluated, no new text” signal if needed
│   └── consolidation.py          # unchanged (ingest still on delivered events)
└── tests/
    ├── test_utterance_finalizer.py   # NEW: pure unit tests
    ├── test_ws_utterance_final.py    # NEW: WS path with fake engine
    └── test_ws_audio_contract.py     # regression: partials still work; disconnect final

docs/development/running.md       # final-on-utterance + Assistente
docs/release/min-flow.md          # one-line note if appropriate
```

**Structure Decision**: Toda a lógica de produto fica no **transcription-service**. Session-core e desktop-shell já mapeiam `transcript.final.v2` → feed / Assistente; não reimplementar. Agent Windows não envia sinal de VAD nesta fatia (research R1).

## Complexity Tracking

> Nenhuma violação constitucional a justificar.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Current state (verified 2026-07-25)

| Item | Estado |
|------|--------|
| `emit(..., final=False)` default em toda janela | Confirmado `main.py` |
| `final=True` só em `transcriber.flush()` no disconnect | Confirmado |
| `transcribe_pcm` retorna `None` se vazio ou texto == last | Confirmado — idle natural |
| Schema v2 com `transcript.final.v2` | Existe; shell/session-core consomem |
| Live-answer só Final (019 FR-003) | Confirmado; empty state `awaiting_final` |
| Echo suppression em mic | Ativo; final não deve reintroduzir eco suprimido |

## Design decisions (see research.md)

| ID | Decision |
|----|----------|
| R1 | State machine no STT por **conexão de canal**, não no agent |
| R2 | Fechamento por **idle de janelas sem texto novo** após open (`idle_windows=1`) |
| R3 | Texto do final = **último texto útil** da utterance |
| R4 | Timeout `max_open_seconds=45` força final |
| R5 | Zero schema change |
| R6 | Disconnect: final residual só se utterance ainda open **ou** residual com texto novo; dedupe por flag `final_emitted` |
| R7 | Observar **toda** avaliação de janela (incluindo `None`), não só partials publicados |

## Implementation outline

1. **`UtteranceFinalizer`** (pure, testável): estados `idle` / `open`; métodos `on_text(text, now)`, `on_no_text(now)`, `on_disconnect(now)` → actions `emit_partial` / `emit_final` / `none`.
2. **Settings**: `finalization_idle_windows: int = 1`, `finalization_max_open_seconds: float = 45.0`.
3. **`main.py`**: por canal WS, instanciar finalizer; após cada `transcribe_pcm` (result ou None), e após echo-suppression, alimentar a machine; emitir partial ou final conforme action; prosódia só em final (já existente).
4. **Timeout**: no worker loop, checar `max_open` com `time.monotonic()` (ou clock injetável nos testes).
5. **Testes**: unit matrix + WS scripted fake_engine sequences.
6. **Docs**: running.md + quickstart da feature.

## Delivery phases

| Phase | Escopo | Stories |
|-------|--------|---------|
| **A — MVP** | State machine + wire main + testes + docs mínimos | US1, US3 (anti-spam), US4 docs |
| **B — Live-answer path** | Quickstart E2E nota; confirmação que feed/session-core expõe final (sem código shell se já OK) | US2 |
| Polish | Logs contadores, health optional settings surface, regression suite | — |

## Risks

| Risk | Mitigation |
|------|------------|
| Micro-pausa entre palavras fecha cedo demais com idle=1 | Default 1 é aceitável com janela ~3s; setting `idle_windows` para 2 se necessário |
| Monólogo sem pausa | `max_open_seconds=45` força final |
| Double final disconnect | flag por utterance / `already_finalized` |
| Echo-suppressed mic counted as open | Só `on_text` após suppress pass; suppress → tratar como no-text se open? Prefer: suppress não abre utterance; se open e suppress, `on_no_text` não — na verdade suppress return early sem chamar finalizer com text; chamar `on_no_text` apenas se window was evaluated. Plan: after suppress, do not feed text; feed as no_text only if we still want idle progress — **safer: suppress does not advance idle** (não fecha por eco). Research R8. |
| Adaptive window muda duração de idle | Idle contado em **número de janelas**, não segundos — SC-007 proporcional à janela atual |

## Test plan (automated)

```bash
PYTHONPATH=services/transcription-service pytest -q \
  services/transcription-service/tests/test_utterance_finalizer.py \
  services/transcription-service/tests/test_ws_utterance_final.py \
  services/transcription-service/tests/test_ws_audio_contract.py
```

Manual: `quickstart.md` — fala + pausa → `GET /api/sessions/{id}/events` contém `transcript.final.v2`.
