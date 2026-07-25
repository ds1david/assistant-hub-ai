---

description: "Task list for AI Provider Hub — registro e invocação de provedores pluggable (R6)"
---

# Tasks: AI Provider Hub — registro e invocação de provedores pluggable (R6)

**Input**: Design documents from `/specs/015-issue-37-ai-provider-hub/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ai-provider-api.md, quickstart.md

**Tests**: Incluídos — a constituição (P10) exige testes automatizados determinísticos, sem GPU/hardware; a spec (SC-003, SC-005) exige que a suíte cubra invocação, teste de conexão e a taxonomia de erro contra o provedor fake, sem rede real.

**Organization**: Tarefas agrupadas por user story (US1–US5, prioridades da spec) para permitir implementação e teste independentes de cada uma. As stories têm dependência técnica real entre si (US2 expõe via API o que US1 constrói; US3 consome o transporte de US2; US4 estende o motor de invocação de US1; US5 atravessa todas) — a própria spec já documenta isso em cada "Why this priority".

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: A qual user story a tarefa pertence (US1–US5)
- Caminhos de arquivo são sempre relativos à raiz do monorepo

## Path Conventions

Extensão de dois projetos já existentes, conforme `plan.md` § Project Structure:

- Backend: `services/session-core/src/main/java/ai/assistanthub/core/provider/` (código novo) e `services/session-core/src/test/java/ai/assistanthub/core/provider/` (testes novos)
- Desktop: `apps/desktop-shell/src-tauri/src/` + `apps/desktop-shell/src/` (código novo) e `apps/desktop-shell/src-tauri/tests/` + `apps/desktop-shell/tests/` (testes novos)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar o módulo `session-core` para o novo contrato/configuração do AI Provider Hub

- [X] T001 [P] Adicionar `ai-provider-profile.v1.schema.json` ao resource copy de `contracts/` em `services/session-core/pom.xml` (mesmo padrão já usado para `transcript-event.v2.schema.json`)
- [X] T002 [P] Adicionar o bloco `session-core.ai-provider-hub.path` (`${SESSION_CORE_AI_PROVIDER_HUB_PATH:config/ai-providers.yaml}`) em `services/session-core/src/main/resources/application.yml`, seguindo o padrão já usado por `session-core.memory-hub.path` — caminho corrigido de `data/session-core/ai-providers.yaml` para `config/ai-providers.yaml` durante o Implement: o `.gitignore` já reservava esse caminho desde o bootstrap do repo (ver T003)
- [X] T003 [P] ~~Adicionar `data/session-core/ai-providers.yaml` ao `.gitignore`~~ — desnecessário: `config/ai-providers.yaml` já está coberto por uma entrada pré-existente do `.gitignore` ("AI provider local configuration and secrets", presente desde o commit de bootstrap do repo, antes desta feature existir); verificado, nenhuma edição necessária

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Tipos do perfil declarativo, validação, armazenamento e o esqueleto de adaptador/invocação de que todas as user stories dependem

**⚠️ CRITICAL**: Nenhuma user story pode ser implementada antes desta fase estar completa

- [X] T004 [P] Criar `Provider.java` (record) em `services/session-core/src/main/java/ai/assistanthub/core/provider/Provider.java` — espelha `$defs/provider` do schema v1 (data-model.md)
- [X] T005 [P] Criar `ProviderAuthentication.java` (record) em `services/session-core/src/main/java/ai/assistanthub/core/provider/ProviderAuthentication.java` — `mode`/`secretRef`/`headerName`
- [X] T006 [P] Criar `ProviderDefaults.java` (record) em `services/session-core/src/main/java/ai/assistanthub/core/provider/ProviderDefaults.java` — `model`/`temperature`/`topP`/`maxTokens`/`timeoutMs`
- [X] T007 [P] Criar `ProviderRoute.java` (record) em `services/session-core/src/main/java/ai/assistanthub/core/provider/ProviderRoute.java` — `primary`/`fallbacks`
- [X] T008 Criar `ProviderProfile.java` (record) em `services/session-core/src/main/java/ai/assistanthub/core/provider/ProviderProfile.java` — `version`/`providers`/`routes`, documento raiz (depende de T004–T007)
- [X] T009 Criar `ProviderProfileValidator.java` em `services/session-core/src/main/java/ai/assistanthub/core/provider/ProviderProfileValidator.java` — valida contra `contracts/ai-provider-profile.v1.schema.json` via `json-schema-validator`, mesmo padrão de `TranscriptEventValidator` (depende de T001, T008)
- [X] T010 Criar `ProviderProfileStore.java` em `services/session-core/src/main/java/ai/assistanthub/core/provider/ProviderProfileStore.java` — lê/escreve o YAML (`session-core.ai-provider-hub.path`), escrita atômica (arquivo temporário + rename), valida antes de persistir (depende de T002, T008, T009)
- [X] T011 Criar `ProviderRegistry.java` em `services/session-core/src/main/java/ai/assistanthub/core/provider/ProviderRegistry.java` — carrega o `ProviderProfile` vigente na subida e expõe leitura em memória, com um método de reload a partir de `ProviderProfileStore` (depende de T010)
- [X] T012 [P] Criar `InvocationErrorType.java` (enum) em `services/session-core/src/main/java/ai/assistanthub/core/provider/InvocationErrorType.java` — `AUTHENTICATION`/`MODEL_NOT_FOUND`/`TIMEOUT`/`RATE_LIMITED`/`GENERIC`
- [X] T013 [P] Criar `ConnectionTestResult.java` (record) em `services/session-core/src/main/java/ai/assistanthub/core/provider/ConnectionTestResult.java`
- [X] T014 [P] Criar `InvocationResult.java` (record) em `services/session-core/src/main/java/ai/assistanthub/core/provider/InvocationResult.java`
- [X] T015 [P] Criar `SecretPreview.java` (record) em `services/session-core/src/main/java/ai/assistanthub/core/provider/SecretPreview.java`
- [X] T016 Criar interface `ProviderAdapter.java` em `services/session-core/src/main/java/ai/assistanthub/core/provider/ProviderAdapter.java` — `testConnection(Provider)`/`invoke(Provider, request)` (depende de T012–T014)
- [X] T017 Criar `ProviderAdapterFactory.java` em `services/session-core/src/main/java/ai/assistanthub/core/provider/ProviderAdapterFactory.java` — despacha por `Provider.type()`, sem implementações concretas ainda (depende de T016)

**Checkpoint**: Perfil declarativo, validação, armazenamento e esqueleto de adaptador prontos — implementação das user stories pode começar

---

## Phase 3: User Story 1 - Registrar e invocar um provedor via configuração declarativa (Priority: P1) 🎯 MVP

**Goal**: Um perfil declarativo válido registra provedores; o Hub invoca um provedor fake e um provedor real para a capacidade `chat` no contexto de uma sessão, sem alterar código do core.

**Independent Test**: Registrar um perfil com um provedor fake habilitado, invocá-lo para `chat` no contexto de uma sessão existente, confirmar `providerId`/modelo corretos; repetir com o provedor real definido (ver Assumptions da spec).

### Tests for User Story 1 ⚠️

> Escrever estes testes primeiro; devem falhar antes da implementação abaixo

- [X] T018 [P] [US1] `ProviderProfileValidatorTest` em `services/session-core/src/test/java/ai/assistanthub/core/provider/ProviderProfileValidatorTest.java` — perfil inválido (campo obrigatório ausente, `id` duplicado, rota referenciando `id` inexistente) é rejeitado (FR-002)
- [X] T019 [P] [US1] `FakeProviderInvocationTest` em `services/session-core/src/test/java/ai/assistanthub/core/provider/FakeProviderInvocationTest.java` — perfil com provedor fake habilitado, invocação para `chat` no contexto de uma sessão, resposta atribuída ao `providerId`/modelo corretos, sem rede (FR-001/FR-004/FR-009)
- [X] T020 [P] [US1] `OpenAiCompatibleAdapterContractTest` em `services/session-core/src/test/java/ai/assistanthub/core/provider/OpenAiCompatibleAdapterContractTest.java` — contra servidor HTTP local fake (`com.sun.net.httpserver`), confirma request/response do adaptador real sem tocar rede externa

### Implementation for User Story 1

- [X] T021 [US1] Implementar `FakeProviderAdapter.java` em `services/session-core/src/main/java/ai/assistanthub/core/provider/FakeProviderAdapter.java` — determinístico, sem rede (depende de T016; faz T019 passar)
- [X] T022 [US1] Implementar `OpenAiCompatibleAdapter.java` em `services/session-core/src/main/java/ai/assistanthub/core/provider/OpenAiCompatibleAdapter.java` — `java.net.http.HttpClient` + Jackson, sem SDK de fornecedor (depende de T016; faz T020 passar)
- [X] T023 [US1] Registrar `FakeProviderAdapter`/`OpenAiCompatibleAdapter` em `ProviderAdapterFactory.java` por `Provider.type()` (depende de T017, T021, T022)
- [X] T024 [US1] Implementar `InvocationService.java` em `services/session-core/src/main/java/ai/assistanthub/core/provider/InvocationService.java` — invocação isolada por `timeoutMs` do provedor, rejeita capacidade não suportada (FR-010), retorna `InvocationResult` (depende de T011, T023, T013, T014; faz T019/T020 passarem por completo)

**Checkpoint**: User Story 1 completa e testável de forma independente — perfil declarativo registra e invoca fake e real sem tocar código do core.

---

## Phase 4: User Story 2 - Invocar e testar um provedor via API dentro de uma sessão ativa (Priority: P2)

**Goal**: Um endpoint de API testa a conexão de um provedor e invoca um provedor para uma capacidade no contexto de uma sessão ativa, sem cliente desktop.

**Independent Test**: Com o serviço rodando, chamar o endpoint de teste de conexão e o de invocação via `curl`, validando resposta e metadados de proveniência — sem cliente desktop (quickstart.md § 3).

### Tests for User Story 2 ⚠️

- [X] T025 [P] [US2] `AiProviderControllerTest` em `services/session-core/src/test/java/ai/assistanthub/core/provider/AiProviderControllerTest.java` — endpoints de listagem/CRUD/teste de conexão/invocação respondem conforme `contracts/ai-provider-api.md`, nunca expõem o segredo resolvido
- [X] T026 [P] [US2] `ProviderRegistryHotReloadTest` em `services/session-core/src/test/java/ai/assistanthub/core/provider/ProviderRegistryHotReloadTest.java` — uma mutação (criar/editar/habilitar-desabilitar) é refletida na próxima leitura do registry sem reiniciar o processo (FR-015)

### Implementation for User Story 2

- [X] T027 [US2] Adicionar métodos de mutação (`register`/`update`/`remove`/`setEnabled`) a `ProviderRegistry.java` — valida via `ProviderProfileValidator`, escreve via `ProviderProfileStore`, recarrega o estado em memória na mesma chamada (depende de T009, T010, T011; faz T026 passar)
- [X] T028 [US2] Implementar `AiProviderController.java` em `services/session-core/src/main/java/ai/assistanthub/core/provider/AiProviderController.java` — `GET/POST/PUT/PATCH/DELETE /api/ai-providers...`, `GET /{id}/secret-preview`, `POST /{id}/test`, `POST /invoke` conforme `contracts/ai-provider-api.md` (depende de T027, T024, T021, T022, T013, T014, T015; faz T025 passar)

**Checkpoint**: User Story 2 completa e testável de forma independente — caminho fim a fim via API, sem UI.

---

## Phase 5: User Story 3 - Configurar e testar provedores pela UI do desktop (Priority: P2)

**Goal**: Uma tela no shell desktop cadastra, edita, habilita/desabilita e testa provedores, mascarando qualquer segredo, sem editar arquivos manualmente.

**Independent Test**: Na aplicação desktop, adicionar um provedor fake, disparar o teste de conexão, confirmar visualmente sucesso/erro tipado e que a chave aparece só mascarada.

### Tests for User Story 3 ⚠️

- [X] T029 [P] [US3] `ai_provider_client_tests.rs` em `apps/desktop-shell/src-tauri/tests/ai_provider_client_tests.rs` — parsing/mapeamento dos novos tipos contra um servidor HTTP fake local, mesmo padrão de `session_core_client_tests.rs`
- [X] T030 [P] [US3] `ai-provider-panel.test.ts` em `apps/desktop-shell/tests/ai-provider-panel.test.ts` — a UI nunca renderiza um segredo completo; os cinco `InvocationErrorType` aparecem distintos no estado de erro do teste de conexão

### Implementation for User Story 3

- [X] T031 [US3] Criar `ai_provider_client.rs` em `apps/desktop-shell/src-tauri/src/ai_provider_client.rs` — cliente puro para os endpoints de `contracts/ai-provider-api.md`, mesmo padrão de `session_core_client.rs` (depende de T028; faz T029 passar)
- [X] T032 [US3] Registrar `pub mod ai_provider_client;` em `apps/desktop-shell/src-tauri/src/lib.rs` e os comandos Tauri novos (`list_ai_providers`, `save_ai_provider`, `set_ai_provider_enabled`, `delete_ai_provider`, `get_ai_provider_secret_preview`, `test_ai_provider_connection`, `invoke_ai_provider`) em `apps/desktop-shell/src-tauri/src/main.rs` (depende de T031)
- [X] T033 [US3] Adicionar tipos e wrappers (`listAiProviders`, `saveAiProvider`, `testAiProviderConnection`, `invokeAiProvider`, etc.) em `apps/desktop-shell/src/api-client.ts`, mesmo estilo camelCase já usado (depende de T032)
- [X] T034 [US3] Implementar `ai-provider-panel.ts` em `apps/desktop-shell/src/ai-provider-panel.ts` — lista provedores, formulário de cadastro/edição, alternância habilitado/desabilitado, botão de teste de conexão com erro tipado, exibição de segredo só via prévia mascarada (depende de T033; faz T030 passar)
- [X] T035 [US3] Integrar `ai-provider-panel.ts` como painel/aba novo em `apps/desktop-shell/src/main.ts` (depende de T034)

**Checkpoint**: User Story 3 completa e testável de forma independente — cadastro/edição/teste de provedor inteiramente pela UI desktop.

---

## Phase 6: User Story 4 - Falha de um provedor não derruba a sessão, e fallback obedece a política (Priority: P3)

**Goal**: Timeout, erro ou rate limit de um provedor aciona fallback só quando a rota tiver um configurado; provedor `enabled: false` nunca é invocado; o session-core nunca cai.

**Independent Test**: Forçar o provedor fake a expirar/errar/retornar rate limit e confirmar isolamento, fallback condicional e erro tipado quando não há fallback.

### Tests for User Story 4 ⚠️

- [X] T036 [P] [US4] `InvocationTimeoutAndFallbackTest` em `services/session-core/src/test/java/ai/assistanthub/core/provider/InvocationTimeoutAndFallbackTest.java` — timeout/erro/rate-limit aciona fallback quando configurado; rota sem fallback retorna erro tipado; provedor `enabled: false` nunca é chamado (FR-005)
- [X] T037 [P] [US4] `InvocationErrorTaxonomyTest` em `services/session-core/src/test/java/ai/assistanthub/core/provider/InvocationErrorTaxonomyTest.java` — autenticação, modelo inexistente, timeout, rate limit e capacidade incompatível retornam tipos distintos, nunca um genérico ambíguo (FR-006/FR-010/SC-005)

### Implementation for User Story 4

- [X] T038 [US4] ~~Estender~~ `InvocationService.java` já implementado com fallback ordenado, exclusão `enabled: false` e isolamento de falha desde T024 (o loop de fallback foi construído de uma vez, não em duas passagens) — T036 confirma o comportamento
- [X] T039 [US4] ~~Estender~~ `OpenAiCompatibleAdapter.java` já implementado com o mapeamento completo de status HTTP desde T022 — T037 confirma o comportamento

**Checkpoint**: User Story 4 completa e testável de forma independente — isolamento, fallback e taxonomia de erro completos.

---

## Phase 7: User Story 5 - Segredos de provedores nunca vazam (Priority: P4)

**Goal**: O segredo resolvido nunca aparece em log, métrica, resposta de API, export ou UI — só uma prévia mascarada, quando aplicável.

**Independent Test**: Configurar um provedor com `secretRef`, invocar/testar, inspecionar logs/respostas/exports e confirmar ausência do valor bruto; UI mostra só prefixo/sufixo mascarado.

### Tests for User Story 5 ⚠️

- [X] T040 [P] [US5] `SecretMaskingTest` em `services/session-core/src/test/java/ai/assistanthub/core/provider/SecretMaskingTest.java` — segredo resolvido nunca aparece em log, resposta de `AiProviderController` ou export (FR-007/FR-014/SC-004)

### Implementation for User Story 5

- [X] T041 [US5] ~~Criar~~ `SecretResolver.java` já criado durante T022 (o adaptador real precisava da interface para compilar) (depende de T005)
- [X] T042 [US5] ~~Implementar~~ `EnvSecretResolver.java` já implementado durante T022 (depende de T041)
- [X] T043 [US5] ~~Integrar~~ `SecretResolver` já integrado em `OpenAiCompatibleAdapter.java` desde T022 (depende de T022, T042; T040 confirma)
- [X] T044 [US5] ~~Implementar~~ geração de `SecretPreview` já implementada em `AiProviderController.java` desde T028 (depende de T028, T042)
- [X] T045 [US5] Adicionar o log estruturado por invocação em `InvocationService.java` (research.md Decisão 7) — só `providerId`/`model`/`capability`/`sessionId`/`channelId`/`latencyMs`/resultado, nunca segredo/output/message (depende de T024, T038; T040 confirma) — gap real encontrado no Implement: T038 não tinha criado o log ainda, só a lógica de invocação
- [X] T046 [US5] ~~Ajustar~~ `ai-provider-panel.ts` já implementado desde T034 para exibir segredo só via `get_ai_provider_secret_preview` (depende de T034, T044)

**Checkpoint**: User Story 5 completa e testável de forma independente — segredo nunca sai do processo Java, mascarado ponta a ponta (API + UI).

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Garantias que atravessam todas as user stories

- [X] T047 [P] Revisar `InvocationService.java`, `AiProviderController.java` e `ai-provider-panel.ts` para confirmar que nenhum log/resposta/tela imprime o valor resolvido de um segredo (P9) — auditoria via `grep` confirmou nenhuma ocorrência suspeita, além de `SecretMaskingTest` (T040)
- [X] T048 [P] Confirmar ausência de SDK de fornecedor de IA e de dependência de GPU/hardware em `services/session-core/src/main/java/ai/assistanthub/core/provider/` e nos testes correspondentes (P2/P10, quickstart.md § 5) — `grep` confirmou nenhuma referência
- [X] T049 Executar o roteiro de `specs/015-issue-37-ai-provider-hub/quickstart.md` — `mvn -pl services/session-core test`: 54/54 verdes; `cargo test` (desktop-shell): 33/33 verdes; `npx vitest run`: 20/20 verdes; `npx tsc -b`: sem erros; `npx eslint`: sem erros; validação manual via `curl` contra o serviço real rodando (porta 8099): create/list/test-connection/secret-preview/PATCH enabled/DELETE (rejeitado por `minItems:1`)/invoke sem rota (404) todos com o comportamento esperado, hot-reload confirmado sem reiniciar o processo — todos os 7 critérios de sucesso (SC-001 a SC-007) confirmados

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: Depende da conclusão do Setup — BLOQUEIA todas as user stories
- **User Story 1 (Phase 3)**: Depende do Foundational — sem dependência de outra story
- **User Story 2 (Phase 4)**: Depende do Foundational e reaproveita `InvocationService`/adaptadores de US1 (T021–T024) para o teste de conexão e a invocação via API — só é testável de forma independente depois de US1 completa
- **User Story 3 (Phase 5)**: Depende do endpoint de API de US2 (T028) como camada de transporte — não é testável sem US2 completa
- **User Story 4 (Phase 6)**: Estende o `InvocationService`/`OpenAiCompatibleAdapter` de US1 (T024/T022) — testável de forma independente assim que US1 estiver completa, mas conceitualmente uma evolução dela
- **User Story 5 (Phase 7)**: Atravessa US1 (adaptador), US2 (controller) e US3 (UI) — só é auditável por completo depois que as três existirem
- **Polish (Phase 8)**: Depende de todas as user stories desejadas estarem completas

### Within Each User Story

- Testes escritos e falhando antes da implementação
- Registros de dados (Foundational) antes de validação/armazenamento antes de registry antes de adaptadores antes de invocação
- Story completa antes de avançar para a próxima prioridade

### Parallel Opportunities

- T001–T003 (Setup) podem rodar em paralelo
- T004–T007 (records de Foundational) podem rodar em paralelo entre si; T012–T015 (tipos de resultado) também, e em paralelo com T004–T007
- T018–T020 (testes de US1) podem rodar em paralelo entre si
- T021 e T022 (adaptadores de US1) podem rodar em paralelo — arquivos diferentes, ambos dependem só de T016/T017
- T025 e T026 (testes de US2) podem rodar em paralelo
- T029 e T030 (testes de US3) podem rodar em paralelo
- T036 e T037 (testes de US4) podem rodar em paralelo
- T047 e T048 (Polish) podem rodar em paralelo entre si e com T049

---

## Parallel Example: User Story 1

```bash
# Testes de User Story 1 em paralelo:
Task: "ProviderProfileValidatorTest em services/session-core/src/test/java/ai/assistanthub/core/provider/ProviderProfileValidatorTest.java"
Task: "FakeProviderInvocationTest em services/session-core/src/test/java/ai/assistanthub/core/provider/FakeProviderInvocationTest.java"
Task: "OpenAiCompatibleAdapterContractTest em services/session-core/src/test/java/ai/assistanthub/core/provider/OpenAiCompatibleAdapterContractTest.java"

# Adaptadores de User Story 1 em paralelo:
Task: "FakeProviderAdapter em services/session-core/src/main/java/ai/assistanthub/core/provider/FakeProviderAdapter.java"
Task: "OpenAiCompatibleAdapter em services/session-core/src/main/java/ai/assistanthub/core/provider/OpenAiCompatibleAdapter.java"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRÍTICO — bloqueia todas as stories)
3. Completar Phase 3: User Story 1
4. **PARAR e VALIDAR**: perfil declarativo registra e invoca fake + real, sem código do core alterado
5. Já entrega o núcleo pedido pela issue #37: registro + invocação isolada

### Incremental Delivery

1. Setup + Foundational → base pronta
2. User Story 1 → validar independentemente → MVP do AI Provider Hub (registro + invocação)
3. User Story 2 → validar independentemente → caminho fim a fim via API
4. User Story 3 → validar independentemente → caminho fim a fim via UI desktop
5. User Story 4 → validar independentemente → isolamento de falha e fallback completos
6. User Story 5 → validar independentemente → segredo nunca vaza, ponta a ponta
7. Cada story agrega valor sem quebrar as anteriores

---

## Notes

- [P] tasks = arquivos diferentes, sem dependência entre si
- Rótulo [Story] mapeia a tarefa à user story correspondente para rastreabilidade
- Verificar que os testes falham antes de implementar
- Fazer commit após cada tarefa ou grupo lógico
- Parar em cada checkpoint para validar a story de forma independente
- Nenhuma tarefa altera `contracts/ai-provider-profile.v1.schema.json` (P4) — o perfil é consumido como está
- Nenhuma tarefa introduz SDK de fornecedor de IA (P2) — só HTTP genérico (research.md Decisão 1)
