# Quickstart: validar AI Provider Hub — registro e invocação (R6)

Guia de validação end-to-end. A suíte automatizada padrão roda inteira no WSL, sem GPU, sem hardware de áudio e sem rede externa (P10/P3/SC-003). Referências: [data-model.md](./data-model.md) (entidades), [contracts/ai-provider-api.md](./contracts/ai-provider-api.md) (endpoints/comandos), [research.md](./research.md) (decisões).

## Pré-requisitos

- Ambiente WSL com Java 21 e Maven já configurados via SDKMAN (`sdk current`).
- Módulo `services/session-core` compilando na branch `015-issue-37-ai-provider-hub`.
- Node/Rust já configurados para `apps/desktop-shell` (mesmo setup usado por `specs/014`).
- Nenhuma credencial de provedor real é necessária para a suíte padrão.

## 1. Rodar a suíte de testes automatizados do backend

```bash
mvn -pl services/session-core -am test
```

**Esperado**: todos os testes de `ai.assistanthub.core.provider` passam, incluindo:

- `ProviderProfileValidatorTest` (FR-002) — perfil inválido (campo obrigatório ausente, `id` duplicado, referência de rota a `id` inexistente) é rejeitado antes de qualquer invocação.
- `ProviderRegistryHotReloadTest` (FR-015) — uma mutação via API é refletida na próxima leitura do registry sem reiniciar o processo.
- `FakeProviderInvocationTest` (US1) — perfil com provedor fake habilitado, invocação para capacidade `chat` no contexto de uma sessão, resposta atribuída ao `providerId`/modelo corretos.
- `InvocationTimeoutAndFallbackTest` (US4) — timeout aciona fallback quando configurado; rota sem fallback retorna erro tipado; provedor `enabled: false` nunca é chamado; rate limit também aciona fallback.
- `InvocationErrorTaxonomyTest` (FR-006/FR-010) — autenticação, modelo inexistente, timeout, rate limit e capacidade incompatível retornam tipos de erro distintos, nunca um genérico ambíguo.
- `SecretMaskingTest` (US5) — nenhuma resposta de API, log ou export contém o valor bruto do segredo; `SecretPreview` só mostra prefixo/sufixo.
- `AiProviderControllerTest` (US2) — endpoints de teste de conexão e invocação respondem via API, sem cliente desktop.
- `OpenAiCompatibleAdapterContractTest` — contra servidor HTTP local fake (`com.sun.net.httpserver`), sem rede real.

## 2. Rodar a suíte automatizada do desktop

```bash
cd apps/desktop-shell
cargo test --manifest-path src-tauri/Cargo.toml
npm test
```

**Esperado**: `ai_provider_client_tests.rs` valida parsing/mapeamento contra um servidor HTTP fake local (sem tocar `session-core` real); `ai-provider-panel.test.ts` valida que a UI nunca renderiza um segredo completo e que os cinco tipos de erro (`InvocationErrorType`) aparecem distintos na tela de teste de conexão.

## 3. Validação manual do fluxo via API (opcional, end-to-end)

```bash
# Sobe o serviço com um perfil de teste isolado
SESSION_CORE_AI_PROVIDER_HUB_PATH=/tmp/ai-providers-quickstart.yaml \
  mvn -pl services/session-core spring-boot:run &

# Registra um provedor fake habilitado
curl -s -X POST http://localhost:8080/api/ai-providers -H 'Content-Type: application/json' \
  -d '{"id":"fake-1","label":"Fake","type":"openai-compatible","enabled":true,"baseUrl":"http://fake.invalid","authentication":{"mode":"none"},"defaults":{"model":"fake-model","timeoutMs":5000},"capabilities":["chat"]}'

# Testa a conexão (sem sair do processo, sem rede real para o fake)
curl -s -X POST http://localhost:8080/api/ai-providers/fake-1/test

# Cria uma sessão (API já existente) e invoca o provedor no contexto dela
SESSION_ID=$(curl -s -X POST http://localhost:8080/api/sessions -H 'Content-Type: application/json' \
  -d '{"title":"quickstart","profileId":"demo","metadata":{}}' | jq -r .id)

curl -s -X POST http://localhost:8080/api/ai-providers/invoke -H 'Content-Type: application/json' \
  -d "{\"sessionId\":\"$SESSION_ID\",\"route\":\"live-answer\",\"capability\":\"chat\",\"input\":\"ola\"}"
```

**Esperado**: teste de conexão e invocação retornam sucesso atribuído a `fake-1`; nenhuma etapa exige reiniciar o processo entre o cadastro e o uso do provedor (SC-006/FR-015).

## 4. Confirmar que segredos nunca aparecem em log

```bash
export SESSION_CORE_TEST_SECRET=super-secreto-nao-deve-vazar
grep -ril "$SESSION_CORE_TEST_SECRET" services/session-core/target/surefire-reports/ 2>/dev/null || echo "OK: nenhuma ocorrência"
```

**Esperado**: `OK: nenhuma ocorrência` — confirma SC-004.

## 5. Confirmar ausência de dependência de GPU/hardware/SDK de fornecedor

```bash
grep -ril "cuda\|gpu\|wasapi\|com.openai\|com.google.genai" services/session-core/src/main/java/ai/assistanthub/core/provider/ services/session-core/src/test/java/ai/assistanthub/core/provider/ || echo "OK: nenhuma referência"
```

**Esperado**: `OK: nenhuma referência` — confirma P2/P10.

## Critérios de sucesso mapeados

| Critério | Como este quickstart valida |
|---|---|
| SC-001 (registrar/invocar provedor OpenAI-compatible só por config) | Passo 1 (`FakeProviderInvocationTest`) e Passo 3 (manual) |
| SC-002 (falha isolada, sessão não cai) | Passo 1 (`InvocationTimeoutAndFallbackTest`) |
| SC-003 (testes contra fake, sem rede/credencial real) | Passo 1 inteiro roda sem rede; Passo 5 confirma ausência de SDK de fornecedor |
| SC-004 (segredo nunca em log/métrica/API/export) | Passo 1 (`SecretMaskingTest`) e Passo 4 |
| SC-005 (auth/modelo/timeout/rate-limit distintos) | Passo 1 (`InvocationErrorTaxonomyTest`) |
| SC-006 (cadastro/teste/uso só pela UI desktop) | Passo 2 (`ai-provider-panel.test.ts`) — cobertura de lógica; fluxo visual completo fica para validação manual em `docs/validation/` na integração com `specs/014` |
| SC-007 (teste/invocação só via API, sem desktop) | Passo 3 (manual, só `curl`) |
