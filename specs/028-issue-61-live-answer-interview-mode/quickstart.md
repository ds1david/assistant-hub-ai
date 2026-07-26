# Quickstart: Modo entrevista — contexto mic+system e 1ª pessoa (issue #61)

## Prerequisites

- Stack running (STT + session-core + agent + shell): see `docs/development/running.md`
- Provedor com rota `live-answer` habilitada
- SessionId **igual** no agent e no shell
- Finais de utterance ativos (`FINALIZATION_IDLE_WINDOWS=1` default)

## Operator flow (manual E2E)

1. Abrir **desktop shell** (não o dashboard STT `:8001`).
2. Selecionar/criar sessão; copiar id para o agent.
3. Painel **Assistente**:
   - Automático **ON**
   - Origem de **disparo**: só **sistema** (default)
   - Modo de entrada: **pergunta + contexto recente**
   - **Modo entrevista** ON
   - **Incluir minha voz no contexto** ON (default)
4. Falar no **microfone** uma resposta curta; pausar → deve aparecer Final `microphone` no feed (não deve disparar Assistente).
5. Entrevistador (loopback/system) faz pergunta; pausar → Final `system` → Assistente **gera**.
6. No painel Assistente:
   - Resposta em **1ª pessoa**, legível em voz alta
   - (Dev) opcional: inspecionar input montado nos testes; em runtime o modelo recebeu contexto com rótulos `Entrevistador:` e `Candidato (eu):` se havia mic
7. Desligar **Incluir minha voz no contexto**; nova pergunta: contexto sem mic (só system + pergunta).
8. Confirmar: resposta aparece no **Assistente**, não no `:8001`.

## Automated (WSL)

```bash
cd apps/desktop-shell
npm test -- --run tests/assistant-auto.test.ts tests/assistant-prefs.test.ts tests/assistant-panel.test.ts
```

### Expected automated coverage

| Case | Expect |
|------|--------|
| Mixed finals + include mic ON | input contains mic + system text + labels |
| include mic OFF | no microphone text in context block |
| question-only | no context block |
| interviewMode ON | instruction prefix present |
| interviewMode OFF | no instruction prefix |
| style detector | bad fixtures true; good fixtures false |
| mic Final only, disparo system | no new turn |
| partial | no new turn |
| prefs default missing field | `includeMicrophoneInContext === true` |
| prefs S/T isolation | OFF stays on S after switch |

## Latency knobs (ops, not code defaults)

Documented fully in `docs/development/running.md` after implement:

| Elo | Knob / note |
|-----|-------------|
| Janela STT | ~3.2s default window |
| Final after pause | `FINALIZATION_IDLE_WINDOWS=1` |
| Whisper | `WHISPER_MODEL=small` (or `base` for speed) |
| LLM | low-latency model on route `live-answer` |
| Fallback | adds tail latency if primary fails |
| Partial invoke | **forbidden** |

## Disparo vs contexto (cheat sheet)

| | Disparo | Contexto |
|--|---------|----------|
| Control | `enabledSourceTypes` | `includeMicrophoneInContext` + `inputMode` |
| Default | system only | mic+system when context mode + include ON |
| Mic phrase | does **not** fire (default) | **does** enter window (default) |

## Out of scope for this quickstart

- TTS
- Invisible interview cheating
- Changing STT schema
