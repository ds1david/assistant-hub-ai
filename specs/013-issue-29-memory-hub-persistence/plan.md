# Implementation Plan: Memory Hub — persistência local de sessão e eventos (R3)

**Branch**: `013-issue-29-memory-hub-persistence` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-issue-29-memory-hub-persistence/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Hoje `SessionRepository` guarda `ConversationSession` e os eventos ingeridos (`HubEvent`, incluindo os `transcript-event.v2` mapeados por `specs/007-sf-021-session-core-events/`) só em `ConcurrentHashMap` — tudo é perdido a cada restart do processo. Esta feature introduz uma camada de persistência local (Memory Hub) em SQLite embarcado (arquivo único, sem servidor) por trás da mesma API de `SessionRepository` (`save`, `findById`, `append`, `events`), garantindo que sessão e eventos sobrevivam a reinícios graciosos e abruptos, mantendo ordem cronológica e metadados de canal intactos, e acrescenta uma política de retenção documentada e configurável para não deixar o armazenamento local crescer sem limite. Nenhum contrato de evento (`transcript-event.v2`) muda; nenhuma UI, provedor de IA ou sincronização multi-dispositivo é tocada.

## Technical Context

**Language/Version**: Java 21 (Spring Boot 3.5.3), módulo Maven existente `services/session-core`.

**Primary Dependencies**: `org.xerial:sqlite-jdbc` (novo — motor de armazenamento embarcado em arquivo único, sem processo de servidor, adequado a "local-first"/ADR-0005 e ao futuro empacotamento desktop de `specs/002-desktop-distribution/`). Acesso via JDBC simples (sem Spring Data JPA/Hibernate), no mesmo estilo direto já usado por `SessionRepository`/`SessionController`. Reaproveita Jackson (já transitivo via `spring-boot-starter-web`) para serializar `metadata`/payload de evento como texto JSON em coluna. Nenhuma dependência nova toca captura de áudio, STT ou provedores de IA (P2).

**Storage**: Arquivo SQLite local único (caminho configurável, padrão `data/session-core/memory-hub.db`, criado relativo ao diretório de trabalho do serviço) com duas tabelas — `sessions` e `session_events` — substituindo o `ConcurrentHashMap` como fonte de verdade. Um cache em memória (o próprio `Map` de hoje) continua existindo como camada de leitura rápida, hidratado a partir do SQLite na inicialização do processo (rehydration). Cada `INSERT` de evento é uma transação atômica própria — uma gravação interrompida no meio (crash) não deixa linha parcial visível (grava tudo ou nada), satisfazendo FR-009 sem exigir lógica própria de recuperação de arquivo truncado.

**Testing**: JUnit 5 + `spring-boot-starter-test` (padrão já usado em `SessionRepositoryTest`), com banco SQLite em arquivo temporário (`@TempDir`) por teste — abrir/fechar/reabrir o mesmo arquivo simula restart gracioso; matar o processo de escrita a meio de uma transação (ou interromper antes do commit) simula crash. Sem GPU, sem hardware de áudio, sem STT real (P10/FR-008).

**Target Platform**: Mesmo serviço Linux (WSL/Docker, ADR-0005) do `session-core` hoje; arquivo `.db` fica no filesystem local do host que roda o serviço.

**Project Type**: Extensão de um módulo Maven já existente (`services/session-core`); nenhum serviço/projeto novo.

**Performance Goals**: Sem SLA numérico novo definido pela issue; um `append` de evento não deve introduzir latência perceptível no caminho de ingestão já existente (uma transação SQLite local, sem round-trip de rede).

**Constraints**: Preservar `channelId`/`sourceType`/`label`/`device` e ordem cronológica através de reinícios (FR-002/FR-003); gravação atômica por evento, sem corromper dados já persistidos em caso de crash (FR-009); política de retenção configurável e documentada (FR-004); contrato `transcript-event.v2` inalterado (FR-007); testes automatizados sem GPU/hardware físico (FR-008); armazenamento local-first, sem dependência de serviço remoto (FR-006).

**Scale/Scope**: Duas tabelas novas (`sessions`, `session_events`), uma camada de persistência (`memory` package) por trás da API já existente de `SessionRepository`, uma rotina de expurgo por retenção, e os testes correspondentes (restart gracioso, crash simulado, ordem pós-retomada, expurgo por retenção). Nenhuma UI, nenhum provedor de IA, nenhuma sincronização multi-dispositivo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|---|---|
| P1 — Especificação antes de código | PASS. `spec.md` cobre requisitos, critérios de aceite e fora de escopo, validado pelo checklist de qualidade; gate humano G1 (Spec) segue pendente de confirmação explícita antes do Implement. |
| P2 — Core independente de fornecedores | PASS. SQLite é um motor de armazenamento local genérico, não um fornecedor de STT/LLM; nenhum SDK de provedor de IA é importado por esta feature. |
| P3 — WSL-first | PASS. Java/Maven/testes continuam rodando no WSL; o arquivo SQLite vive no filesystem Linux do serviço; nada de WASAPI/COM é tocado. |
| P4 — Contratos versionados | PASS. `contracts/transcript-event.v2.schema.json` não é alterado (FR-007); o schema SQLite é um detalhe interno de armazenamento do `session-core`, não um contrato público entre serviços — não entra em `contracts/` na raiz do monorepo. |
| P5 — Separação por canal e origem | PASS — é o próprio objetivo desta feature (FR-002/US1/US2): a persistência preserva `channelId`/`sourceType`/`label`/`device` por evento, sem misturar canais. |
| P6 — Isolamento de endpoint de áudio | N/A. Captura e isolamento por processo são responsabilidade do `windows-audio-agent`; esta feature só persiste o resultado já ingerido. |
| P7 — Identidade de dispositivo | N/A. Esta feature apenas armazena o `device`/`endpointId` já recebido, sem resolver ou selecionar dispositivo. |
| P8 — Automação com autorização | PASS. Nenhum merge, force-push ou fechamento de issue automatizado é proposto por este plano. |
| P9 — Privacidade por padrão | PASS com atenção. Diferente do estado atual (memória volátil, perdida a cada restart), o texto transcrito passa a residir em disco de forma durável. Não é introduzida criptografia adicional (conforme Assumptions da spec — consistente com práticas atuais do projeto de não logar conteúdo sensível), mas o plano deve: (a) adicionar o caminho do arquivo `.db` ao `.gitignore` (nunca commitado); (b) não logar o conteúdo do evento em nível `INFO`/`ERROR`, apenas identificadores (`sessionId`/`channelId`/tipo); (c) documentar em `quickstart.md`/`data-model.md` que dados residem em texto plano local, para que uma decisão futura de criptografia em repouso (se necessária) parta de uma base documentada. |
| P10 — Qualidade determinística | PASS. Todos os testes usam SQLite em arquivo temporário (`@TempDir`), sem GPU nem hardware de áudio físico (FR-008). |

Nenhuma violação exige entrada em Complexity Tracking — a única dependência nova (`sqlite-jdbc`) substitui lógica própria de recuperação de arquivo por um motor transacional já testado, reduzindo complexidade em vez de aumentá-la.

## Project Structure

### Documentation (this feature)

```text
specs/013-issue-29-memory-hub-persistence/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Não gerado nesta fase — sem interface externa nova (ver Structure Decision)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
services/session-core/
├── src/main/java/ai/assistanthub/core/
│   ├── session/                                # existente, sem mudança de API pública
│   │   ├── ConversationSession.java
│   │   ├── SessionStatus.java
│   │   ├── SessionRepository.java              # passa a delegar para memory.SessionPersistenceStore,
│   │   │                                        # mantendo save/findById/append/events como hoje
│   │   └── SessionController.java
│   ├── transcript/                             # existente, sem mudança de contrato (FR-007)
│   └── memory/                                 # novo — Memory Hub / persistência local (R3)
│       ├── MemoryHubProperties.java            # caminho do .db + política de retenção (application.yml)
│       ├── MemoryHubDataSource.java            # conexão SQLite + DDL de sessions/session_events na subida
│       ├── SessionPersistenceStore.java        # JDBC: grava/lê sessão e eventos, em ordem, por sessionId
│       ├── RetentionPolicy.java                # aplica limite de tempo/volume/contagem (FR-004)
│       └── MemoryHubStartupRehydrator.java     # na subida, popula o cache em memória a partir do SQLite
├── src/main/resources/application.yml          # + session-core.memory-hub.{path,retention.*}
└── src/test/java/ai/assistanthub/core/memory/
    ├── SessionPersistenceStoreTest.java         # US1: sessão/eventos sobrevivem a reabrir o mesmo arquivo
    ├── SessionPersistenceCrashSafetyTest.java   # US1 edge: gravação interrompida não corrompe o resto (FR-009)
    ├── SessionPersistenceAppendOrderTest.java   # US2: append pós-retomada mantém ordem e canais
    └── RetentionPolicyTest.java                 # US3: expurgo respeita o limite documentado

.gitignore                                       # + caminho padrão de data/session-core/*.db (P9)
```

**Structure Decision**: Extensão do módulo Maven já existente `services/session-core`, sem novo serviço. Todo o código novo entra em um pacote irmão (`memory`) aos pacotes `session`/`transcript` já existentes; `SessionRepository` continua sendo a única API pública consumida por `SessionController` e pelo consumo de eventos v2 (`specs/007-sf-021-session-core-events/`), agora apoiada em `SessionPersistenceStore` em vez de só `ConcurrentHashMap`. Nenhum `contracts/` novo é gerado nesta fase: o schema SQLite é um detalhe de armazenamento interno ao `session-core` (P4), não uma interface exposta a outro serviço ou usuário — se uma feature futura (ex. AI Provider Hub) precisar ler esses dados diretamente, ela define seu próprio contrato de leitura nessa ocasião.

## Complexity Tracking

*Não se aplica — nenhuma violação de Constitution Check identificada.*
