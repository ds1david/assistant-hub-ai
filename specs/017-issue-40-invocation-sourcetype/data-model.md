# Data Model: Origem de canal no resultado de invocação

**Feature**: `specs/017-issue-40-invocation-sourcetype`  
**Date**: 2026-07-25

Este documento **estende** o modelo de `specs/015-issue-37-ai-provider-hub/data-model.md` apenas nos pontos afetados pelo débito #40. Entidades de provedor/rota/perfil permanecem inalteradas.

## Enum canônico: `SourceType` (domínio de origem)

Valores **exatos** (contrato transcript v2):

| Valor wire | Significado |
|------------|-------------|
| `microphone` | Origem de microfone / fala local |
| `system` | Origem de áudio de sistema / remoto |

Qualquer outro valor (incluindo null em evento, string vazia, aliases) **não** é canônico.

## Entidade existente (somente leitura): `HubEvent`

Fonte de evidência de origem (Q5). Campos relevantes:

| Campo | Uso nesta feature |
|-------|-------------------|
| `sessionId` | Escopo da busca |
| `correlation["channelId"]` | Filtro do canal da invocação |
| `correlation["sourceType"]` | Candidato a origem |

Não se altera o schema de persistência do Memory Hub nem o SDK `HubEvent` nesta fatia.

## Tipo resolvido: `ResolvedChannelOrigin` (transiente)

Não persistido. Resultado interno do resolvedor.

| Campo | Tipo | Regras |
|-------|------|--------|
| `channelId` | `String` | Não blank |
| `sourceType` | `String` | Exatamente `microphone` ou `system` |

## Tipo de resultado: `InvocationResult` (estendido)

Não persistido além do log de métrica. Retorno de `InvocationService.invoke` / `POST /api/ai-providers/invoke`.

| Campo | Tipo | Mudança |
|-------|------|---------|
| `providerId` | `String` | inalterado |
| `model` | `String`, nullable | inalterado |
| `capability` | `String` | inalterado |
| `sessionId` | `String` | inalterado |
| `channelId` | `String`, nullable | inalterado |
| **`sourceType`** | **`String`, nullable** | **NOVO (aditivo)** |
| `success` | `boolean` | inalterado |
| `errorType` | `InvocationErrorType`, nullable | inalterado |
| `output` | `String`, nullable | inalterado |
| `message` | `String`, nullable | inalterado |
| `latencyMs` | `long` | inalterado |
| `occurredAt` | `Instant` | inalterado |

### Regras de preenchimento de `sourceType` no resultado

| Condição na entrada | `sourceType` no resultado | Outro efeito |
|---------------------|---------------------------|--------------|
| `channelId` nulo ou blank | `null` (N/A documentado) | Invoke segue para rota/provedor |
| `channelId` presente + origem resolvida | valor canônico | Invoke segue; log inclui o valor |
| `channelId` presente + 0 eventos do canal / sem sourceType | — | **Não** monta resultado de sucesso; falha 422 pré-provedor |
| `channelId` presente + valor único não canônico | — | falha 422 pré-provedor |
| `channelId` presente + ≥2 valores distintos no canal | — | falha 422 pré-provedor (conflito) |
| Fallback de provedor após origem resolvida | **mesmo** `sourceType` resolvido | Proveniência de provedor muda; origem de canal não |

## Entrada: `InvocationRequest` / `InvokeRequest`

| Campo | Mudança |
|-------|---------|
| `sessionId` | inalterado |
| `channelId` | inalterado (nullable) |
| `capability` | inalterado |
| `input` | inalterado |
| `route` (só API) | inalterado |
| **`sourceType`** | **NÃO existe na entrada** (FR-010) |

## Falha de domínio: `ChannelOriginUnresolvedException` (nome ilustrativo)

| Atributo | Valor |
|----------|--------|
| Quando | Resolução falha (ausente / não canônico / conflito) |
| HTTP | `422 Unprocessable Entity` |
| Corpo | `{ "error": "<mensagem explícita em PT>" }` (padrão dos handlers existentes) |
| Fallback de rota | **Não** acionado |

Submotivos (mensagens distintas recomendadas para testes/SC):

1. canal sem eventos de origem na sessão  
2. origem não canônica  
3. conflito de origens no mesmo canal  
4. (opcional) sessão inexistente quando `channelId` presente  

## Relacionamentos

```text
ConversationSession 1 ── * HubEvent
       │                      │
       │                      └── correlation.channelId + correlation.sourceType
       │
       └── Invocation (transiente)
              ├── channelId? ──► ChannelOriginResolver ──► sourceType?
              └── InvocationResult.sourceType (eco)
```

- O AI Provider Hub **consome** origem; **não** é dono do cadastro de canais.  
- `ConnectionTestResult` **não** ganha `sourceType` (sem canal de sessão).

## Validação (resumo testável)

1. Canônico = `{microphone, system}` apenas.  
2. Resolução monotônica por canal: um valor ou falha.  
3. Isolamento: canais distintos na mesma sessão não compartilham origem no resultado.  
4. Sucesso e falha de **provedor** preservam o `sourceType` já resolvido.
