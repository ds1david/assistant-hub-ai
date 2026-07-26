# Feature Specification: R6 — Descoberta de modelos e métricas de uso

**Feature Branch**: `feature/027-r6-model-discovery-metrics`  
**Created**: 2026-07-26  
**Status**: Draft  

**Input**: Fechar gaps de `specs/003-ai-provider-hub/`: descoberta via `/v1/models` e métricas de tokens (latência já existe); samples/presets Ollama e NVIDIA NIM documentados.

## User Stories

### US1 — Listar modelos de um provedor (P1)
Operador/API consulta os modelos expostos por um provedor OpenAI-compatible (ou fake) sem editar YAML.

### US2 — Ver tokens na invocação (P1)
Após invoke, o resultado inclui contagens de tokens quando o provedor as devolve (prompt/completion/total); se ausentes, campos nulos — nunca inventados.

### US3 — Presets de exemplo (P2)
Repositório documenta perfis de exemplo Ollama local e NVIDIA NIM (hosted) sem chaves em claro.

## Requirements

- **FR-001**: API `GET /api/ai-providers/{id}/models` lista modelos descobertos ou erro tipado.
- **FR-002**: OpenAI-compatible chama `GET {baseUrl}/models` e parseia `data[].id`.
- **FR-003**: Fake retorna lista determinística para testes.
- **FR-004**: `InvocationResult` inclui `promptTokens`, `completionTokens`, `totalTokens` opcionais.
- **FR-005**: OpenAI-compatible preenche tokens a partir de `usage` no JSON de chat/completions quando presente.
- **FR-006**: Não inventar tokens nem custo; custo monetário fora desta fatia (null).
- **FR-007**: Logs não incluem prompt/output; métricas de token só em campos estruturados do resultado.
- **FR-008**: Samples YAML Ollama + NIM documentados; sem segredos.

## Success Criteria

- **SC-001**: Teste fake: list models ≥ 1 id.
- **SC-002**: Teste fake/OpenAI parse: invoke preenche totalTokens quando usage presente.
- **SC-003**: Suíte session-core verde sem rede externa.

## Out of Scope

- UI desktop de lista de modelos (API first).
- Cálculo de custo USD.
- Secure store OS / DPAPI.
