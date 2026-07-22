# Feature Specification: Publicar eventos transcript v2 no session-core (SF-021)

**Feature Branch**: `feature/sf-021-sf-021-publicar-eventos-transcript-v2-no-session`

**Created**: 2026-07-21

**Status**: Draft

**Input**: User description: "Issue #15 — Fazer o session-core consumir eventos transcript-event.v2 (transcript.partial.v2/transcript.final.v2), preservando channelId, sourceType, label e device (endpointId) ponta a ponta."

**Referências**: Issue #15 · Umbrella `specs/001-streaming-foundation/` (item SF-021) · Depende de `specs/004-sf-018-mmdevice-endpoint-id/` (schema v2 e `endpointId`) · Contrato `contracts/transcript-event.v2.schema.json` · Fronteira: `services/transcription-service` publica, `services/session-core` consome.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evento v2 chega à sessão com metadados de canal preservados (Priority: P1)

Um operador mantém uma sessão de conversa vinculada a um ou mais canais de áudio (por exemplo, microfone e áudio do sistema). Enquanto a captura ocorre, o serviço de transcrição publica eventos parciais e finais no contrato `transcript-event.v2` para essa sessão. O session-core recebe cada evento e o registra preservando exatamente `channelId`, `sourceType`, `label` e `device` (`index`/`name`/`endpointId`), sem perda, truncamento ou substituição por valores padrão.

**Why this priority**: É o motivo de existir da issue #15 — sem esta capacidade, a sessão não tem nenhum vínculo com o que foi efetivamente transcrito por canal, e as demais histórias não têm o que testar.

**Independent Test**: Publicar um evento v2 sintético com `channelId`/`sourceType`/`label`/`device` conhecidos para uma sessão ativa e consultar os eventos da sessão, verificando que os metadados retornados são idênticos aos recebidos — sem hardware de áudio, GPU ou modelo STT real.

**Acceptance Scenarios**:

1. **Given** uma sessão existente (qualquer status diferente de `ENDED`) e um canal identificado por `channelId="mic-1"`, `sourceType="microphone"`, **When** chega um evento `transcript.final.v2` para esse `channelId`, **Then** o registro correspondente na sessão contém `channelId`, `sourceType`, `label` e `device` (incluindo `endpointId` quando presente) idênticos aos recebidos.
2. **Given** um evento com `device.endpointId` nulo (dispositivo resolvido apenas por `index`/`name`, cenário legado anterior à SF-018), **When** o evento chega, **Then** session-core aceita normalmente e mantém `endpointId` nulo, sem erro.
3. **Given** um evento `transcript.partial.v2` seguido do `transcript.final.v2` correspondente, **When** ambos chegam, **Then** os dois ficam registrados na sessão em ordem cronológica, sem o parcial ser descartado ou sobrescrito pelo final.

---

### User Story 2 - Canais distintos na mesma sessão não se misturam (Priority: P2)

Uma mesma sessão pode ter canais de origens diferentes ativos simultaneamente (ex.: microfone e sistema). Eventos de `channelId` diferentes precisam permanecer distinguíveis dentro da sessão, sem que o metadado de um canal vaze ou sobrescreva o de outro.

**Why this priority**: É a garantia central de separação por canal (não misturar canais antes da persistência) — sem ela, o registro na sessão vira uma transcrição ambígua, mesmo que a User Story 1 funcione para um canal isolado.

**Independent Test**: Enviar eventos v2 intercalados de dois `channelId` diferentes para a mesma sessão e verificar que cada evento consultado mantém o `channelId`/`sourceType`/`device` de origem corretos, na ordem de chegada, sem contaminação cruzada.

**Acceptance Scenarios**:

1. **Given** uma sessão com dois canais ativos (`channelId` "mic" e "system"), **When** eventos de ambos chegam intercalados, **Then** cada evento registrado mantém o `channelId` de origem correto.
2. **Given** eventos de dois canais diferentes com texto transcrito coincidentemente igual, **When** ambos chegam, **Then** permanecem como registros distintos (não deduplicados por conteúdo do texto).

---

### User Story 3 - Consumo não vira orquestração e evento inválido não derruba a sessão (Priority: P3)

O session-core atua estritamente como consumidor dos eventos de transcrição: não envia comandos de controle (iniciar/parar/reconfigurar captura) de volta ao serviço de transcrição, e um evento malformado ou de sessão desconhecida não interrompe a sessão nem o serviço — é rejeitado e registrado em log.

**Why this priority**: É um critério de aceite explícito da issue ("transcription não vira orquestrador de sessão") e protege a estabilidade do sistema; vem depois das duas histórias anteriores porque é uma garantia de robustez de fronteira, não o fluxo principal de valor.

**Independent Test**: Enviar um evento sem um campo obrigatório do contrato v2 (ex.: sem `device`) e um evento referenciando um `sessionId` inexistente/encerrado; verificar que ambos são rejeitados sem alterar o estado de sessões existentes; confirmar, por inspeção do desenho da fronteira, que não existe nenhum caminho do session-core que envie uma instrução de controle ao serviço de transcrição.

**Acceptance Scenarios**:

1. **Given** um evento que não está conforme o contrato `transcript-event.v2` (campo obrigatório ausente), **When** o session-core o recebe, **Then** o evento é rejeitado e registrado em log, sem afetar o estado atual da sessão.
2. **Given** um evento referenciando um `sessionId` que não existe ou já foi encerrado, **When** é recebido, **Then** é descartado sem criar sessão implícita nem interromper outros fluxos em andamento.

---

### Edge Cases

- O que acontece quando o serviço de transcrição reconecta e reenvia um evento já entregue (reentrega "no mínimo uma vez")? Assume-se registro duplicado, sem deduplicação (ver Assumptions).
- O que acontece quando um `channelId` que ainda não apareceu na sessão chega em um evento (sessão criada sem lista prévia de canais)? Assume-se reconhecimento implícito a partir do próprio evento.
- O que acontece se o serviço de transcrição, durante uma janela de transição, ainda enviar eventos no contrato `v1` (sem `device`/`endpointId`)? Fora do escopo desta feature — session-core não consumia eventos de transcrição antes desta issue, portanto não há compatibilidade retroativa a preservar (ver Assumptions).
- O que acontece com eventos que chegam para uma sessão em estado terminal (encerrada) logo após o encerramento? São descartados como sessão desconhecida, mesmo comportamento do cenário de `sessionId` inexistente.
- O que acontece com um evento para uma sessão ainda em `CREATED` (criada, mas sem transição formal para `ACTIVE`)? É aceito normalmente — `CREATED` não é `ENDED`, portanto não é tratada como sessão desconhecida (ver FR-004).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Session-core MUST aceitar e ingerir eventos `transcript-event.v2` (`transcript.partial.v2` e `transcript.final.v2`) publicados pelo serviço de transcrição, associados a uma sessão existente via `sessionId`.
- **FR-002**: Session-core MUST preservar, sem alteração, os campos `channelId`, `sourceType`, `label` e `device` (`index`, `name`, `endpointId`) exatamente como recebidos em cada evento ingerido.
- **FR-003**: Session-core MUST manter eventos de `channelId` diferentes dentro da mesma sessão como registros distinguíveis, nunca fundindo ou sobrescrevendo o metadado de um canal com o de outro.
- **FR-004**: Session-core MUST rejeitar, sem falhar o serviço nem a sessão como um todo, qualquer evento que não esteja em conformidade com o contrato `transcript-event.v2` ou que referencie uma sessão inexistente ou já encerrada (`SessionStatus.ENDED`). Uma sessão em `CREATED` (sem transição formal para `ACTIVE` — mecanismo que não existe hoje no session-core) é considerada existente e elegível para receber eventos; apenas a ausência da sessão ou o status `ENDED` causam rejeição.
- **FR-005**: Session-core MUST NOT emitir nenhuma ação de controle/orquestração (iniciar, parar ou reconfigurar captura) em direção ao serviço de transcrição como consequência de ingerir esses eventos — permanece um consumidor passivo.
- **FR-006**: A fronteira de consumo (transcrição publica / session-core consome) e suas regras de compatibilidade MUST ser documentadas, incluindo o fato de que apenas o contrato v2 é suportado por esta feature.
- **FR-007**: Testes automatizados (Java e/ou de contrato) MUST verificar a ingestão, a preservação de metadados e a separação por canal descritas acima, sem depender de GPU ou hardware de áudio físico.
- **FR-008**: Eventos ingeridos com seus metadados preservados MUST ser consultáveis por sessão, de forma consistente com a capacidade de consulta de eventos já existente no session-core.

### Key Entities *(include if feature involves data)*

- **Evento de transcrição v2**: representa uma transcrição parcial ou final produzida para um canal de áudio; atributos principais são `sessionId`, `channelId`, `label`, `sourceType`, `device` (`index`/`name`/`endpointId`), texto, idioma e instante de ocorrência. Definido pelo contrato `contracts/transcript-event.v2.schema.json`; é produzido pelo serviço de transcrição e apenas consumido por esta feature.
- **Sessão de conversa**: agrupa canais e seus eventos ao longo de uma conversa; já existe no session-core hoje, mas sem nenhum vínculo com metadados de canal/dispositivo de transcrição.
- **Registro de evento na sessão**: materialização, dentro da sessão, de um evento de transcrição recebido — preserva os metadados de canal/dispositivo de origem para consulta e uso futuro (ex.: apresentação, memória).
- **Canal**: identificado pela combinação `channelId` + `sourceType` + `device`; múltiplos canais podem coexistir na mesma sessão e devem permanecer distinguíveis entre si.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos eventos v2 ingeridos em teste retêm `channelId`, `sourceType`, `label` e `device` idênticos aos recebidos quando consultados posteriormente na sessão.
- **SC-002**: Em cenários com dois ou mais canais simultâneos na mesma sessão, 0% dos eventos têm seu canal de origem trocado ou sobrescrito.
- **SC-003**: Um evento malformado ou de sessão desconhecida nunca interrompe uma sessão ativa — 0% de perda de eventos válidos ou de interrupção de sessão causada por entrada inválida nos testes.
- **SC-004**: 100% dos testes automatizados desta fronteira (ingestão, preservação de metadados, separação de canal, rejeição de evento inválido) passam sem exigir GPU ou hardware de áudio físico.
- **SC-005**: A documentação da fronteira de compatibilidade (o que é e o que não é suportado nesta versão) existe e é suficiente para um novo desenvolvedor decidir o comportamento esperado sem precisar ler o código-fonte do session-core.

## Assumptions

- O contrato `transcript-event.v1` não é consumido pelo session-core nesta feature — apenas `v2` é considerado, já que o session-core não consumia nenhum evento de transcrição antes desta issue (não há compatibilidade retroativa a resolver).
- A entrega de eventos é "no mínimo uma vez" (at-least-once); esta feature não implementa deduplicação — eventos duplicados podem gerar registros distintos, mesmo comportamento já existente para os eventos genéricos de sessão hoje.
- Um canal (`channelId`) não precisa ser pré-cadastrado na sessão antes do primeiro evento chegar; ele é reconhecido implicitamente a partir dos metadados do próprio evento recebido.
- A persistência dos eventos ingeridos segue o mesmo modelo em memória já usado pela sessão hoje; persistência durável em banco (Memory Hub / R3) está fora de escopo, conforme definido na issue.
- O transporte concreto de entrega dos eventos entre os dois serviços (ex.: assinatura em tempo real vs. chamada síncrona) é decisão de arquitetura a ser definida em `/speckit-plan`, não desta especificação.
- Os testes desta feature usam eventos de transcrição sintéticos/fake, sem depender de GPU, hardware de áudio real ou execução de modelo STT.
- Captura por processo isolado (SF-020) e qualquer superfície de UI desktop estão fora de escopo desta feature.
