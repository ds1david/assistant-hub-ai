# Feature Specification: Listener de hot-plug nativo MMDevice (SF-019)

**Feature Branch**: `feature/sf-019-sf-019-listener-de-hot-plug-nativo-mmdevice`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "Issue #13 — Detectar plug/unplug de endpoints WASAPI e re-resolver canais por endpointId sem fallback silencioso."

**Referências**: Issue #13 · Umbrella `specs/001-streaming-foundation/` · Depende de `specs/004-sf-018-mmdevice-endpoint-id/` (resolução por `endpointId`, ADR `docs/adr/0011-mmdevice-endpoint-identity.md`) · Edge cases de SF-018 que esta feature fecha: remoção durante captura ativa e TOCTOU entre enumeração e abertura do stream.

## Clarifications

### Session 2026-07-20

- Q: Onde o listener de hot-plug deve viver em relação ao isolamento de processo por canal (P6/ADR-0007)? → A: Listener embutido em cada subprocesso de canal — cada worker isolado registra sua própria notificação COM/WASAPI para o seu `endpointId`, sem exigir IPC novo entre supervisor e workers (que hoje não existe; o supervisor só monitora via `poll()`).
- Q: SF-019 deve também cobrir o canal que falha já no início porque o endpoint ainda não existe (hoje SF-018 FR-007 encerra imediatamente, sem loop de espera)? → A: Não — SF-019 cobre apenas remoção/retomada durante captura já iniciada; a falha de resolução inicial continua encerrando imediatamente conforme SF-018 FR-007, contrato inalterado.
- Q: Quando o listener detecta chegada do endpointId mas a re-resolução ainda falha (endpoint reaparente porém sem correlação válida), o que o canal deve fazer? → A: Tratar como se a notificação não tivesse chegado — cair no laço de reconexão genérico por backoff já existente, sem tentativa dedicada adicional.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Falha imediata e explícita quando o endpoint some durante a captura (Priority: P1)

Um canal está capturando um endpoint identificado por `endpointId`. O dispositivo físico é desconectado (USB removido, Bluetooth cai, driver desabilitado). Em vez de depender do laço de reconexão genérico do worker — que só percebe o problema quando a próxima leitura de stream falha, após um backoff que cresce até 10s — o listener nativo de hot-plug detecta o evento de remoção do endpoint e o worker encerra a tentativa atual imediatamente com um erro específico de "endpoint removido", distinto de uma falha transitória de stream.

**Why this priority**: É o problema central da issue. Sem detecção dedicada, a remoção de um endpoint é indistinguível de qualquer outra falha de I/O — o operador não sabe se deve replugar o dispositivo, trocar de perfil ou é apenas uma instabilidade passageira do driver.

**Independent Test**: Com um provider de notificação fake (sem hardware), simular um evento de remoção para o `endpointId` de um canal em captura e verificar que o worker reage à notificação — não apenas ao erro de leitura do stream — e produz uma mensagem distinta de "endpoint removido".

**Acceptance Scenarios**:

1. **Given** um canal capturando um `endpointId` válido, **When** o listener recebe uma notificação de remoção para esse `endpointId`, **Then** a tentativa de captura atual encerra com um erro específico de "endpoint removido", sem esperar o próximo ciclo de backoff do laço de reconexão genérico.
2. **Given** uma notificação de remoção para um `endpointId` que **não** pertence a nenhum canal ativo, **When** o listener a recebe, **Then** nenhum canal é afetado.
3. **Given** um endpoint que already estava inativo desde o início (coberto por SF-018), **When** a captura nem chegou a iniciar, **Then** o comportamento permanece o da FR-007 de SF-018 (sem mudança) — esta feature cobre a remoção **durante** captura em andamento, não a resolução inicial.

---

### User Story 2 - Retomada automática quando o endpoint volta (Priority: P2)

Após a remoção do User Story 1, o operador reconecta o mesmo dispositivo físico. O listener detecta o evento de chegada (arrival) do mesmo `endpointId` e o canal correspondente re-resolve e retoma a captura automaticamente — sem exigir reinício manual do agente e sem esperar o teto do backoff genérico.

**Why this priority**: Entrega o valor de recuperação automática, mas depende logicamente da detecção da User Story 1 (não há "voltar a capturar" sem antes ter parado de forma rastreável). Prioridade P2 porque o comportamento de fallback (reconexão manual reiniciando o processo) já existe hoje, só não é imediato nem automático.

**Independent Test**: Com o provider de notificação fake, simular remoção seguida de chegada (arrival) do mesmo `endpointId` e verificar que o canal volta a capturar sem intervenção externa, usando o mesmo `endpointId` (não outro dispositivo).

**Acceptance Scenarios**:

1. **Given** um canal que encerrou por remoção de endpoint (User Story 1), **When** o listener recebe uma notificação de chegada para o mesmo `endpointId`, **Then** o canal re-resolve o endpoint pelo índice de enumeração atual (reaproveitando `find_device_for_endpoint`/`resolve_device` de SF-018) e retoma a captura no mesmo endpoint físico.
2. **Given** uma notificação de chegada para um `endpointId` diferente do configurado no canal, **When** o listener a recebe, **Then** o canal não reage — permanece parado ou no seu estado atual.
3. **Given** múltiplos eventos de chegada/remoção em rajada para o mesmo `endpointId` (bounce comum de driver), **When** o listener os recebe, **Then** o sistema não dispara múltiplas tentativas de retomada simultâneas — os eventos redundantes são agrupados/ignorados (debounce).

---

### User Story 3 - Testável e portátil sem hardware ou COM real (Priority: P3)

Um desenvolvedor ou o CI precisa validar o comportamento do listener sem uma máquina Windows com hardware de áudio físico. O listener é isolado da lógica pura de correlação (`endpoints.py`) em seu próprio módulo, com um provider de notificação substituível por um fake em testes; fora do Windows, o listener degrada para uma implementação nula sem carregar COM/WASAPI.

**Why this priority**: Pré-condição de qualidade e manutenibilidade (constituição P10), mas não é o valor funcional em si — é o que torna as User Stories 1 e 2 verificáveis em CI.

**Independent Test**: Rodar a suíte de testes do listener em Linux/CI usando o provider fake, sem qualquer dependência de `pywin32`/COM carregada, e confirmar que a mesma suíte cobre remoção, chegada e debounce descritos nas User Stories 1 e 2.

**Acceptance Scenarios**:

1. **Given** a execução em uma plataforma sem WASAPI (Linux/CI), **When** o listener é instanciado, **Then** ele usa um provider nulo — nenhuma notificação é emitida e nenhuma dependência específica de Windows é carregada.
2. **Given** o provider de notificação fake usado em teste, **When** um evento de remoção/chegada é injetado programaticamente, **Then** o comportamento observado é idêntico ao descrito nas User Stories 1 e 2, sem exigir hardware.
3. **Given** o módulo do listener, **When** inspecionado, **Then** ele não contém a lógica de correlação estrutural de `correlate_devices`/`find_device_for_endpoint` (que permanece em `endpoints.py`) — o listener apenas consome essas funções.

---

### Edge Cases

- Endpoint removido durante captura ativa (diferente do TOCTOU entre enumeração e abertura do stream, já coberto por SF-018): tratado pela User Story 1 desta feature.
- Rajada de eventos de chegada/remoção do mesmo `endpointId` (bounce de driver): debounce evita múltiplas tentativas de retomada simultâneas.
- Notificação de chegada chega depois que o canal já foi parado deliberadamente (`stop_event` setado, ex. shutdown do agente): o listener não deve reiniciar um canal que o supervisor já decidiu encerrar.
- Dois canais diferentes usando o mesmo `endpointId`: uma notificação de remoção/chegada afeta ambos, cada um em seu processo isolado (P6), sem coordenação entre eles.
- Notificação para um `endpointId` que nunca foi correlacionado (ex.: dispositivo novo, sem endpoint de captura conhecido): ignorada — nenhum canal está configurado para ele.
- Falha ao registrar o listener nativo junto ao SO (ex.: erro de COM ao subscrever notificações): degrada para não ter detecção dedicada (comportamento equivalente ao pré-SF-019, laço de reconexão genérico), sem derrubar o worker nem o supervisor.
- Evento de "state changed" (ex.: endpoint fica `unplugged`/`disabled` sem enumerar como removido) tratado como remoção para efeito de reação do canal.
- Notificação de chegada do `endpointId` correto, mas a re-resolução ainda falha (ex.: endpoint ativo porém sem correlação válida no momento): tratado como se a notificação não tivesse ocorrido — o canal cai no laço de reconexão genérico por backoff, sem tentativa dedicada adicional nem encerramento permanente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST fornecer um listener de notificações de dispositivo WASAPI (chegada, remoção, mudança de estado) em um módulo próprio, separado da lógica pura de correlação em `endpoints.py`. O listener MUST ser instanciado dentro do próprio subprocesso isolado de cada canal (não no processo supervisor), preservando o isolamento de P6/ADR-0007 e sem exigir um canal de IPC novo entre supervisor e workers.
- **FR-002**: Quando o listener recebe uma notificação de remoção/estado-inativo para o `endpointId` em uso por um canal em captura ativa, o worker daquele canal MUST encerrar a tentativa de captura atual com um erro específico de "endpoint removido", distinto de erros genéricos de stream, e MUST NOT aguardar o próximo ciclo do backoff genérico para perceber a remoção.
- **FR-003**: Quando o listener recebe uma notificação de chegada para o `endpointId` de um canal que está em espera de reconexão (ex.: após FR-002), o sistema MUST re-resolver o endpoint (reaproveitando a resolução de SF-018) e retomar a captura no mesmo endpoint físico, sem exigir reinício manual do processo e sem esperar o teto do backoff genérico. Se a re-resolução falhar mesmo após a notificação de chegada (endpoint reaparente sem correlação válida), o sistema MUST tratar a tentativa como se a notificação não tivesse ocorrido, caindo de volta no laço de reconexão genérico por backoff — sem tentativa dedicada adicional nem encerramento permanente.
- **FR-004**: Um canal MUST reagir apenas a notificações do seu próprio `endpointId` configurado — notificações de outros endpoints MUST ser ignoradas por aquele canal.
- **FR-005**: Rajadas de notificações duplicadas/redundantes para o mesmo `endpointId` em uma janela curta MUST ser agrupadas (debounce), de forma que no máximo uma reação (encerramento ou retomada) seja disparada por rajada.
- **FR-006**: Fora do Windows (Linux/CI) ou quando o registro do listener nativo falhar, o sistema MUST degradar para uma implementação nula/sem detecção dedicada, sem lançar exceção não tratada e sem carregar dependências específicas de Windows.
- **FR-007**: O comportamento do listener (remoção, chegada, debounce, ignorar endpoint alheio) MUST ser testável integralmente via um provider de notificação fake, sem hardware físico nem COM real (constituição P10).
- **FR-008**: Uma notificação de chegada para um canal que já foi parado deliberadamente (`stop_event` setado) MUST NOT reiniciar aquele canal.

### Key Entities

- **Listener de hot-plug**: componente que se inscreve em notificações nativas de dispositivo (WASAPI/MMDevice) e traduz eventos do SO em eventos de domínio (chegada, remoção, mudança de estado) por `endpointId`; injetável/substituível por um fake em testes. Vive dentro do subprocesso isolado do próprio canal (um registro COM por worker), não no processo supervisor.
- **Evento de notificação**: `{endpointId, tipo (chegada|remoção|mudança_de_estado), timestamp}`; consumido pelo worker do canal correspondente.
- **Worker de canal** (existente, `capture.py`): passa a reagir a eventos do listener além do seu laço de reconexão genérico por backoff.

### Fora de escopo

- Captura por processo/aplicativo (SF-020).
- `default_microphone` WASAPI-aware (issue separada).
- Resolução inicial de `endpointId` e suas mensagens de erro (já coberto por SF-018) — esta feature reaproveita, não redefine.
- Espera pelo endpoint aparecer no startup: um canal cujo endpoint não existe no momento em que o worker inicia continua encerrando imediatamente conforme SF-018 FR-007 — o listener desta feature só atua sobre canais com captura já iniciada.
- Qualquer fallback silencioso de `endpointId` para `index`/`nameRegex`/`default` (proibido por P7, inalterado aqui).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em teste automatizado com provider fake, a remoção de um endpoint em captura ativa é detectada e reportada pelo listener sem depender do próximo ciclo de backoff do laço de reconexão genérico.
- **SC-002**: Em teste automatizado com provider fake, a chegada do mesmo `endpointId` após remoção resulta em retomada da captura no mesmo endpoint físico, sem reinício manual do processo.
- **SC-003**: 100% da suíte de testes do listener roda em CI Linux sem hardware físico e sem dependência de COM/`pywin32` carregada.
- **SC-004**: Nenhum teste do listener produz fallback silencioso para outro `endpointId`/dispositivo — remoção sempre resulta em erro explícito ou, quando aplicável, retomada no mesmo endpoint.
- **SC-005**: Rajadas simuladas de eventos duplicados nos testes disparam no máximo uma reação por canal, verificado por contagem de chamadas no fake.
- **SC-006**: A validação manual Windows está registrada em `docs/validation/sf-019-windows.md` com ambiente, commit, passos (hot-plug real de um dispositivo USB/Bluetooth) e resultado PASS (constituição P10).

## Assumptions

- Constrói sobre a resolução por `endpointId` de SF-018 (`endpoints.py`, `devices.py`) sem duplicar ou redefinir essa lógica — o listener apenas consome `find_device_for_endpoint`/`resolve_device`.
- A API nativa exata usada para se inscrever em notificações WASAPI (ex.: `IMMNotificationClient` via COM) é decisão de implementação, não de especificação — definida em `/speckit.plan`.
- A janela de debounce é um valor curto o suficiente para absorver bounce de driver sem atrasar perceptivelmente a detecção real; o valor exato é decisão de implementação.
- Testes automatizados usam fakes de provider de notificação (constituição P10); a validação com hardware real de hot-plug (USB/Bluetooth) é manual e documentada, análoga a SF-018.
- O laço de reconexão genérico do worker (backoff até 10s) permanece como rede de segurança para falhas não cobertas pelo listener (ex.: falha ao registrar o listener nativo, FR-006).
- O umbrella `specs/001-streaming-foundation/tasks.md` só é atualizado após o merge desta feature.
