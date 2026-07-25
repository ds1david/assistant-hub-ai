# Contrato: API REST do AI Provider Hub + comandos Tauri do desktop

Interfaces novas introduzidas por esta feature. Formalidade equivalente à já usada para `SessionController` no projeto (código Java como fonte de verdade — este documento é a referência de design para `/speckit-tasks`/`/speckit-implement`, não um schema gerado). O único contrato JSON Schema formal envolvido continua sendo `contracts/ai-provider-profile.v1.schema.json`, reaproveitado sem alteração para o corpo de `Provider`/`Route` abaixo.

## REST — `services/session-core` (`AiProviderController`, prefixo `/api/ai-providers`)

Todas as respostas de erro seguem o padrão já usado por `SessionController` (`ResponseStatusException` → corpo de erro padrão do Spring). Nenhuma resposta, em nenhum endpoint, inclui o valor resolvido de um segredo — só `secretRef` (não sensível) ou `SecretPreview.maskedValue` quando explicitamente pedido.

| Método | Path | Request | Response | Erros |
|---|---|---|---|---|
| `GET` | `/api/ai-providers` | — | `List<Provider>` (perfil vigente do `ProviderRegistry`) | — |
| `POST` | `/api/ai-providers` | `Provider` (sem `id` pré-existente) | `201` + `Provider` criado | `400` perfil resultante inválido (schema) |
| `PUT` | `/api/ai-providers/{id}` | `Provider` (substitui campos editáveis) | `200` + `Provider` atualizado | `404` id não existe; `400` perfil resultante inválido |
| `PATCH` | `/api/ai-providers/{id}/enabled` | `{ "enabled": boolean }` | `200` + `Provider` atualizado | `404` id não existe |
| `DELETE` | `/api/ai-providers/{id}` | — | `204` | `404` id não existe; `409` id referenciado por uma `Route` existente |
| `GET` | `/api/ai-providers/{id}/secret-preview` | — | `SecretPreview` | `404` id não existe |
| `POST` | `/api/ai-providers/{id}/test` | — | `200` + `ConnectionTestResult` (FR-011) | `404` id não existe |
| `POST` | `/api/ai-providers/invoke` | `{ "sessionId": string, "route": string, "capability": string, "input": string }` | `200` + `InvocationResult` (FR-012) | `404` sessão ou rota não existe; `422` capacidade incompatível com o provedor resolvido (FR-010) |

Toda mutação (`POST`/`PUT`/`PATCH`/`DELETE`) aplica hot-reload no `ProviderRegistry` antes de responder (FR-015) — a resposta já reflete o estado pós-reload.

`invoke` resolve o provedor a partir de `routes[route]` (primário, com fallback conforme `InvocationErrorType`), não aceita `providerId` direto — mantém a invocação sempre passando pela política de rota do perfil (FR-005).

## Tauri — `apps/desktop-shell/src-tauri` (`ai_provider_client.rs` + comandos registrados em `main.rs`)

Mesmo padrão de `session_core_client.rs`/`api-client.ts`: o webview nunca fala HTTP diretamente; cada comando Tauri delega para um método puro de `ai_provider_client.rs`, que chama o endpoint REST correspondente.

| Comando Tauri | Args | Retorno | Endpoint REST correspondente |
|---|---|---|---|
| `list_ai_providers` | — | `Provider[]` | `GET /api/ai-providers` |
| `save_ai_provider` | `{ provider: Provider }` | `Provider` | `POST`/`PUT /api/ai-providers[/{id}]` (novo vs. edição, por presença de `id`) |
| `set_ai_provider_enabled` | `{ providerId, enabled }` | `Provider` | `PATCH /api/ai-providers/{id}/enabled` |
| `delete_ai_provider` | `{ providerId }` | `void` | `DELETE /api/ai-providers/{id}` |
| `get_ai_provider_secret_preview` | `{ providerId }` | `SecretPreview` | `GET /api/ai-providers/{id}/secret-preview` |
| `test_ai_provider_connection` | `{ providerId }` | `ConnectionTestResult` | `POST /api/ai-providers/{id}/test` |
| `invoke_ai_provider` | `{ sessionId, route, capability, input }` | `InvocationResult` | `POST /api/ai-providers/invoke` |

Tipos TypeScript espelhando `Provider`/`ConnectionTestResult`/`InvocationResult`/`SecretPreview` entram em `api-client.ts`, no mesmo estilo camelCase já usado para `SessionSummary`/`ChannelStatusView` (ver comentário de topo do arquivo).

## Taxonomia de erro compartilhada (REST + Tauri + UI)

Mesmos cinco valores de `InvocationErrorType` (data-model.md) aparecem em `ConnectionTestResult.errorType` e `InvocationResult.errorType`, para que a UI (FR-013/FR-014) e qualquer chamador de API (FR-011/FR-012) apliquem exatamente a mesma distinção — nenhuma camada reclassifica o erro de forma diferente das demais.
