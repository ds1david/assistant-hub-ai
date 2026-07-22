---

description: "Task list for Memory Hub — persistência local de sessão e eventos (R3)"
---

# Tasks: Memory Hub — persistência local de sessão e eventos (R3)

**Input**: Design documents from `/specs/013-issue-29-memory-hub-persistence/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Incluídos — a spec exige testes automatizados explicitamente (FR-008) para persistência, retomada após restart e crash-safety, sem GPU nem hardware de áudio.

**Organization**: Tarefas agrupadas por user story (US1/US2/US3, prioridades da spec) para permitir implementação e teste independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: A qual user story a tarefa pertence (US1, US2, US3)
- Caminhos de arquivo são sempre relativos à raiz do monorepo

## Path Conventions

Projeto único (extensão de módulo Maven já existente): `services/session-core/src/main/java/ai/assistanthub/core/memory/` (código novo) e `services/session-core/src/test/java/ai/assistanthub/core/memory/` (testes novos), conforme `plan.md` § Project Structure.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar o módulo `session-core` para a nova dependência e configuração do Memory Hub

- [X] T001 Adicionar a dependência `org.xerial:sqlite-jdbc` em `services/session-core/pom.xml`
- [X] T002 [P] Adicionar o bloco `session-core.memory-hub` (`path`, `retention.max-age`, `retention.max-sessions`) em `services/session-core/src/main/resources/application.yml`, seguindo o padrão já usado por `session-core.transcript-ingestion.feed-url`
- [X] T003 [P] Adicionar o caminho padrão `data/session-core/*.db` ao `.gitignore` (P9 — nunca commitar dado de sessão)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Conexão e schema SQLite que todas as user stories dependem

**⚠️ CRITICAL**: Nenhuma user story pode ser implementada antes desta fase estar completa

- [X] T004 Criar `MemoryHubProperties` em `services/session-core/src/main/java/ai/assistanthub/core/memory/MemoryHubProperties.java` — vincula `session-core.memory-hub.*` do `application.yml` (caminho do `.db`, `retention.max-age`, `retention.max-sessions`)
- [X] T005 Criar `MemoryHubDataSource` em `services/session-core/src/main/java/ai/assistanthub/core/memory/MemoryHubDataSource.java` — abre a conexão SQLite (criando o diretório do arquivo se não existir) e executa o DDL das tabelas `sessions` e `session_events` conforme `data-model.md` (depende de T004)

**Checkpoint**: Schema e conexão prontos — implementação das user stories pode começar

---

## Phase 3: User Story 1 - Sessão e eventos preservados após reinício do serviço (Priority: P1) 🎯 MVP

**Goal**: Sessões e eventos gravados no SQLite sobrevivem ao encerramento (gracioso ou abrupto) e reinício do processo `session-core`, continuando consultáveis com os mesmos metadados de canal.

**Independent Test**: Criar sessão, enviar eventos `transcript-event.v2` sintéticos para 1+ canais, reiniciar o processo (ou reidratar o repositório a partir do armazenamento persistido) e consultar a sessão, comparando campo a campo — sem GPU nem hardware de áudio.

### Tests for User Story 1 ⚠️

> Escrever estes testes primeiro; devem falhar antes da implementação abaixo

- [X] T006 [P] [US1] `SessionPersistenceStoreTest` em `services/session-core/src/test/java/ai/assistanthub/core/memory/SessionPersistenceStoreTest.java` — grava sessão + eventos, fecha e reabre o mesmo arquivo SQLite (`@TempDir`) simulando restart gracioso, confirma que sessão e eventos voltam idênticos (campos e ordem)
- [X] T007 [P] [US1] `SessionPersistenceCrashSafetyTest` em `services/session-core/src/test/java/ai/assistanthub/core/memory/SessionPersistenceCrashSafetyTest.java` — interrompe a gravação de um evento antes do commit (transação não concluída) e confirma que os eventos já commitados anteriormente permanecem intactos e consultáveis (FR-009)

### Implementation for User Story 1

- [X] T008 [US1] Implementar `SessionPersistenceStore` em `services/session-core/src/main/java/ai/assistanthub/core/memory/SessionPersistenceStore.java` — grava/lê `ConversationSession` (tabela `sessions`) e `HubEvent` (tabela `session_events`, incluindo `correlation_json` com `channelId`/`sourceType`/`label`/`device`), cada gravação de evento em transação própria; consulta ordenada por `sequence` (depende de T004, T005; deve fazer T006/T007 passarem)
- [X] T009 [US1] Implementar `MemoryHubStartupRehydrator` em `services/session-core/src/main/java/ai/assistanthub/core/memory/MemoryHubStartupRehydrator.java` — na subida do processo, popula o cache em memória (`Map<UUID, ConversationSession>` / `Map<UUID, List<HubEvent>>`) a partir de `SessionPersistenceStore` (depende de T008)
- [X] T010 [US1] Atualizar `SessionRepository` em `services/session-core/src/main/java/ai/assistanthub/core/session/SessionRepository.java` — recebe `SessionPersistenceStore` via construtor (removendo o construtor sem argumento); `save`/`append` passam a escrever também em `SessionPersistenceStore`, mantendo a mesma assinatura pública dos métodos (`save`, `findById`, `append`, `events`) consumida por `SessionController` e pelo mapeador de eventos v2 (depende de T008, T009)
- [X] T010a [US1] Atualizar a instanciação de `SessionRepository` nos testes existentes que hoje usam `new SessionRepository()` sem argumento — `services/session-core/src/test/java/ai/assistanthub/core/session/SessionRepositoryTest.java:13`, `.../transcript/TranscriptFeedClientHappyPathTest.java:57`, `.../transcript/TranscriptFeedClientMultiChannelTest.java:57`, `.../transcript/TranscriptFeedClientResilienceTest.java:61` — passam a usar um `SessionPersistenceStore` de teste (ex.: SQLite em `@TempDir`) (depende de T008, T010)
- [X] T011 [US1] Rodar a suíte já existente (`SessionRepositoryTest`, `TranscriptContractTest`, `TranscriptFeedClientHappyPathTest`, `TranscriptFeedClientMultiChannelTest`, `TranscriptFeedClientResilienceTest` de `specs/007-sf-021-session-core-events/`) e confirmar que continuam verdes com o mesmo comportamento observável (após a atualização de instanciação em T010a) — regressão de FR-007/FR-010 (depende de T010a)

**Checkpoint**: User Story 1 completa e testável de forma independente — sessão/eventos sobrevivem a restart gracioso e a crash simulado.

---

## Phase 4: User Story 2 - Novos eventos após retomada continuam na mesma linha do tempo (Priority: P2)

**Goal**: Depois de uma sessão retomada, novos eventos (canal existente ou novo) se juntam aos eventos anteriores em ordem cronológica correta, sem misturar canais.

**Independent Test**: Retomar uma sessão persistida, enviar novos eventos v2 para um canal já existente e para um canal novo, consultar a sessão e confirmar ordem cronológica (antes + depois do reinício) e separação por canal.

### Tests for User Story 2 ⚠️

- [X] T012 [P] [US2] `SessionPersistenceAppendOrderTest` em `services/session-core/src/test/java/ai/assistanthub/core/memory/SessionPersistenceAppendOrderTest.java` — retoma uma sessão persistida com eventos prévios do canal "mic", anexa um novo evento do canal "mic" e um evento de canal novo ("system"), confirma ordem cronológica correta e nenhuma sobrescrita/mistura de canal

### Implementation for User Story 2

- [X] T013 [P] [US2] `SessionPersistenceSequenceIntegrityTest` em `services/session-core/src/test/java/ai/assistanthub/core/memory/SessionPersistenceSequenceIntegrityTest.java` — confirma que `session_events.sequence` (`INTEGER PRIMARY KEY AUTOINCREMENT`) nunca é reutilizada entre sessões, mesmo quando `RetentionPolicy` (T015) expurga todos os eventos de uma sessão anterior e a tabela fica temporariamente vazia — comportamento garantido pelo motor SQLite, sem lógica própria de contagem (depende de T008)

**Checkpoint**: User Stories 1 e 2 funcionam de forma independente — apêndice contínuo preserva ordem e canais através de reinícios.

---

## Phase 5: User Story 3 - Política de retenção documentada evita crescimento não controlado (Priority: P3)

**Goal**: Existe uma política de retenção/limites configurável e documentada para sessões/eventos persistidos, aplicada sem remover sessões ativas nem falhar novas gravações.

**Independent Test**: Consultar a documentação da política de retenção; em teste automatizado, configurar um limite baixo, gravar sessões `ENDED` além do limite e confirmar expurgo das mais antigas sem afetar sessões ativas.

### Tests for User Story 3 ⚠️

- [X] T014 [P] [US3] `RetentionPolicyTest` em `services/session-core/src/test/java/ai/assistanthub/core/memory/RetentionPolicyTest.java` — configura `retention.max-sessions` baixo, grava sessões `ENDED` além do limite e uma sessão ativa (`CREATED`/não-`ENDED`), confirma que apenas as sessões `ENDED` mais antigas são expurgadas (com seus eventos em cascata) e a sessão ativa permanece intacta

### Implementation for User Story 3

- [X] T015 [US3] Implementar `RetentionPolicy` em `services/session-core/src/main/java/ai/assistanthub/core/memory/RetentionPolicy.java` — aplica `retention.max-age`/`retention.max-sessions` de `MemoryHubProperties`, expurgando (via `SessionPersistenceStore`) as sessões `ENDED` mais antigas e seus eventos em cascata, nunca removendo sessão não-`ENDED` (depende de T004, T008; deve fazer T014 passar)
- [X] T016 [US3] Invocar `RetentionPolicy` na subida do processo, antes da rehydration, em `services/session-core/src/main/java/ai/assistanthub/core/memory/MemoryHubStartupRehydrator.java` (depende de T009, T015) — implementado dentro do próprio `ApplicationRunner` de rehydration, em vez de em `SessionCoreApplication.java`, para eliminar qualquer ambiguidade de ordem entre os dois passos (achado C1 da análise: um único componente orquestra "expurgar, depois repovoar o cache", sem depender da ordem relativa de dois `ApplicationRunner` separados)
- [X] T017 [US3] Documentar a política de retenção padrão e como ajustá-la (sem exigir leitura de código) em `specs/013-issue-29-memory-hub-persistence/data-model.md` — cobre a exigência explícita da issue #29 ("retenção/limites documentados") e SC-002 (já escrito na seção "Conceito: Política de retenção" durante `/speckit-plan`; `data-model.md` escolhido como local canônico, resolvendo a ambiguidade do achado B1 da análise)

**Checkpoint**: Todas as user stories funcionam de forma independente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Garantias que atravessam todas as user stories

- [X] T018 [P] Revisar `SessionPersistenceStore`/`SessionRepository`/`SessionController` para confirmar que nenhum log em nível `INFO`/`ERROR` imprime o conteúdo (`payload`/texto transcrito) de um evento — apenas identificadores (`sessionId`, `channelId`, `type`) (P9) — confirmado: `MemoryHubStartupRehydrator` só loga contagens; `SessionPersistenceStore`/`RetentionPolicy`/`MemoryHubDataSource` não têm nenhum `LOGGER` (só mensagens de exceção com `session.id()`/`event.id()`, que são UUIDs, não conteúdo)
- [X] T019 Executar o roteiro de `specs/013-issue-29-memory-hub-persistence/quickstart.md` (suíte completa via `mvn -pl services/session-core -am test` + validação manual de restart) e confirmar os 5 critérios de sucesso (SC-001 a SC-005) — `mvn -pl services/session-core -am test`: 18/18 testes verdes; `.gitignore` cobre `data/session-core/*.db`; nenhuma referência a GPU/hardware fora dos comentários que documentam a ausência

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: Depende da conclusão do Setup — BLOQUEIA todas as user stories
- **User Story 1 (Phase 3)**: Depende do Foundational — sem dependência de outras stories
- **User Story 2 (Phase 4)**: Depende do Foundational; reaproveita `SessionPersistenceStore` de US1 (T008), mas é testável de forma independente assim que US1 estiver completa
- **User Story 3 (Phase 5)**: Depende do Foundational; reaproveita `MemoryHubProperties` (T004) e `SessionPersistenceStore` (T008) de US1, mas é testável de forma independente
- **Polish (Phase 6)**: Depende de todas as user stories desejadas estarem completas

### Within Each User Story

- Testes escritos e falhando antes da implementação
- `SessionPersistenceStore` (T008) antes de `MemoryHubStartupRehydrator` (T009) e antes de `SessionRepository` (T010)
- Story completa antes de avançar para a próxima prioridade

### Parallel Opportunities

- T002 e T003 (Setup) podem rodar em paralelo
- T006 e T007 (testes de US1) podem rodar em paralelo entre si
- T012 (teste de US2) e T014 (teste de US3) podem rodar em paralelo entre si e com os testes de US1, já que exercitam arquivos de teste diferentes — mas a implementação correspondente (T013, T015) só faz sentido depois de T008 existir
- T018 (Polish) pode rodar em paralelo com T019

---

## Parallel Example: User Story 1

```bash
# Testes de User Story 1 em paralelo:
Task: "SessionPersistenceStoreTest em services/session-core/src/test/java/ai/assistanthub/core/memory/SessionPersistenceStoreTest.java"
Task: "SessionPersistenceCrashSafetyTest em services/session-core/src/test/java/ai/assistanthub/core/memory/SessionPersistenceCrashSafetyTest.java"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRÍTICO — bloqueia todas as stories)
3. Completar Phase 3: User Story 1
4. **PARAR e VALIDAR**: testar User Story 1 de forma independente (restart gracioso + crash simulado)
5. Já entrega o valor central da issue #29: sessão/eventos não são mais perdidos a cada restart

### Incremental Delivery

1. Setup + Foundational → base pronta
2. User Story 1 → validar independentemente → entrega o MVP do Memory Hub
3. User Story 2 → validar independentemente → apêndice contínuo pós-retomada
4. User Story 3 → validar independentemente → retenção documentada e aplicada
5. Cada story agrega valor sem quebrar as anteriores

---

## Notes

- [P] tasks = arquivos diferentes, sem dependência entre si
- Rótulo [Story] mapeia a tarefa à user story correspondente para rastreabilidade
- Verificar que os testes falham antes de implementar
- Fazer commit após cada tarefa ou grupo lógico
- Parar em cada checkpoint para validar a story de forma independente
- Nenhuma tarefa altera `contracts/transcript-event.v2.schema.json` (FR-007) — a persistência é interna ao `session-core`
