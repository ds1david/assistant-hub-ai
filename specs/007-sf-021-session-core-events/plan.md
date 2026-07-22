# Implementation Plan: Publicar eventos transcript v2 no session-core (SF-021)

**Branch**: `007-sf-021-session-core-events` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-sf-021-session-core-events/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

O `session-core` passa a consumir os eventos `transcript.partial.v2`/`transcript.final.v2` já publicados pelo `transcription-service` no feed WebSocket global `/ws/transcripts`, associando cada evento à sessão correta via `sessionId` e preservando `channelId`, `sourceType`, `label` e `device` (`index`/`name`/`endpointId`) sem alteração. Tecnicamente, isso é um novo cliente WebSocket dentro do `session-core` que decodifica cada evento, valida contra `contracts/transcript-event.v2.schema.json`, mapeia para o `HubEvent` já existente (reaproveitando o campo `correlation` para os metadados de canal/dispositivo) e o anexa ao `SessionRepository` em memória — sem nenhuma mudança de contrato, sem nova persistência durável e sem que o `session-core` envie qualquer comando de volta ao `transcription-service`.

## Technical Context

**Language/Version**: Java 21 (Spring Boot 3.5.3), módulo Maven existente `services/session-core`.

**Primary Dependencies**: `spring-boot-starter-web`/`spring-boot-starter-validation` (já presentes) + `spring-boot-starter-websocket` (novo, cliente WebSocket para consumir `/ws/transcripts`) + `networknt:json-schema-validator` (novo, escopo de teste, para validar eventos sintéticos contra `contracts/transcript-event.v2.schema.json` — mesmo arquivo já validado pelo lado Python em `services/transcription-service/tests/test_ws_audio_contract.py`). Reaproveita `plugin-sdk-java`/`HubEvent` (já existente, com o campo `correlation: Map<String,String>`) como representação interna, sem alterar o SDK compartilhado.

**Storage**: Em memória, reaproveitando o `SessionRepository` (`ConcurrentHashMap`) já existente. Sem banco novo — persistência durável (Memory Hub/R3) está fora de escopo (ver spec Assumptions).

**Testing**: JUnit 5 + `spring-boot-starter-test` (padrão já usado em `SessionRepositoryTest`), acrescido de testes de contrato (evento sintético validado contra o schema v2) e testes de integração do cliente WebSocket com um servidor fake em memória — sem GPU, sem hardware de áudio, sem STT real.

**Target Platform**: Serviço Linux (WSL/Docker, ADR-0005), mesmo ambiente do `session-core` hoje. O `transcription-service` é alcançado por uma URL base configurável (`application.yml`/variável de ambiente); `session-core` ainda não está no `infra/compose/docker-compose.yml` (que hoje só define o serviço `transcription`) e esta feature não exige adicioná-lo lá.

**Project Type**: Serviço backend dentro do monorepo existente — extensão de um módulo Maven já existente (`services/session-core`); nenhum projeto/módulo novo.

**Performance Goals**: Sem SLA numérico novo definido pela issue; herda o objetivo qualitativo de baixa latência já rastreado por `specs/001-streaming-foundation` (métricas de p50/p95 por canal já expostas pelo `transcription-service`). A ingestão no `session-core` não deve introduzir um novo gargalo perceptível; nenhum número formal é fixado nesta feature.

**Constraints**: Preservar `channelId`/`sourceType`/`label`/`device` sem alteração (FR-002); nunca fundir eventos de canais diferentes (FR-003); nunca emitir comando de controle de volta ao `transcription-service` (FR-005); testes automatizados sem GPU/hardware de áudio (FR-007); sem persistência durável nova (Assumptions).

**Scale/Scope**: Uma feature dentro de um serviço já existente — um cliente WebSocket de saída, um mapeador de evento v2 → `HubEvent`, configuração de conexão e os testes correspondentes; nenhum serviço novo, nenhum armazenamento persistente novo, nenhuma UI.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|---|---|
| P1 — Especificação antes de código | PASS. `spec.md` já cobre requisitos, critérios de aceite e fora de escopo antes deste plano; o gate humano G1 (Spec) segue pendente de confirmação explícita antes do Implement, conforme a sequência oficial. |
| P2 — Core independente de fornecedores | PASS. Nenhum SDK de fornecedor de IA é importado; o consumo é de um feed interno já existente do próprio `transcription-service`. |
| P3 — WSL-first | PASS. Java/Maven/testes continuam rodando no WSL; nada de WASAPI/COM é tocado por esta feature. |
| P4 — Contratos versionados | PASS. `contracts/transcript-event.v2.schema.json` não é alterado (consumido como está); o mapeamento interno para `HubEvent` reaproveita o campo genérico `correlation` já existente no SDK compartilhado, sem ampliar esse contrato. |
| P5 — Separação por canal e origem | PASS — é o próprio objetivo da feature (FR-002/FR-003/US1/US2). |
| P6 — Isolamento de endpoint de áudio | N/A. Captura e isolamento por processo são responsabilidade do `windows-audio-agent`; esta feature só consome o resultado já publicado. |
| P7 — Identidade de dispositivo | N/A para decisão de seleção — o `session-core` apenas armazena o `device`/`endpointId` recebido, não resolve dispositivo. |
| P8 — Automação com autorização | PASS. Nenhum merge/force-push/fechamento de issue automatizado é proposto por este plano. |
| P9 — Privacidade por padrão | PASS com atenção: eventos rejeitados (FR-004) devem logar `type`/`channelId`/`sessionId` para diagnóstico, sem necessidade de dump do texto transcrito completo em nível de erro; nenhum segredo/token/áudio bruto é introduzido em log por esta feature. |
| P10 — Qualidade determinística | PASS. Todos os testes planejados usam eventos sintéticos/fake WebSocket server, sem GPU nem hardware físico (FR-007). |

Nenhuma violação exige entrada em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
services/session-core/
├── src/main/java/ai/assistanthub/core/
│   ├── session/                          # existente: ConversationSession, SessionStatus,
│   │                                      # SessionRepository, SessionController
│   └── transcript/                       # novo
│       ├── TranscriptEventV2.java        # DTO espelhando contracts/transcript-event.v2.schema.json
│       ├── TranscriptEventValidator.java # validação de contrato (rejeita evento malformado — FR-004)
│       ├── TranscriptEventMapper.java    # v2 event -> HubEvent (payload + correlation — FR-002/FR-003)
│       ├── TranscriptFeedClient.java     # cliente WebSocket para /ws/transcripts, com reconexão
│       └── TranscriptIngestionProperties.java # URL base do transcription-service (application.yml)
├── src/main/resources/application.yml    # + propriedade da URL do feed de transcrição
└── src/test/java/ai/assistanthub/core/transcript/
    ├── TranscriptContractTest.java                # Foundational: valida fixtures contra contracts/transcript-event.v2.schema.json
    ├── TranscriptEventMapperTest.java              # US1: preservação de metadados (endpointId presente/nulo)
    ├── TranscriptFeedClientHappyPathTest.java      # US1: partial+final em ordem, ponta a ponta
    ├── TranscriptFeedClientMultiChannelTest.java   # US2: canais distintos não se misturam
    └── TranscriptFeedClientResilienceTest.java     # US3: evento malformado/sessão desconhecida não derruba nada

contracts/transcript-event.v2.schema.json  # existente na raiz do monorepo, consumido sem alteração (P4)
```

**Structure Decision**: Extensão de um módulo Maven já existente (`services/session-core`), sem novo serviço nem novo projeto. Todo o código novo fica em um pacote irmão (`transcript`) ao pacote `session` já existente, evitando acoplamento do modelo de sessão ao formato específico do evento de transcrição — o acoplamento passa pelo `TranscriptEventMapper`, que traduz para o `HubEvent` genérico já consumido por `SessionRepository`/`SessionController` hoje.

## Complexity Tracking

*Não se aplica — nenhuma violação de Constitution Check identificada.*
