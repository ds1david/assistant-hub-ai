# Data Model: AI Provider Hub — registro e invocação de provedores pluggable (R6)

Duas categorias de dado: (1) o **perfil declarativo** persistido (arquivo YAML, espelha `contracts/ai-provider-profile.v1.schema.json` — fonte única, P4, sem duplicar regras) e (2) os **tipos transientes de resultado** de uma chamada (nunca persistidos além do log de métrica de `research.md` Decisão 7).

## Entidade: Provider (perfil declarativo, dentro de `providers[]`)

Espelha `$defs/provider` do schema v1. Mapeado por `Provider.java` (record).

| Campo | Tipo | Origem / Regra |
|---|---|---|
| `id` | `String` | `^[a-z][a-z0-9-]{2,63}$`; único dentro do perfil (FR-002 — validação rejeita duplicado) |
| `label` | `String` | 1–120 caracteres |
| `type` | enum | `openai-compatible` \| `anthropic` \| `gemini` \| `custom-http` — só `openai-compatible` tem adaptador implementado nesta fatia (research.md Decisão 5); os demais são aceitos pelo schema mas rejeitados na invocação com erro de validação claro (Edge Case da spec) |
| `enabled` | `boolean` | Provider com `enabled: false` nunca é efetivamente invocado (FR-005) |
| `baseUrl` | `String` (URI) | — |
| `authentication` | `ProviderAuthentication` | ver abaixo |
| `defaults` | `ProviderDefaults` | ver abaixo |
| `capabilities` | `Set<String>` | subconjunto de `chat`, `responses`, `embeddings`, `vision`, `audio-input`, `tool-calling`, `structured-output`, `streaming`; usado por FR-010 (rejeição por incompatibilidade de capacidade) |

## Entidade: ProviderAuthentication

| Campo | Tipo | Regra |
|---|---|---|
| `mode` | enum | `none` \| `bearer` \| `api-key` |
| `secretRef` | `String`, nullable se `mode=none` | `^(env\|os):[A-Za-z0-9_./-]+$`; obrigatório se `mode != none` (schema `allOf`/`if`/`then`) — nunca contém o valor resolvido, só o ponteiro |
| `headerName` | `String`, nullable | 1–80 caracteres, usado quando `mode=api-key` com header custom |

## Entidade: ProviderDefaults

| Campo | Tipo | Regra |
|---|---|---|
| `model` | `String` | obrigatório |
| `temperature` | `Double`, nullable | 0–2 |
| `topP` | `Double`, nullable | (0, 1] |
| `maxTokens` | `Integer`, nullable | ≥ 1 |
| `timeoutMs` | `Integer` | 1000–600000; limite isolado por invocação (FR-003) |

## Entidade: Route (dentro de `routes{}`)

| Campo | Tipo | Regra |
|---|---|---|
| chave do mapa | `String` | nome arbitrário da tarefa/capacidade (ex.: `live-answer`, `embeddings`, ou o nome de uma `capability`) |
| `primary` | `String` | `id` de um `Provider` do mesmo perfil |
| `fallbacks` | `List<String>`, ordenada | `id`s de `Provider`, tentados em ordem só quando o primário falhar, expirar ou retornar rate limit (FR-005) |

## Entidade: ProviderProfile (documento raiz)

| Campo | Tipo | Regra |
|---|---|---|
| `version` | `int` | `const 1` |
| `providers` | `List<Provider>` | mínimo 1 |
| `routes` | `Map<String, Route>` | pode ser vazio |

**Persistência**: arquivo YAML único (`config/ai-providers.yaml`, caminho configurável via `session-core.ai-provider-hub.path`; já coberto por uma entrada pré-existente de `.gitignore`), validado contra o schema a cada carga e a cada escrita (`ProviderProfileValidator`). Escrita é atômica (arquivo temporário + rename) — uma escrita interrompida nunca deixa o arquivo em estado parcialmente corrompido, mesmo padrão de garantia usada pelo Memory Hub para eventos (`specs/013`, por transação SQLite; aqui, por rename atômico de arquivo).

**Ciclo de vida / hot-reload (FR-015)**: `ProviderRegistry` mantém o `ProviderProfile` vigente em memória. Toda mutação (via API/UI ou edição manual do arquivo detectada na próxima operação) passa por: validar → escrever atomicamente → recarregar o registry — nunca exige reiniciar o processo. Não há watcher de filesystem nesta fatia: a UI/API sempre escreve através do mesmo processo que mantém o registry, então o reload acontece na mesma chamada que fez a mutação.

## Tipo transiente: ConnectionTestResult

Não persistido — retorno de `ProviderAdapter.testConnection(Provider)`, exposto via `POST /api/ai-providers/{id}/test` (FR-011) e consumido pela UI (FR-013).

| Campo | Tipo |
|---|---|
| `providerId` | `String` |
| `success` | `boolean` |
| `errorType` | `InvocationErrorType`, nullable (só quando `success=false`) |
| `message` | `String` — nunca contém segredo nem header de autenticação |

## Tipo transiente: InvocationResult

Não persistido além do log de métrica (research.md Decisão 7) — retorno de `InvocationService.invoke(...)`, exposto via `POST /api/ai-providers/invoke` (FR-012).

| Campo | Tipo |
|---|---|
| `providerId` | `String` — provedor que efetivamente respondeu (pode ser um fallback, não necessariamente o `primary` da rota) |
| `model` | `String` |
| `capability` | `String` |
| `sessionId` | `String` |
| `channelId` | `String`, nullable |
| `success` | `boolean` |
| `errorType` | `InvocationErrorType`, nullable |
| `output` | `String`, nullable (só quando `success=true`) |
| `message` | `String`, nullable (só quando `success=false`; adicionado durante o Implement, espelhando `ConnectionTestResult.message` — o resultado original não tinha como carregar o motivo textual de uma falha além do enum) |
| `latencyMs` | `long` |
| `occurredAt` | `Instant` |

## Enum: InvocationErrorType

`AUTHENTICATION` \| `MODEL_NOT_FOUND` \| `TIMEOUT` \| `RATE_LIMITED` \| `GENERIC` \| `CAPABILITY_MISMATCH` — ver research.md Decisão 6 para o mapeamento a partir do status HTTP do provedor. Qualquer um desses seis tipos aciona a tentativa do próximo `fallback` da rota, se houver (FR-005 usa "falhar" de forma ampla, cobrindo todos os tipos, não só timeout/rate-limit); `CAPABILITY_MISMATCH` (FR-010, adicionado durante o Implement — o enum original omitia um valor para este caso) é reavaliado por candidato conforme o loop de fallback percorre `primary`/`fallbacks[]` — um fallback com a capacidade correta ainda pode atender mesmo que o `primary` não a suporte.

## Tipo transiente: SecretPreview

Não persistido — gerado sob demanda por `AiProviderController`, nunca contém o valor completo do segredo (FR-014).

| Campo | Tipo |
|---|---|
| `providerId` | `String` |
| `maskedValue` | `String`, ex.: `"sk-...aB3f"` (3 primeiros + 4 últimos caracteres do valor resolvido, resto substituído por `...`); `null` se `authentication.mode == none` ou o segredo não puder ser resolvido |

## Relações

- `ProviderProfile` 1 → N `Provider` (por `providers[]`); o schema exige `minItems: 1` — descoberto durante o Implement (T028/AiProviderController): remover o único provedor restante é rejeitado (`ProviderProfileValidationException` → `400`), não esvazia o perfil. A UI desktop (US3) deve impedir ou avisar antes de tentar remover o último provedor.
- `ProviderProfile` 1 → N `Route` (por `routes{}`); cada `Route.primary`/`fallbacks[]` referencia `Provider.id` do mesmo perfil (validado — FR-002 rejeita referência a `id` inexistente).
- `InvocationResult`/`ConnectionTestResult` referenciam um `Provider.id`, mas não são persistidos como entidade — só como resultado transiente + linha de log.
- `InvocationResult` referencia `sessionId`/`channelId` de uma `ConversationSession`/`HubEvent` já existentes (`specs/013`), sem duplicar nem alterar esses dados — o AI Provider Hub é consumidor, não dono, do contexto de sessão.
