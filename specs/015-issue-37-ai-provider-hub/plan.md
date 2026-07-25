# Implementation Plan: AI Provider Hub — registro e invocação de provedores pluggable (R6)

**Branch**: `015-issue-37-ai-provider-hub` | **Date**: 2026-07-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-issue-37-ai-provider-hub/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Hoje não existe nenhum caminho para invocar um provedor de IA a partir de uma sessão do Assistant Hub AI — o contrato `ai-provider-profile.v1` e o ADR-0010 já existem, mas nada os consome. Esta feature adiciona ao `session-core` já existente um registro de provedores declarativo (arquivo YAML validado contra o schema v1, hot-reload sem restart), um motor de invocação isolado por timeout com fallback e taxonomia de erro tipada (autenticação/modelo/timeout/rate-limit/genérico), um endpoint REST para testar conexão e invocar um provedor dentro do contexto de uma sessão ativa, e — por decisão da clarificação — uma tela nova no shell desktop (`apps/desktop-shell`) para cadastrar, editar, habilitar/desabilitar e testar provedores, sempre mascarando segredos e nunca lendo `secretRef` resolvido fora do processo Java. Um adaptador fake (determinístico, sem rede) e um adaptador real `openai-compatible` (cobre Ollama e, se escolhido, OpenAI/GPT) satisfazem "1 provider real + 1 fake" da issue #37.

## Technical Context

**Language/Version**: Backend — Java 21 (Spring Boot 3.5.3), extensão do módulo Maven já existente `services/session-core`. Desktop — Rust 1.75+ (núcleo Tauri 2) + TypeScript 5 (webview via Vite), extensão do app já existente `apps/desktop-shell` (`specs/014-issue-35-desktop-tauri-shell-local/`).

**Primary Dependencies**: Nenhuma dependência nova de SDK de provedor de IA (P2) — o adaptador real usa `java.net.http.HttpClient` (JDK 21, já disponível) + Jackson (já transitivo via `spring-boot-starter-web`) para falar HTTP genérico com qualquer endpoint `openai-compatible`. Validação do perfil reaproveita `com.networknt:json-schema-validator` (já dependência do módulo, hoje usada por `TranscriptEventValidator`) contra `contracts/ai-provider-profile.v1.schema.json`. Parsing do arquivo YAML do perfil reaproveita SnakeYAML (já transitivo via Spring Boot, usado para `application.yml`). Lado desktop reaproveita `reqwest` (já dependência de `src-tauri/Cargo.toml`), no mesmo padrão de `session_core_client.rs` — nenhuma chamada de rede sai do webview.

**Storage**: Perfil de provedores em um arquivo YAML local (`config/ai-providers.yaml`, caminho configurável — já coberto pela entrada pré-existente de `.gitignore` "AI provider local configuration and secrets", desde o bootstrap do repo), validado contra o schema v1 a cada carga/escrita — é a fonte de verdade declarativa, nunca contém segredo resolvido (só `secretRef`). Um `ProviderRegistry` em memória é recarregado a cada escrita bem-sucedida (via API/UI ou edição manual do arquivo), sem reiniciar o processo (FR-015). Não reaproveita o SQLite do Memory Hub (`specs/013-issue-29-memory-hub-persistence/`) — são domínios de dado distintos (configuração declarativa vs. sessão/eventos), e um arquivo YAML mantém a natureza "perfil declarativo" já usada em `samples/ai-providers/providers.example.yaml` e o caminho de importação/exportação futuro de `specs/003-ai-provider-hub/`. Métricas por invocação (FR-008) são registradas como log estruturado (SLF4J), não uma tabela nova — ver research.md Decisão 7.

**Testing**: JUnit 5 + `spring-boot-starter-test` (padrão já usado no módulo). O adaptador fake é testado em processo, sem rede. O adaptador real (`openai-compatible`) é testado contra um servidor HTTP fake local (`com.sun.net.httpserver.HttpServer`, já na JDK, zero dependência nova) para toda a lógica de timeout/erro/fallback — determinístico, sem rede real (P10/SC-003). Um teste de integração contra o provedor remoto real de referência é opcional/tag-gated (`@Tag("real-provider")`), pulado por padrão e só executado com a credencial configurada via variável de ambiente — não entra na suíte padrão do WSL. Desktop: `cargo test` para `ai_provider_client.rs` (mesmo padrão de `session_core_client_tests.rs`, servidor HTTP fake local) e `vitest` para a lógica de máscara de segredo/estado de erro do painel (`ai-provider-panel.ts`).

**Target Platform**: Backend — mesmo serviço Linux (WSL/Docker, ADR-0005) do `session-core` hoje. Desktop — Windows 10/11 x64 com WebView2 (mesmo alvo de `specs/014`); a lib Rust (`ai_provider_client`) é testável no WSL sem GUI, o binário Tauri completo continua exigindo toolchain Windows.

**Project Type**: Extensão de dois projetos já existentes — `services/session-core` (Maven) e `apps/desktop-shell` (Tauri). Nenhum serviço ou app novo é criado.

**Performance Goals**: Sem SLA numérico novo além do já implícito no contrato v1 (`timeoutMs` entre 1000–600000ms por provedor, FR-003). Teste de conexão e invocação via API devem responder dentro do `timeoutMs` configurado do provedor mais eventual tempo de fallback, sem introduzir latência adicional perceptível na UI desktop além de uma chamada HTTP local ao `session-core`.

**Constraints**: Nenhum SDK de provedor externo importado (P2); segredo resolvido nunca sai do processo Java — nem em log, métrica, resposta de API, export ou UI (P9/FR-007/FR-014); mudança de perfil aplicada sem reiniciar o processo (FR-015); testes automatizados sem GPU/hardware físico e sem depender de credencial paga por padrão (P10/SC-003); WSL-first — nenhuma parte obrigatória do fluxo de teste padrão exige rede externa (P3); UI desktop nunca acessa `session-core` diretamente do webview, só via comando Tauri (regra já registrada no `plan.md` de `specs/014`).

**Scale/Scope**: Um pacote novo `provider` em `services/session-core` (registro, validação, invocação, dois adaptadores, controller REST); um cliente novo (`ai_provider_client.rs`) + uma tela nova (`ai-provider-panel.ts`) em `apps/desktop-shell`; nenhuma tabela de banco nova; nenhum serviço novo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|---|---|
| P1 — Especificação antes de código | PASS. `spec.md` cobre requisitos, critérios de aceite e fora de escopo, com `/speckit-clarify` concluído (4 perguntas de alto impacto resolvidas) e checklist de qualidade 16/16; gate humano G1 (Spec) segue pendente de confirmação explícita antes do Implement. |
| P2 — Core independente de fornecedores | PASS com atenção. Nenhum SDK de provedor (OpenAI, Google GenAI etc.) é importado — só HTTP genérico + Jackson (Technical Context/research.md Decisão 1). Atenção a manter essa disciplina durante o Implement: é a tentação mais provável de violação desta feature. |
| P3 — WSL-first, Windows quando necessário | PASS. Backend Java/Maven/testes continuam no WSL; o teste do adaptador real contra a rede é opcional/tag-gated, não bloqueia a suíte padrão no WSL. Desktop segue o padrão já aceito em `specs/014` (lib Rust testável no WSL, binário Tauri completo exige Windows). |
| P4 — Contratos versionados | PASS. Reaproveita `contracts/ai-provider-profile.v1.schema.json` sem alteração (FR-002); nenhum campo novo é introduzido no schema raiz do monorepo. As novas interfaces REST/Tauri desta feature são documentadas em `contracts/ai-provider-api.md` (interno à feature, mesmo nível de formalidade que `SessionController` hoje — não é um contrato entre serviços externos). |
| P5 — Separação por canal e origem | PASS. Toda invocação carrega `sessionId`/`channelId`/`sourceType` do contexto da sessão (FR-004) até o log de métrica (FR-008), sem misturar canais nem sessões entre chamadas concorrentes (Edge Cases da spec). |
| P6 — Isolamento de endpoint de áudio | N/A. Feature não toca captura de áudio nem WASAPI/COM. |
| P7 — Identidade de dispositivo | N/A. Feature não seleciona nem resolve dispositivo de áudio. |
| P8 — Automação com autorização | PASS. Nenhum merge, force-push ou fechamento de issue automatizado é proposto por este plano. |
| P9 — Privacidade por padrão | PASS com atenção — é o maior risco desta feature. `SecretResolver` nunca loga o valor resolvido; `AiProviderController` nunca retorna o segredo resolvido em nenhuma resposta (só `secretRef`, que não é sensível); a UI só recebe uma prévia mascarada gerada no servidor (FR-014); o arquivo `config/ai-providers.yaml` já é ignorado pelo `.gitignore` desde o bootstrap do repo (é estado de runtime mutável via API/UI, não fonte versionada — paralelo ao `memory-hub.db`), mesmo sem conter segredo bruto. |
| P10 — Qualidade determinística | PASS com atenção. Adaptador fake e testes do adaptador real usam servidor HTTP local (`com.sun.net.httpserver`) — determinístico, sem GPU/hardware/rede real. O único teste que toca rede real (adaptador remoto de referência) é opcional/tag-gated e não roda por padrão, evitando exigir credencial paga em CI. |

Nenhuma violação exige entrada em Complexity Tracking — os dois pontos "com atenção" (P2, P9) são riscos a vigiar durante o Implement, não desvios arquiteturais que precisem de justificativa.

## Project Structure

### Documentation (this feature)

```text
specs/015-issue-37-ai-provider-hub/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── ai-provider-api.md   # Phase 1 output — endpoints REST + comandos Tauri novos
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
services/session-core/
├── src/main/java/ai/assistanthub/core/
│   ├── provider/                                  # novo — AI Provider Hub (R6, issue #37)
│   │   ├── Provider.java                          # record — espelha $defs/provider do schema v1
│   │   ├── ProviderAuthentication.java             # record — mode/secretRef/headerName
│   │   ├── ProviderDefaults.java                   # record — model/temperature/topP/maxTokens/timeoutMs
│   │   ├── ProviderRoute.java                       # record — primary/fallbacks
│   │   ├── ProviderProfile.java                     # record — version/providers/routes (documento raiz)
│   │   ├── ProviderProfileValidator.java            # valida contra contracts/ai-provider-profile.v1.schema.json
│   │   │                                             # (mesmo padrão de transcript/TranscriptEventValidator.java)
│   │   ├── ProviderProfileStore.java                # lê/escreve o YAML (config/ai-providers.yaml),
│   │   │                                             # escrita atômica (arquivo temp + rename)
│   │   ├── ProviderRegistry.java                    # estado em memória, recarregado a cada escrita (FR-015)
│   │   ├── SecretResolver.java                      # interface — resolve secretRef sem nunca logar o valor
│   │   ├── EnvSecretResolver.java                   # impl WSL/dev — secretRef env:VAR (docs/security/provider-secrets.md)
│   │   ├── ProviderAdapter.java                     # interface — testConnection(Provider) / invoke(Provider, req)
│   │   ├── OpenAiCompatibleAdapter.java              # impl real (type=openai-compatible) — Ollama/GPT/NIM/custom
│   │   ├── FakeProviderAdapter.java                  # impl fake — determinística, sem rede (FR-009/SC-003)
│   │   ├── ProviderAdapterFactory.java               # despacha por Provider.type()
│   │   ├── InvocationService.java                   # timeout isolado + fallback + rate-limit (FR-003/FR-005/FR-015)
│   │   ├── InvocationErrorType.java                  # enum AUTHENTICATION/MODEL_NOT_FOUND/TIMEOUT/RATE_LIMITED/GENERIC
│   │   ├── InvocationResult.java                     # record — resultado tipado de uma invocação
│   │   ├── ConnectionTestResult.java                 # record — resultado tipado de um teste de conexão
│   │   ├── SecretPreview.java                        # record — prévia mascarada (nunca o valor completo, FR-014)
│   │   └── AiProviderController.java                 # REST /api/ai-providers/... (ver contracts/ai-provider-api.md)
│   ├── session/                                       # existente, sem mudança de API pública
│   ├── memory/                                        # existente (specs/013), sem mudança
│   └── transcript/                                     # existente, sem mudança de contrato
├── src/main/resources/application.yml                  # + session-core.ai-provider-hub.path (SESSION_CORE_AI_PROVIDER_HUB_PATH)
├── pom.xml                                              # resource copy passa a incluir também
│                                                          # ai-provider-profile.v1.schema.json (mesmo padrão do v2 de transcript)
└── src/test/java/ai/assistanthub/core/provider/
    ├── ProviderProfileValidatorTest.java                # FR-002 — perfil inválido rejeitado, id duplicado
    ├── ProviderRegistryHotReloadTest.java                # FR-015 — mudança aplicada sem reiniciar
    ├── FakeProviderInvocationTest.java                    # US1 — invocação fim a fim sem rede
    ├── InvocationTimeoutAndFallbackTest.java               # US4 — timeout/fallback/rate-limit/enabled=false
    ├── InvocationErrorTaxonomyTest.java                     # FR-006/FR-010 — auth/modelo/timeout/rate-limit/genérico/capacidade
    ├── SecretMaskingTest.java                               # US5 — segredo nunca aparece em log/resposta/export
    ├── AiProviderControllerTest.java                        # US2 — endpoints de teste/invocação via API
    └── OpenAiCompatibleAdapterContractTest.java              # contra HttpServer local fake (sem rede real)

.gitignore                                               # config/ai-providers.yaml já coberto (entrada pré-existente do bootstrap)

apps/desktop-shell/
├── src-tauri/src/
│   ├── ai_provider_client.rs                           # novo — cliente puro para os novos endpoints REST
│   │                                                     # (mesmo padrão de session_core_client.rs — só GET/POST tipados)
│   ├── lib.rs                                           # + pub mod ai_provider_client;
│   └── main.rs                                          # + registro dos novos comandos Tauri (mesmo padrão já existente)
├── src-tauri/tests/
│   └── ai_provider_client_tests.rs                       # parsing/mapeamento contra servidor HTTP fake local
├── src/
│   ├── ai-provider-panel.ts                              # novo — tela de configuração/teste de provedores (US3)
│   └── api-client.ts                                     # + wrappers list/save/test/invoke de provedores
└── tests/
    └── ai-provider-panel.test.ts                          # vitest — máscara de segredo e estados de erro tipados
```

**Structure Decision**: Extensão de dois módulos já existentes, sem novo serviço/app. No backend, todo o código novo entra em um pacote irmão (`provider`) aos pacotes `session`/`memory`/`transcript` já existentes em `services/session-core`, seguindo o mesmo estilo direto (sem ORM, sem SDK de fornecedor) já usado pelo módulo. No desktop, a UI de provedores segue exatamente o padrão já estabelecido em `specs/014-issue-35-desktop-tauri-shell-local/plan.md`: todo acesso de rede sai do processo Rust via comando Tauri, nunca do webview — `ai_provider_client.rs` é o único ponto que fala HTTP com o `session-core`, espelhando `session_core_client.rs`. `specs/014` havia explicitamente marcado "AI Provider Hub fora de escopo" (seu FR-013); esta feature é o retorno planejado a esse ponto, sem alterar nada do que `specs/014` já entregou. `contracts/ai-provider-api.md` documenta as interfaces novas (REST + Tauri) no mesmo nível de formalidade que o restante do projeto usa para `SessionController` (código como contrato, não OpenAPI) — o único contrato JSON Schema formal continua sendo `ai-provider-profile.v1.schema.json`, já existente e não alterado.

## Complexity Tracking

*Não se aplica — nenhuma violação de Constitution Check identificada.*
