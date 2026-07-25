# Research: Consistência de `sourceType` em resultados de invocação

**Feature**: `specs/017-issue-40-invocation-sourcetype`  
**Date**: 2026-07-25  
**Spec**: [spec.md](./spec.md) (clarifications session 2026-07-25)

## Decision 1 — Resolução server-side a partir de `HubEvent.correlation`

**Decision**: Introduzir um resolvedor (ex.: `ChannelOriginResolver`) no `session-core` que, dado `sessionId` + `channelId`, lê eventos via `SessionRepository.events(sessionId)`, filtra por `correlation.channelId`, e devolve o único `correlation.sourceType` canônico observado para aquele canal.

**Rationale**: `TranscriptEventMapper` já grava `channelId` e `sourceType` em `HubEvent.correlation` (P5). O Memory Hub / cache em memória já persiste esses eventos (issue #29). A clarificação Q5 exige evidência via eventos de transcript/hub já gravados, **sem** cadastro de canal novo. Reutilizar `SessionRepository` evita duplicar origem e mantém o hub de provedores como consumidor do contexto de sessão (como em 015).

**Alternatives considered**:
- **Campo `sourceType` no request do chamador** — rejeitado (Q1): chamador não é autoridade.
- **Tabela/registro de canais na sessão** — rejeitado nesta fatia (Q5): escopo de débito, não redesign de Memory Hub.
- **Ler só do SQLite, ignorando cache** — rejeitado: leituras de sessão já são servidas pelo cache rehidratado; usar o mesmo caminho que o resto do core.

## Decision 2 — Momento da resolução e semântica de falha

**Decision**: Resolver origem **antes** do loop de provedores em `InvocationService.invoke`.  
- `channelId` nulo/blank → `sourceType = null` no resultado; prosseguir.  
- `channelId` presente e origem resolvível → preencher e prosseguir.  
- `channelId` presente e não resolvível / não canônico / conflito → **falha explícita sem chamar provedor**.

**Forma da falha**: exceção de domínio dedicada (ex.: `ChannelOriginUnresolvedException`) mapeada no controller para **HTTP 422** com mensagem clara (canal sem eventos, origem não canônica, ou conflito). Não reutilizar `InvocationErrorType` de provedor (timeout, auth, etc.) — a falha é de **contexto de sessão**, não de adaptador.

**Rationale**: Spec FR-006/FR-011 e edge cases pedem rejeição explícita, não “melhor esforço”. Separar de `InvocationErrorType` evita acionar fallback de rota quando o problema é origem do canal. Alinha a `RouteNotFoundException` / `UnsupportedProviderTypeException` (pré-condições fora do loop de fallback).

**Alternatives considered**:
- **`InvocationResult.success=false` com novo `InvocationErrorType.ORIGIN_*`** — possível, mas misturaria taxonomia de provedor com contexto de sessão e poderia acionar fallback indevidamente se mal classificado.
- **HTTP 404** — enganoso (sessão pode existir; falta origem do canal).
- **HTTP 400** — aceitável, mas 422 comunica melhor “payload ok, semântica incompleta”.

## Decision 3 — Campo aditivo em `InvocationResult`

**Decision**: Adicionar `String sourceType` (nullable) ao record `InvocationResult` e espelhar nos clientes desktop (`api-client.ts`, `ai_provider_client.rs`). **Não** adicionar `sourceType` ao body de entrada `InvokeRequest` / `InvocationRequest`.

**Rationale**: FR-001/FR-010; preferência de compatibilidade aditiva da spec; request já tem `channelId` opcional. Jackson/serde com campo novo no JSON de resposta é aditivo; clientes que ignoram campos desconhecidos continuam ok.

**Alternatives considered**:
- **Só documentar sem campo** — rejeitado: issue #40 e SC-001 exigem preservação no resultado.
- **Envelope `context: { sourceType }`** — over-engineering para um débito de consistência.

## Decision 4 — Conjunto canônico e conflito

**Decision**: Aceitar **somente** `microphone` e `system` (enum do `transcript-event.v2`).  
Algoritmo: coletar set distinto de `sourceType` não-nulos nos eventos do canal;  
- size 0 → unresolved;  
- size 1 e canônico → ok;  
- size 1 e não canônico → reject;  
- size > 1 → conflict reject (não “último evento ganha” — Q5).

**Rationale**: FR-002, FR-011, Q3, Q5. Fail-closed evita segundo vocabulário.

**Alternatives considered**: aliases (`mic`→`microphone`), último evento, valor “unknown” — todos rejeitados nas clarificações.

## Decision 5 — Observabilidade

**Decision**: Estender o log estruturado `ai-provider-invocation` com `sourceType={}` (valor ou literal `null` quando N/A). Continuar **sem** logar `output`/`message`/segredos.

**Rationale**: Q4 / FR-012 / SC-006. SLF4J já usado em `InvocationService.logInvocation`.

**Alternatives considered**: métricas Micrometer novas — fora de escopo; só resultado API sem log — rejeitado (Q4).

## Decision 6 — Superfície de testes e fixtures

**Decision**:  
1. Testes unitários do resolvedor com `HubEvent`s sintéticos (correlation).  
2. Testes de `InvocationService` com canal: fixture de sessão + eventos no `SessionRepository` (ou double do resolvedor).  
3. Atualizar testes existentes que passam `channelId` **sem** eventos: ou (a) passar `channelId=null` quando o foco é só provedor, ou (b) inserir evento mínimo com origem canônica. Preferir (b) quando o teste afirma contexto de canal; (a) quando afirma só adaptador/rota.  
4. Testes de contrato do resultado: sucesso, falha de provedor (origem ainda presente), sem canal, unresolved, non-canonical, conflito multi-canal.

**Rationale**: FR-008; testes atuais (`FakeProviderInvocationTest`) usam `"mic-1"` sem eventos e quebrariam com a Decision 2.

## Decision 7 — Documentação de débito (FR-009)

**Decision**: Ao fechar a implementação, atualizar tracking: issue #40 (comentário/close via processo humano), e nota no próximo material de release/changelog de que `InvocationResult-sourceType` foi resolvido. Não inventar tag de produto nesta fatia.

**Rationale**: FR-009; P8 proíbe fechar issue por script no fluxo normal.

## Decision 8 — Fora de escopo técnico confirmado

- Sem mudança no Windows audio agent, transcription-service ou schema JSON de transcript.  
- Sem UI desktop obrigatória além de espelhar campo opcional no tipo `InvocationResult` (para não dessincronizar o cliente).  
- Sem Vite audit (#41).  
- Sem ADR novo: mudança aditiva de campo de resultado + regra de resolução; P4 satisfeito com contrato feature-local e testes (ADR só se no futuro o resultado virar schema JSON formal versionado no monorepo).

## Open items deferred to implement (not research blockers)

- Nome exato da exception e da mensagem PT ao usuário da API (T019).  

## Closed by analyze remediation (2026-07-25)

- **`sessionId` com canal (U1)**: com `channelId` não blank, o servidor DEVE interpretar `sessionId` como UUID; UUID inválido → `ChannelOriginUnresolvedException` / HTTP 422 (não 500). Sessão/eventos ausentes → mesma família 422 via resolução de origem. Sem canal: não exige UUID (testes provider-only com strings livres permanecem válidos).  
- **SC-006 / log (C1)**: implementação do campo no log (T018) + assert automatizado (T032).
