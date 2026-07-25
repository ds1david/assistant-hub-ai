# Implementation Plan: Consistência de origem (`sourceType`) em resultados de invocação de IA

**Branch**: `017-issue-40-invocation-sourcetype` | **Date**: 2026-07-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/017-issue-40-invocation-sourcetype/spec.md` (issue #40; clarifications 2026-07-25)

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Fechar o débito **`InvocationResult-sourceType`** (#40): o resultado de `POST /api/ai-providers/invoke` deve ecoar a **origem canônica do canal** (`microphone` \| `system`) resolvida **somente no servidor** a partir de `HubEvent.correlation` já gravado na sessão; o chamador **não** envia `sourceType`. Sem canal → `sourceType` nulo (N/A). Com canal sem evidência / não canônico / conflito → **422** antes do loop de provedores. Log estruturado e clientes desktop recebem o campo de forma **aditiva**. Abordagem: `ChannelOriginResolver` + extensão de `InvocationResult` / `InvocationService` / handlers + testes determinísticos no `session-core` (e espelho de tipos no desktop).

Detalhes de decisão: [research.md](./research.md). Modelo: [data-model.md](./data-model.md). Contrato: [contracts/invocation-result-sourcetype.md](./contracts/invocation-result-sourcetype.md).

## Technical Context

**Language/Version**: Java 21 (session-core / Maven); TypeScript + Rust (desktop-shell, espelho aditivo de tipos apenas).

**Primary Dependencies**: Spring Boot (`session-core`), SLF4J, SDK `ai.assistanthub.sdk.HubEvent`, Memory Hub / `SessionRepository` (já existentes). Sem novo adaptador de provedor.

**Storage**: Somente leitura de eventos de sessão já persistidos/cacheados (`SessionRepository` + SQLite Memory Hub). Sem migração de schema, sem nova tabela de canais.

**Testing**: JUnit 5 + AssertJ em `services/session-core` (unit/contrato do resolvedor e invoke). Opcional: vitest/cargo para tipos desktop. Sem GPU/hardware (P10).

**Target Platform**: WSL para build/testes Java; desktop types opcionais no mesmo monorepo.

**Project Type**: Débito de consistência de contrato no serviço de domínio `session-core` (hub de provedores + contexto de sessão), com espelho de DTO no shell desktop.

**Performance Goals**: Resolução de origem é O(n) nos eventos da sessão (n tipicamente pequeno em sessões interativas); não altera metas de timeout de provedor. SC-001–SC-003: cobertura 100% dos cenários de teste, zero contaminação multi-canal.

**Constraints**: Constituição P5 (origem ponta a ponta); P4 aditivo; P9 sem logar output/segredos; P1/G1 spec já clarificada; fail-closed em origem inválida; não acionar fallback de rota em falha de origem; não expandir vocabulário de `sourceType`.

**Scale/Scope**: ~1 serviço Java + testes; 2 arquivos de tipo desktop; 1 contrato feature-local; tracking issue #40 / changelog. Sem feature de domínio nova, sem agent Windows, sem transcription-service.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|-----------|-----------|
| P1 — Spec antes de código | PASS. Spec + 5 clarificações + checklist 16/16; implementação ainda não iniciada. G1 humano antes de Implement. |
| P2 — Core independente de fornecedores | PASS. Nenhuma dependência nova de LLM/STT; fake/openai-compatible inalterados. |
| P3 — WSL-first | PASS. Java/Maven/testes no WSL; sem captura WASAPI nesta fatia. |
| P4 — Contratos versionados | PASS. Campo aditivo em resultado; contrato documentado em `contracts/`; transcript schema intocado; preferência aditiva na entrada. |
| P5 — Canal/origem | PASS. Objetivo da fatia: ecoar `sourceType` no resultado e no log a partir do contexto de sessão. |
| P6 — Isolamento áudio | N/A. |
| P7 — Identidade dispositivo | N/A. |
| P8 — Automação com autorização | PASS. Plano não automatiza merge/close de issue; FR-009 é tracking humano. |
| P9 — Privacidade | PASS. Log sem output/message/segredos (FR-012). |
| P10 — Qualidade determinística | PASS. Testes com HubEvents sintéticos + fake provider; quickstart sem hardware. |
| Versionamento | PASS. Sem tag de produto nesta fatia; só nota de débito resolvido. |

Nenhuma violação → Complexity Tracking vazio.

### Post-design re-check (Phase 1)

Gates permanecem PASS. `research.md` / `data-model.md` / `contracts/invocation-result-sourcetype.md` / `quickstart.md` não introduzem SDK de provedor, não misturam canais, falham fechado em origem inválida, e mantêm resolução server-side sem campo de entrada `sourceType`.

## Project Structure

### Documentation (this feature)

```text
specs/017-issue-40-invocation-sourcetype/
├── plan.md                 # This file
├── research.md             # Phase 0
├── data-model.md           # Phase 1
├── quickstart.md           # Phase 1
├── contracts/
│   └── invocation-result-sourcetype.md
├── checklists/
│   └── requirements.md
└── tasks.md                # Phase 2 — /speckit-tasks (não criado aqui)
```

### Source Code (repository root) — arquivos prováveis

```text
services/session-core/src/main/java/ai/assistanthub/core/
├── provider/
│   ├── InvocationResult.java          # + sourceType
│   ├── InvocationService.java         # resolve antes do loop; log
│   ├── InvocationRequest.java         # sem sourceType (só docs se preciso)
│   ├── AiProviderController.java      # handler 422 ChannelOrigin*
│   └── ChannelOriginUnresolvedException.java  # novo (nome final no implement)
├── session/  ou  provider/
│   └── ChannelOriginResolver.java     # novo — lê SessionRepository
└── session/SessionRepository.java     # uso existente (events)

services/session-core/src/test/java/ai/assistanthub/core/provider/
├── ChannelOriginResolverTest.java     # novo
├── InvocationSourceTypeContractTest.java  # novo (ou nome equivalente)
├── FakeProviderInvocationTest.java    # fixture de eventos ou channelId null
├── InvocationErrorTaxonomyTest.java   # ajustar se necessário
├── SecretMaskingTest.java             # ajustar se necessário
└── ProviderTestSupport.java           # wiring SessionRepository / resolver

apps/desktop-shell/
├── src/api-client.ts                  # InvocationResult.sourceType?
└── src-tauri/src/ai_provider_client.rs  # campo opcional no struct

CHANGELOG.md                           # nota de débito resolvido (quando fechar fatia)
# issue #40 — comentário/close humano
```

**Structure Decision**: Manter o layout monorepo existente. Toda a lógica de domínio no módulo `session-core` (provider + session). Desktop só espelha DTO. Sem novos pacotes Maven/npm. Sem mudança em `agents/` ou `services/transcription-service/`.

## Complexity Tracking

> Preenchido apenas se houver violação justificada da constituição.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Implementation sketch (for `/speckit-tasks`, not code)

1. **ChannelOriginResolver** (pacote `provider/`, não `session/`)  
   - Input: `String sessionId`, `String channelId`  
   - Se `channelId` presente: parse `sessionId` → `UUID`; UUID inválido → `ChannelOriginUnresolvedException` (422), nunca exceção de parse crua  
   - Output: `ResolvedChannelOrigin` ou throw  
   - Scan `SessionRepository.events(uuid)`, filter `correlation.channelId`, collect distinct `sourceType`  
   - Fixtures de teste com canal usam `session.id().toString()` real (analyze U1)

2. **InvocationService.invoke**  
   - Se `channelId` blank → `resolvedSourceType = null` (sem lookup; `sessionId` pode não ser UUID)  
   - Senão → resolver (throw se falhar)  
   - Passar `sourceType` a todos os construtores de `InvocationResult` (sucesso, failureResult, lastFailure, empty providers)  
   - `logInvocation`: incluir `sourceType`; cobertura automatizada do log = task T032 (analyze C1 / SC-006)

3. **AiProviderController**  
   - `@ExceptionHandler` → 422  
   - Request body **sem** campo de origem

4. **Desktop**  
   - Campo opcional no resultado; serde ignora ausência

5. **Testes** conforme [quickstart.md](./quickstart.md)

6. **Tracking** FR-009: changelog/issue (humano no merge)

## Phases completed by this command

| Phase | Artifact | Status |
|-------|----------|--------|
| 0 Research | [research.md](./research.md) | Done |
| 1 Design | [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md) | Done |
| 2 Tasks | `tasks.md` | **Not** this command → `/speckit-tasks` |
