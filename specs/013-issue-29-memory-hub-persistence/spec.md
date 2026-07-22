# Feature Specification: Memory Hub — persistência local de sessão e eventos (R3)

**Feature Branch**: `feature/issue-29-r3-memory-hub-persist-ncia-local-de-sess-o-e-eve`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Issue #29 — [R3] Memory Hub — persistência local de sessão e eventos. Persistir sessões e eventos transcript além da memória volátil do session-core: append de eventos por sessionId/canal, retomada após restart, retenção/limites documentados, testes sem GPU, local-first. Fora de escopo: UI desktop, AI providers, sync multi-device."

**Referências**: Issue #29 · Depende de `specs/007-sf-021-session-core-events/` (session-core já ingere `transcript-event.v2` em memória via `SessionRepository`/`ConversationSession`) · Contrato `contracts/transcript-event.v2.schema.json` (não deve mudar) · ADR-0005 (WSL-first / local-first).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sessão e eventos preservados após reinício do serviço (Priority: P1)

Um operador está usando o Assistant Hub AI durante uma conversa; a sessão registra eventos de transcrição de um ou mais canais (ex.: microfone e áudio do sistema). O serviço session-core é reiniciado — por atualização, crash ou reinício manual — durante ou depois da conversa. Ao voltar, o operador consulta a mesma sessão e todos os eventos gravados antes do reinício continuam disponíveis, com os mesmos metadados de canal.

**Why this priority**: É o motivo de existir da issue #29 (R3) — hoje sessão e eventos vivem só em `ConcurrentHashMap` e desaparecem a cada restart do processo; sem sobreviver a um reinício, o Memory Hub não cumpre seu propósito, e as demais histórias não têm o que testar.

**Independent Test**: Criar uma sessão, enviar eventos `transcript-event.v2` sintéticos para um ou mais canais, reiniciar o processo do session-core (ou reidratar o repositório a partir do armazenamento persistido) e consultar a sessão, comparando campo a campo com o que foi enviado — sem GPU nem hardware de áudio real.

**Acceptance Scenarios**:

1. **Given** uma sessão ativa com eventos registrados em 2 canais, **When** o processo do session-core é reiniciado, **Then** a sessão e todos os eventos continuam consultáveis com os mesmos `channelId`, `sourceType`, `label`, `device` e texto.
2. **Given** uma sessão criada mas ainda sem nenhum evento, **When** o serviço reinicia, **Then** a sessão em si (metadados, status) permanece consultável mesmo sem eventos.
3. **Given** um reinício abrupto do processo (sem shutdown gracioso) ocorrido depois que eventos já foram confirmados como gravados, **When** o serviço volta, **Then** nenhum desses eventos previamente confirmados é perdido.

---

### User Story 2 - Novos eventos após retomada continuam na mesma linha do tempo (Priority: P2)

Depois que uma sessão é retomada após um reinício, a conversa continua e novos eventos de transcrição seguem chegando — para os mesmos canais de antes ou para canais novos. Esses eventos precisam se juntar de forma consistente ao que já existia antes da interrupção, preservando ordem cronológica e sem misturar canais.

**Why this priority**: Garante que a persistência é um fluxo contínuo de apêndice (append), não apenas "salvar e carregar uma vez" — é o padrão real de uso (a conversa não para no reinício do serviço), e depende de que a User Story 1 já exista.

**Independent Test**: Retomar uma sessão persistida, enviar novos eventos v2 para um canal já existente e para um canal novo, consultar a sessão e verificar que a lista combinada (antes + depois do reinício) está em ordem cronológica correta, sem cross-contaminação de canal.

**Acceptance Scenarios**:

1. **Given** uma sessão retomada após reinício com eventos prévios do canal "mic", **When** um novo evento do canal "mic" chega, **Then** ele aparece depois dos eventos prévios, na ordem correta, sem sobrescrever nenhum deles.
2. **Given** uma sessão retomada, **When** um evento de um canal novo ("system") chega pela primeira vez após o reinício, **Then** é aceito e persistido distintamente do canal "mic", com o mesmo comportamento de não mistura já garantido em memória hoje.

---

### User Story 3 - Política de retenção documentada evita crescimento não controlado (Priority: P3)

Como os dados de sessão agora sobrevivem além do tempo de vida do processo, precisa existir — e estar documentada — uma política de retenção/limites para sessões e eventos, para que o armazenamento local não cresça indefinidamente sem controle nem conhecimento do operador.

**Why this priority**: É um critério de aceite explícito da issue ("retenção/limites documentados"), mas é uma garantia operacional que só faz sentido depois que a persistência (US1/US2) já existe — sem dados persistidos, não há o que reter ou expurgar.

**Independent Test**: Consultar a documentação da feature e confirmar que descreve claramente o que é retido, por quanto tempo/volume, e o que acontece ao atingir o limite; em teste automatizado, gravar eventos além de um limite configurado e verificar que a política documentada é aplicada sem falhar novas gravações.

**Acceptance Scenarios**:

1. **Given** a documentação da feature, **When** um desenvolvedor ou operador a consulta, **Then** encontra a política de retenção padrão e como ajustá-la, sem precisar ler o código-fonte do session-core.
2. **Given** um limite de retenção configurado em teste, **When** o volume de dados persistidos excede esse limite, **Then** os dados mais antigos são expurgados conforme documentado e novas gravações continuam funcionando normalmente.

---

### Edge Cases

- O que acontece se o processo é encerrado abruptamente (crash) no meio da gravação de um evento? O evento incompleto não pode corromper os demais dados já gravados da sessão (ver FR-009).
- O que acontece quando o armazenamento local atinge o limite de retenção configurado? Os dados mais antigos são expurgados conforme a política documentada, sem que isso falhe a gravação de novos eventos.
- O que acontece ao consultar uma sessão criada em uma execução anterior à ativação desta feature (sem registro persistido correspondente)? Retorna "sessão não encontrada" — mesmo comportamento já existente hoje para uma sessão inexistente.
- O que acontece se eventos do mesmo canal chegarem em rápida sucessão durante a janela em que o serviço ainda está subindo após um reinício? Todos são aceitos e persistidos na ordem de chegada assim que o serviço estiver pronto; nenhum é descartado silenciosamente.
- O que acontece se o contrato de transcrição evoluir para uma versão futura (v3)? Fora do escopo desta feature — apenas `transcript-event.v2` é suportado; qualquer migração de dado persistido para uma versão futura é tratada e documentada em feature própria quando ocorrer.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Session-core MUST persistir sessões (`ConversationSession`) e seus eventos ingeridos em armazenamento local durável, de forma que sobrevivam ao encerramento e reinício do processo.
- **FR-002**: Session-core MUST manter, após persistência, a mesma capacidade de "append" incremental de eventos por `sessionId` e a mesma preservação de `channelId`, `sourceType`, `label` e `device` já garantida em memória (`specs/007-sf-021-session-core-events/`), agora também através de reinícios.
- **FR-003**: Session-core MUST preservar a ordem cronológica de chegada dos eventos de uma sessão, tanto antes quanto depois de um reinício, sem reordenar eventos já persistidos.
- **FR-004**: Session-core MUST expor e documentar uma política de retenção/limites (por tempo, volume ou contagem) para sessões e eventos persistidos, evitando crescimento não controlado do armazenamento local.
- **FR-005**: Session-core MUST permitir consultar sessões e seus eventos por `sessionId` após um reinício, com o mesmo contrato de leitura hoje oferecido por `SessionRepository.findById`/`events` em memória.
- **FR-006**: A persistência MUST ser local-first — sem dependência de serviço remoto ou nuvem para funcionar — consistente com ADR-0005 e `docs/vision.md`.
- **FR-007**: O contrato `transcript-event.v2` MUST permanecer inalterado por esta feature; qualquer campo adicional necessário para fins de armazenamento é interno e não MUST vazar para o contrato público sem uma evolução documentada explicitamente.
- **FR-008**: Testes automatizados MUST verificar a persistência e a retomada de sessões/eventos após reinício simulado (gracioso e abrupto), sem depender de GPU ou hardware de áudio real.
- **FR-009**: Session-core MUST tratar de forma segura uma gravação interrompida no meio (crash durante um append), sem corromper ou perder os demais eventos/sessões já persistidos.
- **FR-010**: Session-core MUST continuar rejeitando, sem falhar o serviço, eventos malformados ou de sessão inexistente/encerrada, mesmo com a camada de persistência introduzida (preservando a garantia já estabelecida em `specs/007-sf-021-session-core-events/`).

### Key Entities *(include if feature involves data)*

- **Sessão de conversa (`ConversationSession`)**: já existe hoje apenas em memória; passa a ser persistida localmente, preservando `id`, `title`, `profileId`, `status`, `createdAt`/`startedAt`/`endedAt` e metadados através de reinícios do processo.
- **Registro de evento na sessão**: materialização de um evento de transcrição (`transcript-event.v2`) já ingerido pela sessão (`specs/007-sf-021-session-core-events/`); passa a ser persistido com os mesmos metadados de canal/dispositivo, mantendo ordem cronológica.
- **Política de retenção**: regra documentada que determina até quando (tempo, volume ou contagem) uma sessão ou seus eventos permanecem no armazenamento local antes de serem elegíveis para expurgo.
- **Armazenamento local (Memory Hub)**: componente de durabilidade que substitui a estrutura em memória (`ConcurrentHashMap`) como fonte de verdade para sessões e eventos; a tecnologia concreta é decisão de arquitetura a ser definida em `/speckit-plan`, não desta especificação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das sessões e eventos gravados com sucesso antes de um reinício do serviço continuam disponíveis e idênticos (mesmos campos, mesma ordem) após o reinício, em testes automatizados.
- **SC-002**: Um operador ou desenvolvedor consegue determinar, a partir da documentação, exatamente o que é retido, por quanto tempo/volume por padrão, e o que acontece ao atingir o limite — sem examinar o código-fonte.
- **SC-003**: 0% de perda de eventos válidos confirmados como gravados antes de uma interrupção abrupta (crash) simulada em teste.
- **SC-004**: O contrato de eventos de transcrição consumido por esta feature permanece 100% compatível com `transcript-event.v2` já publicado, verificado por teste de contrato, sem exigir mudança no serviço de transcrição.
- **SC-005**: 100% dos testes de persistência e retomada desta feature rodam sem GPU e sem hardware de áudio físico.

## Assumptions

- Retenção padrão: na ausência de configuração explícita, os dados são mantidos indefinidamente; um limite (tempo, volume ou contagem) é configurável e documentado, mas não exige interface gráfica — consistente com "UI desktop fora de escopo" definido na issue.
- "Reinício" cobre tanto um encerramento gracioso do processo quanto um término abrupto (crash); os testes desta feature cobrem os dois casos.
- Não existe dado persistido anterior a esta feature para migrar — sessões e eventos de execuções passadas viviam apenas em memória e já eram perdidos a cada restart; esta feature não precisa de rotina de migração de dados legados.
- A tecnologia concreta de armazenamento local (arquivo, banco embarcado, etc.) é decisão de arquitetura definida em `/speckit-plan`, não desta especificação.
- Um único processo session-core é o escritor da persistência local; concorrência de múltiplos processos/instâncias escrevendo na mesma base e sincronização entre dispositivos estão fora de escopo (consistente com "sync multi-device fora de escopo" da issue).
- Provedores de IA (`specs/003-ai-provider-hub/`) e UI desktop (`specs/002-desktop-distribution/`) não são afetados nem exercitados por esta feature, conforme delimitado na issue #29.
- O contrato `transcript-event.v2` não muda; se a persistência exigir campos técnicos adicionais (ex.: identificadores internos de armazenamento), eles permanecem internos ao session-core e fora do contrato público.
