---

description: "Task list for Publicar eventos transcript v2 no session-core (SF-021)"
---

# Tasks: Publicar eventos transcript v2 no session-core (SF-021)

**Input**: Design documents from `/specs/007-sf-021-session-core-events/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/README.md, quickstart.md

**Tests**: Incluídos — `spec.md` FR-007 exige explicitamente testes automatizados (Java e/ou de contrato), e cada User Story define seu próprio "Independent Test".

**Organization**: Tarefas agrupadas por user story (`spec.md`), para implementação e teste independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: A qual user story a tarefa pertence (US1, US2, US3)
- Caminhos de arquivo são sempre absolutos-relativos ao repositório

## Path Conventions

Módulo Maven já existente `services/session-core` (ver `plan.md` → Project Structure):

- `services/session-core/src/main/java/ai/assistanthub/core/transcript/` — código novo
- `services/session-core/src/test/java/ai/assistanthub/core/transcript/` — testes novos
- `services/session-core/pom.xml`, `services/session-core/src/main/resources/application.yml` — configuração
- `contracts/transcript-event.v2.schema.json` (raiz do repo) — contrato consumido, sem alteração

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar o módulo `session-core` para o novo pacote `transcript` (dependências e esqueleto de pastas).

- [x] T001 Adicionar dependência `spring-boot-starter-websocket` em `services/session-core/pom.xml` (cliente WebSocket para consumir `/ws/transcripts`, ver `research.md` #1)
- [x] T002 [P] Adicionar dependência `networknt:json-schema-validator` em `services/session-core/pom.xml` (escopo principal — `TranscriptEventValidator` valida eventos reais em runtime, não só fixtures de teste; ver `research.md` #5)
- [x] T003 [P] Criar os pacotes `services/session-core/src/main/java/ai/assistanthub/core/transcript/` e `services/session-core/src/test/java/ai/assistanthub/core/transcript/` (diretórios vazios com `package-info.java` ou primeiro arquivo de cada, conforme convenção do módulo)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura usada por todas as três user stories — DTO do evento v2, configuração de conexão e validação de contrato.

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase estar completa.

- [x] T004 [P] Criar o DTO `TranscriptEventV2` (record, com `Device` aninhado) espelhando `contracts/transcript-event.v2.schema.json` em `services/session-core/src/main/java/ai/assistanthub/core/transcript/TranscriptEventV2.java` (ver `data-model.md` → TranscriptEventV2)
- [x] T005 [P] Criar `TranscriptIngestionProperties` (URL do feed `/ws/transcripts` do `transcription-service`, configurável via a propriedade `session-core.transcript-ingestion.feed-url`) em `services/session-core/src/main/java/ai/assistanthub/core/transcript/TranscriptIngestionProperties.java`, com a propriedade correspondente em `services/session-core/src/main/resources/application.yml`
- [x] T006 [P] Criar `TranscriptEventValidator`, validando o JSON bruto recebido contra `contracts/transcript-event.v2.schema.json` (via `networknt`, mesma fonte de verdade usada por `services/transcription-service/tests/test_ws_audio_contract.py`) em `services/session-core/src/main/java/ai/assistanthub/core/transcript/TranscriptEventValidator.java`
- [x] T007 [P] Escrever `TranscriptContractTest` cobrindo: evento v2 válido com `device.endpointId` presente passa; evento válido com `device.endpointId` nulo passa; evento sem campo obrigatório (ex.: sem `device`) é rejeitado — em `services/session-core/src/test/java/ai/assistanthub/core/transcript/TranscriptContractTest.java` (depende de T006)

**Checkpoint**: DTO, configuração e validação de contrato prontos — as user stories podem começar.

---

## Phase 3: User Story 1 - Evento v2 chega à sessão com metadados de canal preservados (Priority: P1) 🎯 MVP

**Goal**: Um evento `transcript.partial.v2`/`transcript.final.v2` publicado pelo `transcription-service` é ingerido pelo `session-core` e vira um registro na sessão preservando `channelId`, `sourceType`, `label` e `device` (`index`/`name`/`endpointId`) sem perda.

**Independent Test**: Publicar um evento v2 sintético com metadados conhecidos para uma sessão ativa (via um servidor WebSocket fake que reproduz `/ws/transcripts`) e consultar `GET /api/sessions/{id}/events`, verificando que os metadados retornados em `correlation` são idênticos aos recebidos — sem hardware, GPU ou STT real.

### Tests for User Story 1 ⚠️

> Escrever estes testes primeiro; devem falhar antes da implementação.

- [x] T008 [P] [US1] Escrever `TranscriptEventMapperTest`: mapeamento de um `TranscriptEventV2` para `HubEvent` preserva `channelId`/`sourceType`/`label`/`device.*` em `correlation`; caso com `device.endpointId` nulo também é aceito (AC1/AC2 da US1) — em `services/session-core/src/test/java/ai/assistanthub/core/transcript/TranscriptEventMapperTest.java`
- [x] T009 [P] [US1] Escrever `TranscriptFeedClientHappyPathTest`: contra um servidor WebSocket fake que reproduz `/ws/transcripts`, um evento `partial` seguido do `final` correspondente ficam registrados na sessão em ordem cronológica, sem o parcial ser descartado (AC3 da US1) — em `services/session-core/src/test/java/ai/assistanthub/core/transcript/TranscriptFeedClientHappyPathTest.java`

### Implementation for User Story 1

- [x] T010 [US1] Implementar `TranscriptEventMapper` (evento v2 → `HubEvent`, mapeando `payload`/`correlation` conforme `data-model.md`) em `services/session-core/src/main/java/ai/assistanthub/core/transcript/TranscriptEventMapper.java` (depende de T004; faz T008 passar)
- [x] T011 [US1] Implementar `TranscriptFeedClient`: conecta ao feed `/ws/transcripts` (URL de T005), decodifica JSON, valida com `TranscriptEventValidator` (T006), resolve a `ConversationSession` pelo `sessionId` recebido (comparando com `ConversationSession.id().toString()`, ver `research.md` #3) — tratando como sessão desconhecida tanto a ausência de `ConversationSession` quanto o status `ENDED` (`CREATED` também é aceito, conforme FR-004) —, mapeia com `TranscriptEventMapper` (T010) e anexa via `SessionRepository.append` — em `services/session-core/src/main/java/ai/assistanthub/core/transcript/TranscriptFeedClient.java` (depende de T005, T006, T010; faz T009 passar)
- [x] T012 [US1] Conectar `TranscriptFeedClient` à inicialização do serviço via `@EventListener(ApplicationReadyEvent)` + `@PreDestroy` (implementado dentro do próprio `TranscriptFeedClient.java`, mais coeso do que acoplar em `SessionCoreApplication.java`) para que a ingestão comece junto com o `session-core` (depende de T011)

**Checkpoint**: US1 completa e testável de forma independente (`mvn -pl services/session-core -am test`, `quickstart.md` seções 1–2).

---

## Phase 4: User Story 2 - Canais distintos na mesma sessão não se misturam (Priority: P2)

**Goal**: Eventos de `channelId` diferentes na mesma sessão permanecem distinguíveis, nunca fundidos ou sobrescritos.

**Independent Test**: Enviar eventos v2 intercalados de dois `channelId` diferentes para a mesma sessão e verificar, via `GET /api/sessions/{id}/events`, que cada evento mantém seu `channelId`/`sourceType`/`device` de origem, na ordem de chegada, sem contaminação cruzada.

### Tests for User Story 2 ⚠️

- [x] T013 [P] [US2] Escrever `TranscriptFeedClientMultiChannelTest`: dois canais ("mic" e "system") intercalados mantêm seu `channelId` de origem correto; eventos de canais diferentes com o mesmo texto transcrito permanecem registros distintos (não deduplicados por conteúdo) — em `services/session-core/src/test/java/ai/assistanthub/core/transcript/TranscriptFeedClientMultiChannelTest.java`

### Implementation for User Story 2

- [x] T014 [US2] Confirmar (e ajustar se necessário) que o despacho de eventos em `TranscriptFeedClient` cria um `HubEvent` independente por evento, sem estado mutável compartilhado entre canais, em `services/session-core/src/main/java/ai/assistanthub/core/transcript/TranscriptFeedClient.java` (depende de T011, T013; faz T013 passar)

**Checkpoint**: US1 e US2 funcionam de forma independente e conjunta.

---

## Phase 5: User Story 3 - Consumo não vira orquestração e evento inválido não derruba a sessão (Priority: P3)

**Goal**: `session-core` permanece um consumidor passivo — nunca envia comando de controle ao `transcription-service` — e um evento malformado ou de sessão desconhecida/encerrada é rejeitado e logado, sem interromper a ingestão de outras sessões.

**Independent Test**: Enviar um evento sem campo obrigatório do contrato v2 e um evento referenciando um `sessionId` inexistente/encerrado; verificar que ambos são rejeitados sem alterar sessões existentes e sem derrubar o loop de leitura do cliente; confirmar por inspeção que nenhum caminho de código envia instrução de controle ao `transcription-service`.

### Tests for User Story 3 ⚠️

- [x] T015 [P] [US3] Escrever `TranscriptFeedClientResilienceTest`: evento sem campo obrigatório é descartado e logado sem interromper o cliente; evento de `sessionId` desconhecido/encerrado é descartado sem criar sessão implícita; um evento válido enviado logo depois de um inválido ainda é processado normalmente; nenhuma chamada de controle é emitida de volta ao servidor fake — em `services/session-core/src/test/java/ai/assistanthub/core/transcript/TranscriptFeedClientResilienceTest.java`

### Implementation for User Story 3

- [x] T016 [US3] Implementar o caminho de rejeição/log em `TranscriptFeedClient` (WARN com `type`/`channelId`/`sessionId`, sem propagar exceção, mantendo o loop de leitura ativo) usando `TranscriptEventValidator` (T006) e a checagem de sessão existente e não `ENDED` de T011 (`CREATED` também é aceito — FR-004), em `services/session-core/src/main/java/ai/assistanthub/core/transcript/TranscriptFeedClient.java` (depende de T006, T011, T015; faz T015 passar)
- [x] T017 [US3] Implementar reconexão com backoff limitado em `TranscriptFeedClient` ao perder a conexão com `/ws/transcripts`, sem falhar a inicialização do `session-core` (ver `research.md` #7), em `services/session-core/src/main/java/ai/assistanthub/core/transcript/TranscriptFeedClient.java` (depende de T011, T015)

**Checkpoint**: As três user stories funcionam de forma independente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Fechamento da issue #15 — suíte completa verde e evidência da validação.

- [x] T018 [P] Rodar `mvn -pl services/session-core -am test` completo e confirmar que todas as suítes (T007, T008, T009, T013, T015) passam sem GPU/hardware (FR-007, SC-004)
- [x] T019 [P] Executar `quickstart.md` seções 1–2 (validação automatizada + verificação de consulta ponta a ponta) e registrar o resultado no resumo da PR
- [x] T020 [P] Conferir que `specs/007-sf-021-session-core-events/contracts/README.md` (seção 2, mapeamento `correlation`) ainda reflete os nomes de chave e o comportamento realmente implementados em `TranscriptEventMapper` (T010) e `TranscriptFeedClient` (T011/T016), atualizando o documento se tiver divergido (FR-006, SC-005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as user stories
- **User Stories (Phase 3–5)**: todas dependem da conclusão da Fase 2
  - US1 (P1) é o MVP e deve ser concluída primeiro na prática, pois US2 e US3 estendem o mesmo `TranscriptFeedClient` que US1 cria (T011)
  - US2 e US3 podem prosseguir em paralelo depois que US1 termina T011, já que tocam preocupações distintas do mesmo arquivo (separação de canal vs. resiliência/rejeição)
- **Polish (Phase 6)**: depende de todas as user stories desejadas estarem completas

### User Story Dependencies

- **User Story 1 (P1)**: depende apenas da Fase 2 — sem dependência de outra story
- **User Story 2 (P2)**: depende da Fase 2 e de T011 (US1) já existir, pois estende o mesmo `TranscriptFeedClient`; ainda assim é testável de forma independente (T013 não depende de T016/T017 de US3)
- **User Story 3 (P3)**: depende da Fase 2 e de T011 (US1) já existir, pelo mesmo motivo; testável de forma independente de US2

### Parallel Opportunities

- T002 e T003 (Setup) em paralelo após T001
- T004, T005, T006 (Foundational) em paralelo entre si; T007 depende apenas de T006
- Dentro de cada user story, o teste (`[P]`) pode ser escrito em paralelo com o teste de outra story, mesmo que a implementação seja sequencial dentro do mesmo arquivo `TranscriptFeedClient.java`
- T018, T019 e T020 (Polish) em paralelo

---

## Parallel Example: User Story 1

```bash
# Escrever os testes da User Story 1 em paralelo (arquivos diferentes):
Task: "Escrever TranscriptEventMapperTest em services/session-core/src/test/java/ai/assistanthub/core/transcript/TranscriptEventMapperTest.java"
Task: "Escrever TranscriptFeedClientHappyPathTest em services/session-core/src/test/java/ai/assistanthub/core/transcript/TranscriptFeedClientHappyPathTest.java"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Fase 1: Setup
2. Completar Fase 2: Foundational (bloqueia todas as stories)
3. Completar Fase 3: User Story 1
4. **PARAR e VALIDAR**: rodar `quickstart.md` seções 1–2 de forma independente
5. Esse MVP já satisfaz o primeiro critério de aceite da issue #15 ("Evento v2 chega ao session-core com channelId/sourceType/device")

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 → testar independentemente → já é um incremento demonstrável (MVP)
3. US2 → testar independentemente → separação de canal comprovada
4. US3 → testar independentemente → robustez de fronteira comprovada, fechando o critério "transcription não vira orquestrador de sessão"
5. Cada story agrega valor sem quebrar a anterior

### Ordem sugerida (equipe única)

Dada a dependência real de arquivo (`TranscriptFeedClient.java` é criado em US1 e estendido por US2/US3), a ordem sequencial P1 → P2 → P3 é mais simples do que paralelizar entre desenvolvedores neste caso específico.

---

## Notes

- `[P]` = arquivos diferentes, sem dependência de tarefa incompleta
- Rótulo `[Story]` mapeia a tarefa à user story correspondente em `spec.md`
- Testes devem ser escritos e falhar antes da implementação correspondente
- Fazer commit após cada tarefa ou grupo lógico
- Parar em qualquer checkpoint para validar a story isoladamente
- Evitar: tarefas vagas, conflito no mesmo arquivo sem necessidade, dependências entre stories que quebrem a independência de teste

---

## Phase 7: Convergence

**Purpose**: Gaps encontrados por `/speckit-converge` entre o código já implementado e o que `spec.md`/`plan.md`/`tasks.md` exigem — nenhuma tarefa anterior foi alterada.

- [x] T021 Tornar `SessionRepository.append` seguro para chamadas concorrentes para a mesma sessão (ex.: lista sincronizada em vez de `ArrayList` puro), já que `TranscriptFeedClient` despacha mensagens do feed WebSocket em threads de I/O diferentes por evento (confirmado nos logs do teste de resiliência), risco real de perda/corrupção de evento sob múltiplos canais concorrentes — em `services/session-core/src/main/java/ai/assistanthub/core/session/SessionRepository.java` per FR-003/SC-001/SC-002 (partial) — **feito**: `Collections.synchronizedList` + `synchronized` em `append`/`events`/`hydrate`; teste `SessionRepositoryTest.concurrentAppendsOnSameSessionPreserveAllEvents`
- [x] T022 Adicionar ao `contracts/README.md` uma nota explícita de que `transcript-event.v1` não é suportado por este consumidor — hoje esse fato só está documentado em `spec.md` (seção Assumptions), não na própria documentação de fronteira/compatibilidade — em `specs/007-sf-021-session-core-events/contracts/README.md` per FR-006/SC-005 (partial) — **feito**: seção "Compatibilidade de versão"
