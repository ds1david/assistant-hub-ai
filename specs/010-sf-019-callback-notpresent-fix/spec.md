# Feature Specification: Correção de aridade do callback COM e de `notpresent` fatal (SF-019, Issue #22)

**Feature Branch**: `010-sf-019-callback-notpresent-fix`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "[bug] SF-019: OnDeviceStateChanged assinatura COM inválida + notpresent mata worker (issue #22). Contexto: validação Windows da SF-019 (2026-07-22), após o fix de comtypes.gen.MMDeviceAPILib (IMMNotificationClient manual, issue #20). Workers sobem e resolvem endpointId. No unplug físico/estado de dispositivo, o Windows dispara notificação COM, mas o ciclo hot-plug não completa e o processo encerra. Bug A — assinatura do callback COM: TypeError 'OnDeviceStateChanged() takes 3 positional arguments but 4 were given'; aridade incorreta na implementação comtypes, evento de remoção não propaga para ChannelHotplugSignal. Bug B — notpresent encerra worker de forma permanente: EndpointResolutionError/resolução com estado notpresent tratada como fatal no retry em vez de aguardar arrival/backoff (FR-003/woke_on_arrival); sem o sinal de remoção (Bug A), o caminho cai no resolve e mata o worker, impedindo resume no replug. Fora de escopo: SF-020 captura por processo, default_microphone() WASAPI-aware, mudança de contrato transcript-event.v2. Critérios de validação Windows: run com endpointId estável; unplug sem TypeError no callback; worker não termina 'failed permanently' só por notpresent transitório; replug resume no mesmo endpointId sem reiniciar o processo; atualizar docs/validation/sf-019-windows.md."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Callback COM de mudança de estado chega ao listener sem erro (Priority: P1)

Um operador roda o agente em host Windows real com um canal configurado por `endpointId` (SF-018) e hot-plug habilitado (SF-019). Ao desconectar fisicamente o dispositivo, o Windows dispara a notificação COM `OnDeviceStateChanged` no `IMMNotificationClient`, mas a implementação atual do callback tem aridade incompatível com a convenção de chamada do `comtypes` (`TypeError: ...OnDeviceStateChanged() takes 3 positional arguments but 4 were given`) — o evento nunca chega ao `ChannelHotplugSignal` do canal, e a captura não é avisada da remoção pelo caminho rápido já especificado em `specs/006-sf-019-hotplug-listener/`.

**Why this priority**: sem isso, nenhum evento de hot-plug real chega ao domínio — a feature SF-019 continua não funcionando em produção mesmo após a correção de #20 (issue #22 é o resultado da primeira validação manual real, que revelou este bug adicional).

**Independent Test**: em host Windows real, desconectar fisicamente o `endpointId` monitorado e confirmar nos logs que `OnDeviceStateChanged`/demais callbacks do `IMMNotificationClient` são invocados sem `TypeError`, e que o evento resultante chega ao `ChannelHotplugSignal` do canal (reação de remoção).

**Acceptance Scenarios**:

1. **Given** um `IMMNotificationClient` registrado via `RegisterEndpointNotificationCallback`, **When** o Windows invoca `OnDeviceStateChanged` (ou qualquer outro método da interface) no callback real, **Then** a chamada é aceita pela assinatura do método Python sem `TypeError` de aridade.
2. **Given** o callback aceito sem erro, **When** o novo estado corresponde a `notpresent`/removido para o `endpointId` monitorado, **Then** o evento é traduzido e entregue ao `ChannelHotplugSignal` como uma reação de remoção (comportamento já especificado em `specs/006-sf-019-hotplug-listener/spec.md`, hoje bloqueado por este bug).

---

### User Story 2 - `notpresent` transitório não encerra o worker permanentemente (Priority: P1)

Mesmo que o evento de remoção não chegue a tempo pelo caminho do callback (ex.: uma corrida entre a falha do stream de áudio e a notificação COM), uma tentativa de resolução de endpoint que falhe porque o dispositivo está temporariamente `notpresent` não pode ser tratada com a mesma política permanente/fatal usada para erros de configuração (índice inválido, `nameRegex` ambíguo, ou um `endpointId` que nunca existiu desde o início). O worker deve continuar vivo, aguardando o replug (arrival) ou o backoff genérico, em vez de encerrar com "failed permanently" e derrubar a captura daquele canal.

**Why this priority**: é a segunda causa, independente da primeira, do sintoma relatado na issue #22 ("Audio worker stopped unexpectedly", "All audio channels stopped") — mesmo corrigindo o Bug A (User Story 1), uma corrida residual entre stream/notificação ainda poderia derrubar o worker sem esta correção; as duas User Stories são necessárias para o comportamento real observado no Windows.

**Independent Test**: em teste automatizado (WSL, sem hardware), simular uma resolução de endpoint que falha por estado `notpresent` fora da janela de `woke_on_arrival` e confirmar que o canal continua vivo (aguardando backoff/arrival) em vez de propagar `EndpointResolutionError` de forma permanente; simular também um `endpointId` desconhecido desde o startup e confirmar que o fail-fast de SF-018 continua ocorrendo.

**Acceptance Scenarios**:

1. **Given** um canal cujo `endpointId` já foi resolvido com sucesso ao menos uma vez, **When** uma tentativa de resolução subsequente falha porque o estado do dispositivo é `notpresent` (unplug), **Then** o worker não encerra permanentemente — continua aguardando arrival/backoff no mesmo `endpointId`.
2. **Given** o mesmo canal aguardando, **When** o dispositivo é reconectado (arrival), **Then** a captura retoma no mesmo `endpointId` sem reinício manual do processo (comportamento já especificado em SF-019, preservado).
3. **Given** um canal cujo `endpointId` nunca foi resolvido com sucesso desde o startup (nunca existiu), **When** a resolução falha, **Then** o worker encerra de forma fatal/permanente como já especificado em SF-018 (fail-fast preservado, sem regressão).

---

### User Story 3 - Evidência de validação manual em Windows real atualizada (Priority: P3)

Como mantenedor responsável por fechar a issue #22, preciso que `docs/validation/sf-019-windows.md` reflita o resultado real desta correção contra hardware/COM Windows real — os critérios de validação já foram declarados na própria issue (unplug sem `TypeError`, worker não termina "failed permanently" só por `notpresent` transitório, replug resume no mesmo `endpointId`).

**Why this priority**: cumpre P10 (validação manual documentada) e é o critério de saída do gate G3 (Validate) antes de PR/merge; sem hardware Windows real os Bugs A e B não podem ser comprovados fim a fim (a suíte automatizada cobre os componentes isoladamente, não o COM real).

**Independent Test**: seguir os "Critérios de validação Windows" da issue #22 em host real (run, unplug, replug) e atualizar `docs/validation/sf-019-windows.md` com o resultado (PASS ou PASS parcial explícito, com a causa raiz remanescente documentada).

**Acceptance Scenarios**:

1. **Given** as correções das User Stories 1 e 2 aplicadas, **When** os passos de validação da issue #22 são executados em host Windows real, **Then** o resultado (PASS/PASS parcial/FAIL) e a data são registrados em `docs/validation/sf-019-windows.md`.

---

### Edge Cases

- O que acontece com um `endpointId` que nunca existiu desde o startup (nunca resolvido nem uma vez)? Continua fail-fast como já especificado em SF-018 — não deve ser confundido com `notpresent` transitório de um endpoint já resolvido antes (User Story 2, Acceptance Scenario 3).
- O que acontece se o dispositivo for removido e reconectado rapidamente (dentro da janela de debounce)? O comportamento de debounce já especificado em `specs/006-sf-019-hotplug-listener/` permanece inalterado — esta correção não o modifica.
- `OnDefaultDeviceChanged`/`OnPropertyValueChanged` hoje usam uma assinatura de aridade variável (`*_args`) — precisam da mesma auditoria de compatibilidade com a convenção de chamada do `comtypes` que motivou o Bug A, mesmo não tendo sido citados no `TypeError` original relatado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Os métodos de callback do `IMMNotificationClient` (`OnDeviceStateChanged`, `OnDeviceAdded`, `OnDeviceRemoved`, `OnDefaultDeviceChanged`, `OnPropertyValueChanged`) MUST ter assinatura compatível com a convenção de chamada real do `comtypes` para `COMObject`, sem levantar `TypeError` de aridade em nenhum dos métodos.
- **FR-002**: Nenhum callback do `IMMNotificationClient` MUST propagar exceção para o runtime COM — qualquer erro interno ao callback MUST ser capturado e logado, retornando ao chamador COM sem lançar (mesma filosofia de degrade explícito sem crash silencioso de P3/P10, já aplicada à falha de `subscribe()` em `specs/009-issue-20-mmdevice-notification-fix/`).
- **FR-003**: Um `OnDeviceStateChanged` reportando estado `notpresent` (ou removido/desabilitado) para o `endpointId` monitorado pelo canal MUST chegar ao `ChannelHotplugSignal` como uma reação de remoção, restaurando o comportamento já especificado em `specs/006-sf-019-hotplug-listener/spec.md` (hoje bloqueado pelo Bug A/FR-001).
- **FR-004**: Uma falha de resolução de endpoint (`EndpointResolutionError`) cuja causa seja o estado transitório `notpresent` de um `endpointId` **já resolvido com sucesso ao menos uma vez** MUST NOT usar a política permanente/fatal reservada a erros de configuração (índice inválido, `nameRegex` ambíguo) — o canal MUST continuar vivo, aguardando arrival ou o backoff genérico já especificado em SF-019.
- **FR-005**: O comportamento de fail-fast já existente (SF-018) para um `endpointId` que nunca foi resolvido com sucesso desde o startup MUST permanecer inalterado — não deve ser confundido com `notpresent` transitório de um endpoint já ativo antes (FR-004).
- **FR-006**: A suíte de testes automatizados MUST incluir teste(s) de regressão que (a) simulem a aridade real de chamada do `comtypes` para os callbacks do `IMMNotificationClient` (Bug A/FR-001) e (b) cubram os três casos de FR-004/FR-005: `notpresent` após resolução prévia → espera; arrival após espera → resume; `endpointId` nunca resolvido → fatal.
- **FR-007**: A correção MUST ser revalidada manualmente em host Windows real seguindo os "Critérios de validação Windows" da issue #22 (unplug sem `TypeError` no callback; worker não termina "failed permanently" só por `notpresent` transitório; replug resume no mesmo `endpointId` sem reiniciar o processo), com resultado registrado em `docs/validation/sf-019-windows.md`.
- **FR-008**: A correção MUST NOT alterar o comportamento de SF-020 (captura por processo, fora de escopo), `default_microphone()` WASAPI-aware (issue separada, fora de escopo), nem o contrato `transcript-event.v2`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em host Windows real, o unplug físico do `endpointId` monitorado gera log de remoção/estado sem `TypeError` em nenhum callback COM.
- **SC-002**: Em host Windows real, o worker não encerra com "failed permanently"/exit inesperado apenas por `notpresent` transitório durante um ciclo normal de unplug/replug.
- **SC-003**: Em host Windows real, o replug do mesmo dispositivo físico retoma a captura no mesmo `endpointId` sem reinício manual do processo.
- **SC-004**: 100% da suíte automatizada de hot-plug/captura continua passando após a correção, incluindo os novos testes de regressão de FR-006.
- **SC-005**: `docs/validation/sf-019-windows.md` reflete um resultado final (PASS ou PASS parcial explícito, com causa raiz remanescente documentada) para os critérios de validação da issue #22.

## Assumptions

- O Bug A (aridade do callback COM, FR-001/FR-002) é a causa raiz principal do sintoma relatado; o Bug B (`notpresent` tratado como fatal, FR-004/FR-005) é uma camada de defesa independente, necessária mesmo após o Bug A corrigido, para cobrir uma corrida residual entre a falha do stream de áudio e a chegada da notificação COM.
- Diferente de `specs/009-issue-20-mmdevice-notification-fix/` (correção retroativa a um código já alterado), esta spec precede a correção de código — nenhuma mudança de domínio para os Bugs A/B foi aplicada à árvore de trabalho antes desta spec (P1 cumprido na ordem normal, sem necessidade de aprovação retroativa de gate).
- Esta spec cobre apenas os dois bugs descritos na issue #22, resultado da primeira validação manual Windows real de SF-019 após a correção de #20; não reabre o design da feature de hot-plug em si (`specs/006-sf-019-hotplug-listener/`).
- SF-020 (captura por processo) e mudanças de contrato `transcript-event.v2` estão fora de escopo, conforme declarado explicitamente na issue #22.
