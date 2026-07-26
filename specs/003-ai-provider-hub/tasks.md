# Tarefas — AI Provider Hub

Visão R6 completa. Fatia entregue: `specs/015-issue-37-ai-provider-hub/` (+ `017-issue-40-invocation-sourcetype`). Itens abaixo marcam o que a visão ainda exige além dessas fatias.

- [x] Criar interfaces do provider SDK. (`ProviderAdapter`, `InvocationService`, etc. em `services/session-core/.../provider/`)
- [x] Adicionar schema `ai-provider-profile.v1`. (`contracts/ai-provider-profile.v1.schema.json`)
- [x] Criar parser e validador YAML. (`ProviderProfileValidator`, store + hot-reload)
- [x] Implementar `secretRef` com backend `env`. (`EnvSecretResolver`)
- [ ] Implementar armazenamento seguro Windows no desktop.
- [x] Criar adaptador OpenAI-compatible genérico. (`OpenAiCompatibleAdapter`)
- [x] Criar presets Ollama e NVIDIA NIM. (`samples/ai-providers/presets-ollama-nim.example.yaml` + `providers.example.yaml`; type openai-compatible)
- [x] Implementar descoberta via `/v1/models` quando suportada. (`specs/027` — `GET /api/ai-providers/{id}/models`)
- [x] Criar teste de conexão com erros tipados. (API + UI + taxonomia de erros)
- [x] Implementar streaming e cancelamento. (`specs/026-r6-circuit-breaker-streaming/` — SSE `/invoke/stream` + cancel; sync cancel por timeout permanece)
- [x] Implementar fallback e circuit breaker. (fallback 015; circuit breaker 026 por providerId)
- [x] Criar métricas de latência, tokens e custo informado. (latência + prompt/completion/total tokens em 027; **custo USD** ainda não — não inventar)
- [x] Criar UI de provedores e modelos. (`apps/desktop-shell/src/ai-provider-panel.ts`)
- [x] Adicionar testes que garantem redação de chaves. (`SecretMaskingTest` e correlatos)
- [x] Documentar políticas de privacidade por perfil. (parcial operacional: `docs/security/provider-privacy-profiles.md` + secrets; flags YAML por perfil de conversa ainda futuros)

## Notas de higiene (2026-07-26)

015/017/026/027 cobrem a maior parte do hub. **Ainda aberto na visão 003**:
armazenamento seguro Windows (DPAPI/keyring) e custo monetário informado.
