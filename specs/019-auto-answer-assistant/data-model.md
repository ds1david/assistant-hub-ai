# Data Model: Assistente de respostas automáticas

**Feature**: `specs/019-auto-answer-assistant`  
**Date**: 2026-07-25

Modelos de domínio/UI desta fatia. Tipos wire do hub de provedores e de sessão existentes permanecem a fonte de verdade nos módulos Java/Rust já documentados em `specs/015` e `specs/014`.

## Entidades de sessão (session-core — extensão aditiva)

### ConversationSession (existente)

Campos já expostos: `id`, `title`, `profileId`, `status`, `createdAt`, `startedAt`, `endedAt`, `metadata`.

**Uso nesta feature**: item da lista; alvo de seleção; âncora do feed e do invoke.

### Session list item

Projeção de leitura para `GET /api/sessions` — **mesmo shape** de `ConversationSession` (ou subconjunto estável: id, title, profileId, status, createdAt). Sem campos novos obrigatórios.

**Validação**: lista pode ser vazia; ordenação recomendada: `createdAt` descendente (mais recente primeiro).

## Preferências do Assistente (shell local)

### AssistantSessionPreferences

Persistidas **por `sessionId`** no JSON local do shell (não no core).

| Campo | Tipo | Default (ausente) | Notas |
|-------|------|-------------------|--------|
| `autoEnabled` | boolean | `false` | Modo automático |
| `enabledSourceTypes` | set/array de `"microphone" \| "system"` | `["system"]` | Só valores canônicos |
| `inputMode` | `"question-only" \| "question-plus-recent-context"` | `"question-plus-recent-context"` | Modo de montagem do `input` |

### AssistantPreferencesStore (arquivo)

```text
{
  "bySessionId": {
    "<uuid>": { "autoEnabled": true, "enabledSourceTypes": ["system"], "inputMode": "question-plus-recent-context" }
  }
}
```

**Regras**:
- Chave ausente ⇒ defaults da tabela acima.
- **Save on change**: toda alteração de toggle/origens/inputMode na UI MUST gravar o mapa para aquele `sessionId` (FR-025).
- **Load on select**: ao ativar uma sessão, MUST carregar prefs daquele id (ou defaults).
- Ao gravar, só sessionIds conhecidos pelo operador (não é erro reter prefs de sessão apagada; GC opcional fora do escopo).
- Nunca contém segredos, tokens ou texto de resposta do modelo.

## Orquestração em memória (shell — não persistido)

### Transcript identity

- `eventId` (string): chave de idempotência de disparo (FR-015).

### QuestionCandidate

| Campo | Tipo | Notas |
|-------|------|--------|
| `eventId` | string | Idempotência |
| `text` | string | Texto trimado do trecho final |
| `channelId` | string \| null | Metadado; não enviado no invoke nesta fatia |
| `sourceType` | `"microphone" \| "system" \| null` | Filtro FR-020 |

### AssistantTurn (interação na UI)

| Campo | Tipo | Notas |
|-------|------|--------|
| `id` | string | Id local da interação |
| `eventId` | string | Trecho de origem |
| `question` | string | Texto exibido |
| `status` | enum | `running` \| `queued` \| `done` \| `error` \| `cancelled` |
| `answer` | string \| null | Só em `done` |
| `error` | string \| null | Erro/cancelamento legível |
| `providerId` | string \| null | Proveniência se houver |
| `latencyMs` | number \| null | Proveniência se houver |

**Exibição no painel**: lista em ordem **mais recente primeiro** (último turn criado no topo). Estado `queued` MUST aparecer enquanto a interação aguarda a geração anterior (FR-009).

### State transitions (AssistantTurn)

```text
(new) → running → done
              ↘ error
              ↘ cancelled   (operador cancelou em favor de outra pergunta)
(new) → queued → running → …
```

### AssistantConflict

| Campo | Tipo | Notas |
|-------|------|--------|
| `runningQuestion` | string | Resumo da em execução |
| `runningTurnId` | string | |
| `incoming` | QuestionCandidate | Nova pergunta aguardando decisão |

### AssistantAutoController (estado)

| Campo | Notas |
|-------|--------|
| prefs | AssistantSessionPreferences da sessão ativa |
| seenEventIds | Set para idempotência |
| turns | Lista de AssistantTurn da sessão corrente na UI |
| runningTurnId / generation | Controle de uma geração ativa e descarte lógico |
| conflict | AssistantConflict \| null |
| queued | QuestionCandidate \| null (após “aguardar”) |

**Troca de sessão ativa**: carrega prefs da sessão; zera ou isola turns/seen da sessão anterior na UI (histórico de interações do Assistente é **só sessão corrente na UI** — Out of Scope de persistência longa).

## Transcript feed (existente)

### Transcript entry (shell)

Campos usados: `eventId`, `text`, `kind` (`Partial` \| `Final`), `channelId`, `sourceType`, `occurredAt`.

**Elegibilidade para candidata**:
1. `kind === Final`
2. `looksLikeQuestion(text)` conforme **FR-004** (min 8 chars; `?` ou prefixos canônicos pt/en)
3. `sourceType` ∈ `enabledSourceTypes` (se `sourceType` nulo/ausente: **inelegível** — FR-002; não fura default só-sistema)

## Invoke (existente — consumo)

### Invocation request (shell → core)

| Campo | Valor nesta feature |
|-------|---------------------|
| `sessionId` | Sessão ativa |
| `route` | `live-answer` |
| `capability` | `chat` |
| `input` | Montado conforme `inputMode` |
| `channelId` | omitido/null |

### InvocationResult

Usar campos existentes: `success`, `output`, `errorType`, `message`, `providerId`, `latencyMs`, `sourceType` (null sem channel).

## Contexto recente (montagem)

| Constante | Valor |
|-----------|--------|
| `MAX_CONTEXT_FINAL_SEGMENTS` | 12 |
| `MAX_CONTEXT_CHARS` | 4000 |

Apenas trechos `Final` da sessão (feed atual), excluindo ou incluindo a pergunta atual de forma documentada no builder (recomendação: contexto = finais **anteriores** à candidata; pergunta em seção separada “Pergunta atual:”).

## Relacionamentos

```text
ConversationSession 1 ── * HubEvent/transcript entries
ConversationSession 1 ── 0..1 AssistantSessionPreferences (no store local do shell)
Sessão ativa (shell) ── * AssistantTurn (memória UI)
AssistantTurn 0..1 ── 1 QuestionCandidate (origem)
```
