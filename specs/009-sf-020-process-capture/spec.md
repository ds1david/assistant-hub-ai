# Feature Specification: Captura de áudio por processo (WASAPI loopback por app)

**Feature Branch**: `009-sf-020-process-capture`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "[SF-020] Captura de áudio por processo (WASAPI loopback por app). Objetivo: capturar áudio de processo/aplicativo específico via WASAPI, isolado por canal, sem quebrar endpointId nem o contrato transcript-event.v2. Escopo: descoberta/seleção por processo (PID ou nome de app); loopback por processo integrado ao worker de canal existente; compatível com hot-plug (SF-019) e profiles com endpointId (SF-018); testes com fakes/mocks no Linux, evidência Windows em docs/validation/. Fora de escopo: UI desktop, persistência de sessão, adaptive window (já entregue). Critérios de aceite: canal pode ser ligado a um processo alvo; metadados v2 (channelId, sourceType, device) preservados; falha explícita se processo/endpoint sumir (sem fallback silencioso); testes automatizados verdes sem GPU."

## Clarifications

### Session 2026-07-22

- Q: A seleção por processo deve ser restrita a processos da mesma sessão/usuário do operador, ou pode alvejar qualquer processo visível ao SO (incluindo processos de sistema ou de outro usuário)? → A: Restringir a processos da mesma sessão/usuário do operador — nunca processos de sistema/kernel nem de outro usuário na mesma máquina.
- Q: Quando um canal seleciona o alvo por NOME do processo e esse app reinicia durante a sessão (PID novo), o canal deve seguir automaticamente a nova instância, ou tratar isso como o processo desaparecido (falha explícita)? → A: Re-seguir automaticamente por nome — análogo a uma chegada de hot-plug (SF-019); aplica-se somente à seleção por nome, nunca à seleção por PID (identidade exata, sem conceito de "restart").

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operador liga um canal a um processo/aplicativo específico (Priority: P1)

Um operador quer capturar o áudio de um aplicativo específico (ex.: uma aba do navegador, um app de conferência) via WASAPI loopback, isolado por canal — em vez de capturar um dispositivo de saída físico inteiro, que hoje mistura o áudio de todos os aplicativos que tocam nele. O operador seleciona o alvo por PID ou por nome do processo/aplicativo no canal do perfil. Os eventos de transcrição resultantes desse canal preservam os mesmos metadados v2 (`channelId`, `sourceType`, `device`) que os canais baseados em dispositivo já produzem hoje, sem exigir tratamento especial por quem consome esses eventos (session-core, dashboard).

**Why this priority**: É a capacidade central pedida pela issue #19 — sem ela, não existe captura por processo, apenas a captura por dispositivo físico já existente (SF-018).

**Independent Test**: Configurar um canal de perfil apontando para um processo/aplicativo em execução (por nome ou PID), iniciar uma sessão e confirmar que o áudio capturado nesse canal corresponde apenas ao processo alvo, e que os eventos de transcrição desse canal carregam os mesmos campos v2 obrigatórios que qualquer outro canal.

**Acceptance Scenarios**:

1. **Given** um canal de perfil configurado para um processo em execução (por nome ou PID), **When** o operador inicia uma sessão, **Then** o áudio capturado nesse canal fica limitado ao processo alvo, e os eventos de transcrição desse canal contêm `sessionId`, `channelId`, `label`, `sourceType`, `device`, `text`, `latencyMs` e `occurredAt` como qualquer outro canal.
2. **Given** dois canais na mesma sessão — um por processo, outro por dispositivo (`endpointId`, SF-018) —, **When** ambos capturam simultaneamente, **Then** o áudio e os metadados de um canal nunca se misturam com os do outro (isolamento por canal, ADR-0007).

---

### User Story 2 - Falha explícita quando o processo alvo desaparece (Priority: P2)

Se o processo/aplicativo alvo de um canal encerra ou deixa de ter uma sessão de áudio ativa durante a captura, o canal precisa falhar de forma explícita e identificável — não pode silenciosamente trocar para outro processo/dispositivo, nem simplesmente parar de produzir transcrição sem sinalizar o motivo. Isso preserva a mesma filosofia de "sem fallback silencioso" já aplicada a `endpointId` (SF-018/P7) e a eventos de hot-plug (SF-019). Exceção deliberada (Clarifications): quando o canal foi selecionado por **nome** do processo (não por PID) e uma nova instância inequívoca daquele nome aparece depois do encerramento, o canal re-segue automaticamente essa nova instância — análogo à chegada (arrival) de hot-plug — em vez de falhar; a falha explícita permanece o comportamento para seleção por **PID** (identidade exata, sem conceito de "restart") e para qualquer caso em que a nova instância por nome seja ambígua (FR-005).

**Why this priority**: Evita perda ou atribuição incorreta de dados de transcrição — um canal que muda de fonte silenciosamente, ou que só para sem nenhum sinal, corrompe a confiança nos dados da sessão.

**Independent Test**: Em teste automatizado (WSL, sem hardware), simular o desaparecimento do processo alvo (fake/mocked) durante a captura e confirmar que o canal reporta um erro específico e identificável, sem tentar continuar capturando de outro processo/dispositivo e sem derrubar os demais canais da sessão.

**Acceptance Scenarios**:

1. **Given** um canal selecionado por **PID** capturando loopback de um processo específico, **When** esse processo encerra, **Then** o canal loga/levanta um erro distinto e identificável (citando o processo alvo) em vez de se reconectar silenciosamente a outro processo ou dispositivo — nunca re-segue automaticamente (PID é identidade exata).
2. **Given** a mesma falha, **When** ela ocorre, **Then** ela não derruba o supervisor nem os demais canais da sessão (isolamento por canal, ADR-0007/P6).
3. **Given** um canal selecionado por **nome** de processo, **When** o processo alvo encerra e uma única nova instância com o mesmo nome inicia em seguida, **Then** o canal resolve automaticamente essa nova instância e retoma a captura, sem falha explícita nem reinicialização manual do canal.
4. **Given** o mesmo canal por nome, **When** o processo encerra e múltiplas novas instâncias com o mesmo nome aparecem (ambíguo), **Then** o canal falha de forma explícita (mesma política de ambiguidade de FR-005) em vez de escolher uma instância arbitrariamente.

---

### User Story 3 - Compatibilidade validada com hot-plug e perfis existentes (Priority: P3)

Como mantenedor responsável por aprovar esta feature, preciso confirmar que a captura por processo convive corretamente com a captura por dispositivo já existente (`endpointId`, SF-018) e com o listener de hot-plug (SF-019) na mesma sessão/perfil, validado em hardware Windows real — para que esta feature não regrida o caminho de captura por dispositivo já entregue.

**Why this priority**: Cumpre P10 (validação manual documentada) e é o critério de saída do gate G3 (Validate); é a prova de que a nova capacidade não interfere nas duas já entregues.

**Independent Test**: Rodar uma sessão com um perfil misturando um canal por processo e um canal por `endpointId`, provocar um evento de hot-plug no canal por dispositivo e confirmar, em hardware Windows real, que o comportamento de hot-plug (SF-019) permanece inalterado e que o canal por processo continua capturando normalmente.

**Acceptance Scenarios**:

1. **Given** um perfil com um canal por processo e um canal por `endpointId` na mesma sessão, **When** ocorre um evento de hot-plug no `endpointId` do canal por dispositivo, **Then** o comportamento de hot-plug já especificado em `specs/006-sf-019-hotplug-listener/` permanece inalterado, e o canal por processo não é afetado.

---

### Edge Cases

- O que acontece se o nome do processo/aplicativo corresponder a múltiplos processos em execução (ambíguo)? Falha explícita na resolução — mesma filosofia de "sem fallback silencioso" já usada para `nameRegex` ambíguo em SF-018 (P7); não escolhe um processo arbitrariamente.
- O que acontece se o processo alvo está em execução mas ainda não tem nenhuma sessão de áudio ativa (nenhum som tocando ainda)? O canal aguarda uma sessão de áudio aparecer, em vez de falhar imediatamente — desde que o processo em si exista e seja resolvido de forma não ambígua.
- O que acontece se dois canais diferentes forem configurados para o mesmo processo alvo? Cada canal mantém sua própria captura isolada (ADR-0007) — não há restrição de exclusividade entre canais quanto ao processo alvo.
- O que acontece com um canal por processo cujo alvo nunca existiu desde o início da sessão (processo nunca rodou)? Falha explícita e permanente no startup do canal — mesmo comportamento de fail-fast já especificado para um `endpointId` nunca resolvido (SF-018).
- O que acontece se o processo/PID indicado pertence a outro usuário ou é um processo de sistema/kernel? Falha explícita e permanente no startup do canal (fora do escopo permitido, FR-011) — nunca tenta capturar mesmo que o processo exista e seja tecnicamente visível ao SO.
- O que acontece quando um canal selecionado por **PID** perde o processo? Falha explícita e permanente para aquele canal — PID nunca re-segue uma nova instância, mesmo que um processo com o mesmo nome reapareça (Clarifications; diferente do comportamento de re-seguir por nome, FR-012).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir configurar a fonte de áudio de um canal como um processo/aplicativo específico (por PID ou por nome de processo/aplicativo), como alternativa aos seletores de dispositivo já existentes (`endpointId`, `index`, `nameRegex`, `default`).
- **FR-002**: Um canal configurado por processo MUST capturar, via loopback WASAPI, somente o áudio da(s) sessão(ões) de áudio daquele processo — isolado por canal, sem misturar com outro processo ou canal (mesma isolação de um processo por endpoint já especificada em ADR-0007/P6).
- **FR-003**: Eventos de transcrição produzidos por um canal por processo MUST preencher os mesmos campos obrigatórios do contrato `transcript-event.v2` (`sessionId`, `channelId`, `label`, `sourceType`, `device`, `text`, `latencyMs`, `occurredAt`) que canais por dispositivo já produzem; qualquer metadado específico de processo (ex.: nome/PID do processo) MUST ser adicionado apenas como campo adicional opcional, nunca substituindo ou quebrando os campos já obrigatórios (P4 — contratos aditivos).
- **FR-004**: O sistema MUST NOT cair em fallback silencioso — nem para um processo diferente do resolvido de forma inequívoca, nem para um dispositivo físico — quando a seleção por processo for ambígua (múltiplos processos correspondendo) ou quando o processo alvo desaparecer durante a captura; a única resolução automática permitida é o re-seguimento por nome já especificado em FR-012 (nunca uma escolha ambígua ou um device diferente), preservando a mesma filosofia de falha explícita sem fallback arbitrário já exigida para `endpointId` (P7).
- **FR-005**: Um canal configurado por processo MUST falhar de forma explícita e permanente no startup se o processo alvo não puder ser resolvido de forma única (não está em execução, ou múltiplos processos correspondem ao nome informado) — mesmo comportamento de fail-fast já especificado para um `endpointId` não resolvido (SF-018).
- **FR-006**: Um canal configurado por processo (**PID**) que perder seu processo alvo durante a sessão (processo encerrado) MUST falhar de forma explícita para aquele canal, sem silenciar os demais canais da mesma sessão (ADR-0007/P6) — PID nunca re-segue uma nova instância (FR-012 é exclusivo de seleção por nome, Clarifications).
- **FR-007**: Canais por processo e canais por dispositivo (`endpointId`/`index`/`nameRegex`/`default`, SF-018) MUST poder coexistir no mesmo perfil/sessão sem interferir um no outro.
- **FR-008**: Canais por processo MUST permanecer compatíveis com o listener de hot-plug já existente (SF-019) para quaisquer canais por dispositivo na mesma sessão — esta feature MUST NOT alterar o comportamento de hot-plug já especificado para esses canais.
- **FR-009**: Os testes automatizados desta feature MUST rodar sem GPU nem hardware físico (fakes/mocks em WSL/Linux); a validação real de captura de loopback por processo em WASAPI MUST ser documentada manualmente em `docs/validation/`, seguindo o padrão já usado para SF-018/SF-019 (P10).
- **FR-010**: Esta feature MUST NOT introduzir UI desktop, persistência de sessão, nem alterar o comportamento de janela adaptativa já entregue (SF-022) — explicitamente fora de escopo pela issue #19.
- **FR-011**: A seleção por processo MUST ser restrita a processos da mesma sessão/usuário do operador que inicia o agente — o sistema MUST NOT permitir capturar um processo de sistema/kernel nem um processo pertencente a outro usuário na mesma máquina (Clarifications, P9).
- **FR-012**: Um canal configurado por **nome** de processo (não por PID) que perder seu processo alvo MUST resolver e retomar automaticamente uma nova instância inequívoca do mesmo nome que apareça em seguida — análogo à chegada (arrival) de hot-plug (SF-019) — sem falha explícita nem reinicialização manual do canal; se, em vez disso, múltiplas novas instâncias ambíguas aparecerem, aplica-se a mesma política de falha explícita de FR-005 (Clarifications).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operadores conseguem apontar um canal para um aplicativo específico em execução e obter transcrição limitada ao áudio desse aplicativo, sem precisar alterar a configuração dos demais canais do mesmo perfil.
- **SC-002**: 100% dos eventos de transcrição gerados por canais por processo validam contra o schema `transcript-event.v2` já existente (campos obrigatórios inalterados).
- **SC-003**: Quando o processo alvo desaparece durante a sessão, o canal afetado reporta um erro distinto e para (seleção por PID), ou retoma automaticamente numa nova instância inequívoca do mesmo nome sem intervenção manual (seleção por nome) — em ambos os casos, os demais canais da mesma sessão continuam funcionando sem interrupção.
- **SC-004**: Zero incidentes de fallback silencioso — seleção de processo ambígua ou ausente sempre produz um erro explícito e acionável, nunca uma captura não intencional de outro processo/dispositivo.
- **SC-005**: A suíte automatizada desta feature passa 100% sem depender de GPU/hardware; evidência de validação manual Windows é registrada em `docs/validation/` antes de considerar a feature concluída.

## Assumptions

- A seleção por processo aceita tanto PID quanto nome de processo/aplicativo como alternativas mutuamente exclusivas entre si, seguindo o mesmo padrão de seletor exclusivo já usado em `DeviceSelector` (`endpointId`/`index`/`nameRegex`/`default`, SF-018) — a issue já pede explicitamente as duas formas de seleção.
- O metadado `sourceType` do contrato `transcript-event.v2` para canais por processo é tratado como uma variação de captura de sistema (`"system"`), com nome/PID do processo adicionados como campos opcionais adicionais no objeto `device` — decisão exata de schema (novo valor de enum vs. campo adicional) fica para `/speckit-plan`, respeitando P4 (aditivo, documentado, com ADR se estrutural).
- A captura de loopback por processo depende de uma API do Windows com requisito mínimo de versão do SO mais recente que o já exigido pelas features de dispositivo (SF-018/SF-019); a validação exata de compatibilidade de versão fica para `/speckit-plan`/`research.md`.
- Um canal por processo aguarda o aparecimento de uma sessão de áudio ativa (processo já em execução, mas ainda silencioso) em vez de falhar — desde que o processo em si já tenha sido resolvido sem ambiguidade no startup.
- Esta spec cobre apenas a captura por processo em si (seleção, isolamento, metadados, falha explícita); não inclui UI desktop, persistência de sessão, nem qualquer alteração ao comportamento de janela adaptativa (SF-022, já entregue) — fora de escopo conforme a issue #19.
