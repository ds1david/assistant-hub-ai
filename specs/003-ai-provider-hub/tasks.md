# Tarefas — AI Provider Hub

Visão R6 completa. Fatia entregue: `specs/015-issue-37-ai-provider-hub/` (+ `017-issue-40-invocation-sourcetype`). Itens abaixo marcam o que a visão ainda exige além dessas fatias.

- [x] Criar interfaces do provider SDK. (`ProviderAdapter`, `InvocationService`, etc. em `services/session-core/.../provider/`)
- [x] Adicionar schema `ai-provider-profile.v1`. (`contracts/ai-provider-profile.v1.schema.json`)
- [x] Criar parser e validador YAML. (`ProviderProfileValidator`, store + hot-reload)
- [x] Implementar `secretRef` com backend `env`. (`EnvSecretResolver`)
- [ ] Implementar armazenamento seguro Windows no desktop.
- [x] Criar adaptador OpenAI-compatible genérico. (`OpenAiCompatibleAdapter`)
- [ ] Criar presets Ollama e NVIDIA NIM. (parcial: Ollama/openai-compatible via perfil YAML de exemplo; presets NIM dedicados ainda não)
- [ ] Implementar descoberta via `/v1/models` quando suportada.
- [x] Criar teste de conexão com erros tipados. (API + UI + taxonomia de erros)
- [x] Implementar streaming e cancelamento. (`specs/026-r6-circuit-breaker-streaming/` — SSE `/invoke/stream` + cancel; sync cancel por timeout permanece)
- [x] Implementar fallback e circuit breaker. (fallback 015; circuit breaker 026 por providerId)
- [ ] Criar métricas de latência, tokens e custo informado. (latência no `InvocationResult`: parcial; tokens/custo: não)
- [x] Criar UI de provedores e modelos. (`apps/desktop-shell/src/ai-provider-panel.ts`)
- [x] Adicionar testes que garantem redação de chaves. (`SecretMaskingTest` e correlatos)
- [ ] Documentar políticas de privacidade por perfil. (parcial: `docs/security/provider-secrets.md`; políticas por perfil de conversa ainda abertas)

## Notas de higiene (2026-07-26)

Marcações `[x]` alinham a umbrella ao que a fatia 015/017 entregou no monorepo.
Circuit breaker, streaming, secure store OS, descoberta de modelos e presets NIM
permanecem trabalho futuro de R6 — não recortados nesta higiene.
