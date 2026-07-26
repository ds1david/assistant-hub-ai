# Quickstart validation: final-on-utterance (issue #55)

**Feature**: `specs/024-issue-55-stt-final-utterance`  
**Date**: 2026-07-25

## Prerequisites

- WSL: STT + session-core up (`./scripts/wsl/start-assistant-hub.sh --no-build` or equivalent)
- Windows: audio agent com **mesmo sessionId** da sessão ativa (UUID session-core)
- Opcional para US2: desktop shell com automático **ligado**, origem **system**, provedor `live-answer` OK

## Automated (P10 — no GPU)

```bash
PYTHONPATH=services/transcription-service pytest -q \
  services/transcription-service/tests/test_utterance_finalizer.py \
  services/transcription-service/tests/test_ws_utterance_final.py \
  services/transcription-service/tests/test_ws_audio_contract.py
```

**Expect**: all green; unit tests cover open→partials→1 final; second utterance → second final; no final without text; disconnect dedupe.

## Manual A — Final na sessão sem disconnect (SC-001)

1. Criar/selecionar sessão no shell (ou anotar UUID).
2. Iniciar agent com esse sessionId (profile com system/loopback se for remoto).
3. Falar **uma frase** (ex.: pergunta curta) e **fazer pausa** ≥ ~4s (mais que uma janela STT).
4. **Sem** parar o agent, consultar eventos:

```bash
# substitua SESSION_ID
curl -s "http://localhost:8080/api/sessions/SESSION_ID/events" | jq '.[].type' | sort | uniq -c
```

**Expect**:
- Contagem de `transcript.partial.v2` ≥ 1
- Contagem de `transcript.final.v2` ≥ 1
- Repetir fala + pausa → contagem de finais aumenta (não fica 0)

5. Repetir o passo 3–4 **três vezes** (SC-001: 100% das N≥3).

## Manual B — Live-answer path (SC-003 / US2)

1. Shell: sessão ativa = agent; automático **on**; origem **system** (e mic se for o caso).
2. Produzir pergunta clara no canal system + pausa.
3. **Expect**:
   - Feed/session tem Final
   - Empty state **não** fica preso só em “Aguardando trecho final…” se a pergunta for elegível
   - Assistente **pode** iniciar geração (sujeito a 019/023 — se não for pergunta, Final existe mas não gera)

## Manual C — Partials streaming (SC-004)

1. Durante a fala (antes da pausa), abrir dashboard STT `http://localhost:8001`.
2. **Expect**: texto partial atualiza; após pausa, final existe na sessão (pode ou não ser destacado na UI — não bloqueia aceite).

## Manual D — Anti-spam (SC-002)

1. Fala longa com vários partials sem pausa longa o suficiente para idle.
2. **Expect**: 0 finais até pausa; após pausa, **exatamente 1** final daquela utterance.

## Docs check (SC-006)

- [x] `docs/development/running.md` menciona final ao fim de utterance e vínculo com Assistente
- [x] Este quickstart descreve verificação sem disconnect

## Settings (implementados)

| Env | Default | Health field |
|-----|---------|--------------|
| `FINALIZATION_IDLE_WINDOWS` | `1` | `finalizationIdleWindows` |
| `FINALIZATION_MAX_OPEN_SECONDS` | `45` | `finalizationMaxOpenSeconds` |

```bash
curl -s http://localhost:8001/health | jq '{finalizationIdleWindows, finalizationMaxOpenSeconds, prosodyEnabled}'
```

## Failure triage

| Sintoma | Causa provável |
|---------|----------------|
| Só partials após pausa | Finalizer não wired / idle_windows alto / janelas não avaliadas em None |
| Final só ao parar agent | Ainda no path só-disconnect (regressão) |
| Muitos finais por frase | idle_windows=0 ou bug double emit |
| Assistente ainda awaiting_final com Final na sessão | sessionId mismatch (020–022) ou automático off / origem |
| Assistente com Final de afirmação sem gerar | Esperado — heurística 023, não bug #55 |
