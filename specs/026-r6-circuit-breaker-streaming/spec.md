# Feature Specification: R6 — Circuit breaker e streaming de invocação de IA

**Feature Branch**: `feature/026-r6-circuit-breaker-streaming`

**Created**: 2026-07-26

**Status**: Draft

**Input**: User description: "R6 — circuit breaker por provedor e streaming token-a-token com cancelamento no AI Provider Hub, fechando o buraco de specs/003-ai-provider-hub após a fatia 015 (registro + invoke síncrono + fallback de rota)."

**Referências**: `specs/003-ai-provider-hub/` · `specs/015-issue-37-ai-provider-hub/` · `specs/017-issue-40-invocation-sourcetype/` · ADR-0010 · `docs/security/provider-secrets.md` · `contracts/ai-provider-profile.v1.schema.json`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Provedor instável deixa de ser chamado até recuperar (Priority: P1)

Quando um provedor falha de forma repetida (timeout, 5xx, rate limit persistente), o hub abre um circuit breaker para esse provedor e deixa de enviá-lo novas invocações por um período, preferindo fallbacks da rota. Depois do período de resfriamento, tenta novamente de forma controlada.

**Why this priority**: Fallback já existe (015), mas sem breaker o hub continua martelando um provedor morto, aumentando latência e custo. É o gap mais crítico da visão 003.

**Independent Test**: Configurar fake primary que falha N vezes; após o limiar, a próxima invocação da rota deve pular o primary (breaker aberto) e usar o fallback sem chamar o primary; após a janela de abertura, uma tentativa half-open pode reabilitar o primary.

**Acceptance Scenarios**:

1. **Given** um provedor com falhas consecutivas acima do limiar configurado, **When** uma nova invocação usa uma rota que o tem como primary, **Then** o hub não chama esse provedor e tenta o próximo fallback habilitado (ou retorna erro tipado se não houver fallback).
2. **Given** o breaker de um provedor está aberto, **When** o tempo de abertura expira, **Then** o hub permite uma tentativa de prova (half-open); sucesso fecha o breaker; falha reabre.
3. **Given** o breaker está aberto para o primary e existe fallback saudável, **When** o operador invoca a rota, **Then** a resposta de sucesso vem do fallback com `providerId` do fallback (como já em 015).

---

### User Story 2 - Receber resposta em streaming e cancelar (Priority: P1)

Um chamador (API ou cliente futuro) solicita invocação em modo streaming e recebe trechos de texto à medida que o provedor os gera. Pode cancelar a geração em andamento; o hub para de consumir o provedor e libera recursos.

**Why this priority**: A visão 003 e o live-answer pedem latência percebida baixa; invoke síncrono de 015 só devolve o texto completo. Streaming + cancel fecham o segundo gap grande do hub.

**Independent Test**: Com fake adapter em modo stream, abrir o endpoint de stream e receber múltiplos chunks que concatenados formam a resposta; abortar a conexão no meio e confirmar que a geração para (sem derrubar o session-core).

**Acceptance Scenarios**:

1. **Given** uma rota com provedor fake de stream, **When** o cliente abre o stream de invocação, **Then** recebe uma sequência de trechos e um evento final de conclusão com metadados de proveniência (`providerId`, modelo, latência).
2. **Given** um stream em andamento, **When** o cliente cancela/desconecta, **Then** o hub encerra a invocação sem deixar o processo session-core em falha e sem logar o conteúdo completo da resposta como se fosse métrica de segredo.
3. **Given** o primary falha no stream e há fallback, **When** a política de rota/breaker permitir, **Then** o cliente ainda recebe um resultado utilizável (stream do fallback ou erro tipado explícito no canal de stream).

---

### User Story 3 - Observar estado do breaker sem vazamento de segredos (Priority: P2)

Operação e testes precisam saber se um provedor está em circuito aberto, half-open ou fechado, sem expor chaves ou prompts.

**Why this priority**: Diagnóstico; secundário ao comportamento de US1/US2.

**Independent Test**: Após forçar abertura do breaker, consultar o status exposto (API ou estrutura interna coberta por teste) e ver estado OPEN para aquele `providerId`.

**Acceptance Scenarios**:

1. **Given** o breaker de `provider-x` está OPEN, **When** o status do hub para provedores é consultado, **Then** `provider-x` aparece com estado aberto e timestamp de reabertura estimada, sem segredos.

---

### Edge Cases

- Capacidade incompatível (`CAPABILITY_MISMATCH`) **não** conta como falha de breaker (é config, não saúde do provedor).
- `AUTHENTICATION` / `MODEL_NOT_FOUND` contam como falha (provedor ou config que deve acionar fallback e pode abrir breaker se repetidas).
- Provedor `enabled: false` continua nunca invocado (015); breaker não o “ressuscita”.
- Stream sem suporte no adaptador: erro tipado claro, sem inventar chunks.
- Invoke síncrono existente (`POST /invoke`) permanece e **também** respeita o breaker.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O hub MUST manter um circuit breaker **por `providerId`**, com estados fechado, aberto e half-open.
- **FR-002**: Após um limiar configurável de falhas consecutivas (default documentado), o breaker MUST abrir e o hub MUST NOT chamar esse provedor até half-open/fechamento.
- **FR-003**: Em estado aberto, o hub MUST preferir o próximo candidato da rota (fallback); se nenhum restar, MUST retornar erro tipado incluindo indicação de circuito aberto quando for a causa.
- **FR-004**: Após o tempo de abertura configurável, o hub MUST permitir exatamente uma tentativa half-open por provedor; sucesso fecha; falha reabre o temporizador.
- **FR-005**: Sucesso de invocação (síncrona ou stream completa) MUST registrar sucesso no breaker (fecha ou mantém fechado).
- **FR-006**: O hub MUST expor invocação em streaming (trechos parciais + conclusão) via API versionada do session-core.
- **FR-007**: Cancelamento/desconexão do cliente de stream MUST interromper o consumo do provedor de forma isolada (não derruba session-core).
- **FR-008**: O adaptador OpenAI-compatible MUST suportar `stream=true` quando a capacidade for `chat` (ou equivalente já suportada).
- **FR-009**: O adaptador fake MUST suportar modo stream determinístico para testes sem rede.
- **FR-010**: Invoke síncrono existente MUST continuar funcionando e MUST aplicar a mesma política de breaker.
- **FR-011**: Logs MUST NOT incluir segredos, prompts completos nem áudio; métricas de stream usam contagens/latência/providerId apenas (P9).
- **FR-012**: Testes automatizados MUST cobrir abertura/fechamento do breaker, skip de primary aberto, stream multi-chunk e cancel, sem GPU/rede externa (P10).
- **FR-013**: MUST NOT alterar o schema `ai-provider-profile.v1` de forma incompatível; defaults de breaker podem ser código/config de serviço, não obrigatoriamente YAML nesta fatia.
- **FR-014**: MUST NOT implementar billing, marketplace, nem novos tipos de provedor além dos já suportados (fake + openai-compatible).

### Key Entities

- **ProviderCircuitState**: por `providerId` — CLOSED | OPEN | HALF_OPEN, contadores, timestamps.
- **StreamChunk**: trecho de texto parcial com índice opcional.
- **StreamCompletion**: metadados finais alinhados a `InvocationResult` (proveniência, sucesso/erro).

## Success Criteria *(mandatory)*

- **SC-001**: Após o limiar de falhas, 100% das invocações de rota com fallback saudável **não** chamam o primary com breaker OPEN (verificado em teste).
- **SC-002**: Stream fake entrega ≥ 2 chunks + evento final em teste automatizado.
- **SC-003**: Cancel de stream não propaga exceção não tratada ao container (teste).
- **SC-004**: Invoke síncrono de 015 permanece verde na suíte existente.
- **SC-005**: Nenhum teste loga ou devolve secret em claro.

## Assumptions

- Defaults: 5 falhas consecutivas abrem o breaker; 30s de abertura; half-open com 1 tentativa. Ajustáveis por propriedades do serviço (`ai.provider.circuit.*`).
- Fallback de rota (015) permanece a política de ordem de candidatos; breaker só remove candidatos OPEN da chamada efetiva (ou os marca como falha CIRCUIT_OPEN sem HTTP).
- Streaming nesta fatia é **API session-core**; UI desktop live-answer pode continuar síncrona e consumir stream numa fatia futura.
- Formato de stream: Server-Sent Events (SSE) com eventos `chunk` e `done`/`error` JSON.

## Out of Scope

- UI desktop de streaming no painel do Assistente.
- Circuit breaker distribuído entre réplicas (single-process in-memory basta).
- Retry com backoff além do half-open.
- Descoberta `/v1/models`, secure store OS, presets NIM (outros itens de 003).
