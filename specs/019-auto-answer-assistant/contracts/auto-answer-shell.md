# Contrato: Assistente automático — API de sessão (aditiva) + comandos Tauri + UI

**Feature**: `specs/019-auto-answer-assistant`  
**Date**: 2026-07-25

Formalidade alinhada a `specs/015-issue-37-ai-provider-hub/contracts/ai-provider-api.md`.  
Invoke de IA **não** muda nesta fatia (ver `specs/015` e `specs/017`); apenas o consumo pelo shell.

## REST — session-core (extensão aditiva)

| Método | Path | Request | Response | Erros |
|--------|------|---------|----------|-------|
| `GET` | `/api/sessions` | — | `200` + `ConversationSession[]` (lista; pode ser `[]`) | — (503/rede via infra) |
| `POST` | `/api/sessions` | existente (`title`, `profileId`, `metadata?`) | `201` + sessão | `400` validação |
| `GET` | `/api/sessions/{id}` | — | existente | `404` |
| `GET` | `/api/sessions/{id}/events` | — | existente (base do transcript feed) | `404` |
| `POST` | `/api/ai-providers/invoke` | existente | `InvocationResult` | existente (`404` rota/sessão, `422` origem se `channelId` — **esta feature omite channelId**) |

**GET /api/sessions**:
- Fonte: sessões no `SessionRepository` (rehidratadas do Memory Hub na subida).
- Ordenação: preferencialmente `createdAt` desc.
- Sem paginação nesta fatia (escala local).

Nenhuma resposta inclui segredos ou áudio.

## Tauri — `apps/desktop-shell`

| Comando | Args | Retorno | Endpoint / ação |
|---------|------|---------|-----------------|
| `list_sessions` | — | `SessionSummary[]` | `GET /api/sessions` |
| `create_session` | `{ title, profileId }` | `SessionSummary` | `POST /api/sessions` |
| `get_session_status` | `{ sessionId }` | existente | existente |
| `get_transcript_feed` | `{ sessionId }` | existente | existente |
| `invoke_ai_provider` | `{ sessionId, route, capability, input, channelId? }` | existente | `POST .../invoke` |
| (local) prefs load/save | via módulo config/prefs do shell — **não** precisa ser comando se FS só no Rust; se webview precisa, expor `get_assistant_prefs` / `set_assistant_prefs` com `{ sessionId, prefs }` **sem** rede |

### Preferências (contrato lógico)

```typescript
type CanonicalSourceType = "microphone" | "system";
type InputMode = "question-only" | "question-plus-recent-context";

interface AssistantSessionPreferences {
  autoEnabled: boolean;
  enabledSourceTypes: CanonicalSourceType[];
  inputMode: InputMode;
}
```

Defaults: ver [data-model.md](../data-model.md).

## UI — contratos observáveis (testids / comportamento)

Painel **Assistente** (além de sessão):

| Elemento | data-testid (recomendado) | Comportamento |
|----------|---------------------------|---------------|
| Painel | `assistant-panel` | Sempre montável |
| Toggle automático | `assistant-enabled` | Liga/desliga auto da sessão ativa |
| Origens | `assistant-origin-system`, `assistant-origin-microphone` | Checkboxes; default system on, mic off |
| Modo entrada | `assistant-input-mode` | select/radio: só pergunta / contexto recente |
| Conflito | `assistant-conflict` | Visível só em conflito |
| Cancelar | `assistant-conflict-cancel` | FR-008 |
| Aguardar | `assistant-conflict-wait` | FR-009 |
| Turno | `assistant-turn` | `data-status` = running\|queued\|done\|error\|cancelled; lista **mais recente primeiro** |
| Resposta | `assistant-answer` | Texto da resposta |
| Lista sessões | `session-list` | Itens selecionáveis |
| Criar sessão | `session-create` | Cria e ativa |
| Id ativo | `session-active-id` | Texto do UUID/id |

## Regras de orquestração (contrato de comportamento)

1. Só `Final` + `looksLikeQuestion` (FR-004) + origem habilitada (FR-002) + `autoEnabled`.
2. Idempotência por `eventId`.
3. Uma geração ativa; segunda pergunta ⇒ conflito obrigatório.
4. Cancelar ⇒ descarte lógico de resultado tardio.
5. Aguardar ⇒ fila (última pendente); ao terminar, inicia pendente; pergunta C com geração ainda em curso ⇒ reabre conflito (FR-010).
6. `input` montado conforme `inputMode` e limites da janela (research Decisão 5).
7. Rota `live-answer`, capability `chat`, sem `channelId`.
8. Turns na UI: mais recente primeiro (FR-029). Create session UI: defaults FR-028.

## Taxonomia de erro na UI

Reutilizar `InvocationErrorType` do hub (015): exibir label + `message` seguro quando houver (já melhorado no painel de teste de conexão; mesmo espírito).
