# Research: Live-answer modo entrevista (issue #61)

**Date**: 2026-07-26  
**Spec**: `specs/028-issue-61-live-answer-interview-mode/spec.md`

## R1 — Buffer de finais com origem

**Decision**: Estender `recentFinals` de `{ eventId, text }` para `{ eventId, text, sourceType: CanonicalSourceType | null }`. `trackFinal` grava `normalizeSourceType`. Builder filtra por canônico + preferência de mic.

**Rationale**: Hoje o buffer já recebe **todos** os finais no `ingestTranscript`/`markSeen`, inclusive mic — mas sem origem o modelo não distingue papéis e o toggle “só system no contexto” é impossível de testar.

**Alternatives considered**:
- Filtrar no feed UI em vez do controller → quebra orquestração unitária.
- Reconsultar session-core no invoke → latência e acoplamento desnecessários.

## R2 — Rótulos canônicos

**Decision**:
```text
Entrevistador: <texto>
Candidato (eu): <texto>
```
Constantes exportadas e assertadas em teste.

**Rationale**: pt-BR alinhado ao modo entrevista; evita jargão `system`/`microphone` no prompt do modelo.

**Alternatives considered**:
- Inglês only → pior para modelo pt-BR e operador.
- Incluir `channelId` no rótulo → ruído; sourceType basta (P5).

## R3 — Preferência `includeMicrophoneInContext`

**Decision**: Campo booleano nas prefs por sessão; **default true** quando ausente (`normalize`: se `undefined`/`null` → true; se explicit false → false). UI checkbox “Incluir minha voz no contexto”.

**Rationale**: Issue #61 pede default ON no treino; opt-out de privacidade; independente de `interviewMode` e de `enabledSourceTypes`.

**Alternatives considered**:
- Ligar automaticamente só com interviewMode → esconde o controle e confunde disparo vs contexto.
- Default false → regressão do pedido do usuário (“contexto deve considerar minha resposta”).

**Serde Rust**: `#[serde(default = "default_true")]` ou `Option<bool>` com normalize no load; preferir default function `true` + TS normalize espelhado.

## R4 — Estilo 1ª pessoa via prefixo de input

**Decision**: Constante `INTERVIEW_ANSWER_INSTRUCTION` (pt-BR) prefixada ao input montado **somente** se `prefs.interviewMode === true`, antes do bloco de contexto/pergunta:

```text
<INSTRUÇÃO ENTREVISTA>
...regras 1ª pessoa, 30–90s, sem meta, sem inventar...

Contexto recente do transcript:
1. Entrevistador: ...
2. Candidato (eu): ...

Pergunta atual:
...
```

Invoke permanece `(sessionId, route live-answer, capability chat, input string)`.

**Rationale**: `invokeAiProvider` hoje só envia `input`; não há system message separado no client. Prefixo é aditivo, testável, sem tocar hub.

**Alternatives considered**:
- System prompt no perfil de provedor → global, não por sessão/modo entrevista.
- Novo campo no API de invoke → escopo maior (015/hub); adiar.

## R5 — Detector de estilo só em testes

**Decision**: Exportar `hasMetaAssistantStyle(text: string): boolean` com padrões FR-012. Usar em Vitest com fixtures boas/ruins. **Não** chamar no caminho `startTurn` para descartar resposta.

**Rationale**: FR-012b; modelos ocasionalmente violam instrução — apagar resposta piora UX. CI prova instrução + detector; spot-check manual no quickstart.

**Alternatives considered**:
- Soft-strip de “Claro!” no início → edge cases e i18n; adiar.
- Retry automático com re-prompt → latência e custo; fora de escopo.

## R6 — Latência

**Decision**: Documentar elos (janela STT ~3.2s, `FINALIZATION_IDLE_WINDOWS=1`, Whisper model, timeout/modelo da rota `live-answer`, fallback). Recomendar ops entrevista sem mudar default global de produto. UI: manter `latencyMs` por turn (já em `assistant-panel.ts`).

**Rationale**: Issue pede docs + knobs; código de finalização já permite idle=1 (024). Mudar default Whisper global regrediria WER em outros modos.

**Recommended ops (docs only)**:

| Knob | Valor sugerido entrevista | Onde |
|------|---------------------------|------|
| `WHISPER_MODEL` | `small` (default) ou `base` se priorizar velocidade | STT env |
| `FINALIZATION_IDLE_WINDOWS` | `1` | STT env |
| Modelo rota `live-answer` | modelo de baixa latência no perfil de provedores | `config/ai-providers.yaml` / UI hub |
| Partials → invoke | **nunca** | shell (inalterado) |

## R7 — Escopo de código

**Decision**: Apenas `apps/desktop-shell` (+ Tauri prefs) e `docs/**`. Sem STT, sem session-core, sem schema v2.

**Rationale**: Contexto e estilo são orquestração de UI; STT já emite finais com sourceType.

## R8 — Limites de janela

**Decision**: Manter `MAX_CONTEXT_FINAL_SEGMENTS` / `MAX_CONTEXT_CHARS` da 019 (12 / 4000). Filtrar mic **antes** de contar segmentos quando preferência off (system-only window). Quando on, mic e system competem na mesma janela por recência.

**Rationale**: Evita regressão de tamanho de prompt; testes existentes de limite continuam válidos com ajuste de shape.

## Open items deferred to implement

- Copy exata do bloco de instrução (conteúdo FR-009–011) — redigir em implement com asserts de substrings canônicas.
- Se Rust prefs `Default` deve setar `include_microphone_in_context: true` — sim, alinhar a TS.
