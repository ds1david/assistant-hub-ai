# Feature Specification: Tornar `default_microphone()` WASAPI-aware (Issue #27)

**Feature Branch**: `feature/issue-27-bug-default-microphone-n-o-wasapi-aware`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "[bug] default_microphone() não é WASAPI-aware (issue #27). Contexto: reproduzido 2x durante a validação manual SF-015 (docs/validation/sf-015-default-mic.md, 2026-07-20) — o canal `local_microphone` de um `run` sem `--profile` resolve o microfone default via `pyaudio.get_default_input_device_info()`, que retorna o default global do PortAudio (host API MME, index 1) em vez do default marcado `isDefault: true` no host API WASAPI (index 9). Como `correlate_devices()` (endpoints.py) só correlaciona dispositivos cujo `hostApi` é WASAPI, o canal de microfone default fica com `endpointId: None` — perdendo estabilidade de endpoint, correlação de hot-plug (SF-019) e o campo `endpointId` no evento `transcript-event.v2`, ao contrário de `default_loopback()` (devices.py:76-86), que já força o host API WASAPI corretamente. Corrigir `default_microphone()` para resolver o default dentro do host API WASAPI (mesmo padrão de `default_loopback()`), preservando fail-fast explícito quando não houver device WASAPI default de entrada disponível. Fora de escopo: SF-020 (captura por processo), mudança de contrato `transcript-event.v2`, redesign do hot-plug (specs/006)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Canal de microfone default recebe `endpointId` estável via WASAPI (Priority: P1)

Um operador roda o agente sem `--profile` (`assistant-hub-audio run`), configurando implicitamente o canal de microfone como `default: true`. Hoje, `default_microphone()` devolve o dispositivo default global do PortAudio (que pode ser MME, DirectSound ou WDM-KS, conforme a ordem de enumeração do host), não o dispositivo marcado como default dentro do host API WASAPI. Como a correlação de endpoint (`correlate_devices()`) só considera dispositivos WASAPI, o canal termina sem `endpointId`, ficando "invisível" para o sistema de identidade MMDevice (ADR-0011) e para a correlação de hot-plug (SF-019).

**Why this priority**: é a causa raiz única do bug — sem corrigir a fonte da resolução, nenhuma das garantias de estabilidade de endpoint já entregues em SF-018/SF-019 se aplicam ao caminho `default` de microfone, que é o caminho mais comum de uso (`run` sem `--profile`).

**Independent Test**: em host Windows real com pelo menos um dispositivo de entrada marcado `isDefault: true` no host API WASAPI, rodar `assistant-hub-audio run` sem `--profile` e confirmar nos logs/evento `transcript-event.v2` do canal de microfone que `endpointId` é preenchido e corresponde ao `endpointId` WASAPI reportado por `list-devices` para o mesmo dispositivo físico.

**Acceptance Scenarios**:

1. **Given** um host Windows com um dispositivo de entrada marcado `isDefault: true` no host API WASAPI, **When** o agente resolve o canal de microfone configurado com `default: true`, **Then** o dispositivo resolvido é o default reportado pelo host API WASAPI (mesmo índice/nome exibido por `list-devices` para a entrada WASAPI default), não o default global do PortAudio.
2. **Given** o dispositivo resolvido no cenário anterior, **When** `resolve_device()`/`correlate_devices()` processam o canal, **Then** o campo `endpointId` é preenchido (não `None`) e é estável entre execuções, seguindo a prioridade `endpointId > index > default` já especificada em ADR-0011.
3. **Given** o canal de microfone default com `endpointId` preenchido, **When** um evento `transcript-event.v2` é emitido para esse canal, **Then** o evento carrega `endpointId`/`channelId`/`sourceType` preenchidos, no mesmo padrão já garantido hoje para o canal de loopback (`default_loopback()`).

---

### User Story 2 - Ausência de default WASAPI de entrada falha de forma explícita, sem fallback silencioso (Priority: P2)

Em um host onde o host API WASAPI não está disponível ou não reporta nenhum dispositivo de entrada default (cenário raro, mas possível em ambientes com apenas drivers legados), o sistema não deve silenciosamente cair de volta para um dispositivo não-WASAPI (repetindo o bug atual de forma disfarçada). O comportamento deve ser um erro explícito e diagnosticável, consistente com o fail-fast já especificado para `endpointId` desconhecido em SF-018.

**Why this priority**: evita reintroduzir o mesmo problema por outra via (fallback silencioso) e mantém a filosofia de "degrade explícito, sem crash silencioso" já usada em specs anteriores (P3/P10, spec 009); prioridade P2 porque é uma salvaguarda para um cenário de borda, não o caminho principal do bug.

**Independent Test**: em teste automatizado (WSL, sem hardware), simular uma lista de dispositivos PortAudio em que o host API WASAPI não expõe `defaultInputDevice` (ou o host API WASAPI está ausente) e confirmar que `default_microphone()` levanta um erro claro e diagnosticável, em vez de devolver um dispositivo de outro host API.

**Acceptance Scenarios**:

1. **Given** uma lista de dispositivos PortAudio onde o host API WASAPI não tem `defaultInputDevice` válido, **When** `default_microphone()` é chamado, **Then** o sistema levanta um erro explícito identificando a ausência de default WASAPI de entrada, sem devolver um dispositivo de outro host API.
2. **Given** o erro do cenário anterior, **When** o canal usa `default: true` sem alternativa configurada (`index`/`endpointId`/`nameRegex`), **Then** o worker do canal falha de forma diagnosticável (mensagem de log clara), no mesmo espírito do fail-fast já especificado em SF-018 para `endpointId` inexistente.

---

### User Story 3 - Cobertura de teste automatizado para `default_microphone()` (Priority: P3)

Hoje não existe nenhum teste automatizado cobrindo `default_microphone()` (nem `test_devices.py`, nem referências em `test_capture.py`/`test_endpoints.py`). A correção precisa vir acompanhada de testes de regressão que fixem o comportamento correto e previnam a reintrodução do bug.

**Why this priority**: sem teste automatizado, o bug pode voltar silenciosamente em um refactor futuro, exatamente como aconteceu (o gap já era conhecido desde a validação SF-015 de 2026-07-20 e só agora está sendo corrigido); prioridade P3 porque é rede de segurança, não o comportamento em si (coberto pelas User Stories 1 e 2).

**Independent Test**: rodar a suíte automatizada do `windows-audio-agent` (WSL, sem hardware) e confirmar que os novos testes de `default_microphone()` cobrem: (a) resolução correta dentro do host API WASAPI quando há default de entrada, e (b) erro explícito quando não há default WASAPI de entrada.

**Acceptance Scenarios**:

1. **Given** uma lista de dispositivos PortAudio simulada com host API WASAPI presente e `defaultInputDevice` válido, **When** o teste chama `default_microphone()`, **Then** o dispositivo devolvido é o do host API WASAPI, com `hostApi` correspondente ao índice WASAPI simulado.
2. **Given** uma lista de dispositivos PortAudio simulada sem `defaultInputDevice` WASAPI válido, **When** o teste chama `default_microphone()`, **Then** o teste confirma que o erro explícito da User Story 2 é levantado.

---

### Edge Cases

- O que acontece se existir mais de um host API WASAPI reportado pelo PortAudio (não deveria ocorrer normalmente, mas o código não pode assumir índice fixo)? A resolução deve usar `get_host_api_info_by_type(pyaudio.paWASAPI)`, o mesmo padrão já usado por `default_loopback()`, que não assume índice fixo.
- O que acontece se o dispositivo marcado default pelo Windows dentro do WASAPI mudar em tempo de execução (troca de dispositivo padrão pelo usuário durante uma sessão `run`)? Fora de escopo desta correção — comportamento de mudança de default em runtime já é tratado (ou não) pela feature de hot-plug (`specs/006-sf-019-hotplug-listener/`), que não é alterada aqui.
- O que acontece com canais que já usam `endpointId`/`index`/`nameRegex` explícitos (não `default: true`)? Nenhum impacto — esta correção altera apenas o caminho de resolução usado quando `default: true` é o seletor efetivo do canal.
- O que acontece com o canal de loopback (`default_loopback()`)? Nenhuma mudança — já é WASAPI-aware; a correção usa o mesmo padrão, não devendo alterar seu comportamento.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `default_microphone()` MUST resolver o dispositivo de entrada default consultando o host API WASAPI (`get_host_api_info_by_type(pyaudio.paWASAPI)` e seu `defaultInputDevice`), no mesmo padrão já usado por `default_loopback()` (`devices.py:76-86`), em vez de `pyaudio.get_default_input_device_info()` (default global do PortAudio, agnóstico de host API).
- **FR-002**: Quando o host API WASAPI expõe um `defaultInputDevice` válido, `resolve_device()`/`correlate_devices()` MUST preencher `endpointId` (não `None`) para canais que usam o seletor `default: true` de microfone, seguindo a prioridade `endpointId > index > default` já especificada em ADR-0011.
- **FR-003**: Quando o host API WASAPI não está disponível ou não reporta `defaultInputDevice` válido, `default_microphone()` MUST levantar um erro explícito e diagnosticável, sem devolver um dispositivo de outro host API como fallback silencioso.
- **FR-004**: A correção MUST NOT alterar o comportamento de `default_loopback()`, que já é WASAPI-aware, nem as regras de prioridade de correlação já especificadas em ADR-0011.
- **FR-005**: A suíte de testes automatizados MUST incluir teste(s) de regressão cobrindo (a) resolução correta de `default_microphone()` dentro do host API WASAPI quando há default de entrada, e (b) o erro explícito de FR-003 quando não há default WASAPI de entrada.
- **FR-006**: A correção MUST NOT alterar o comportamento de SF-020 (captura por processo, fora de escopo) nem o contrato `transcript-event.v2`.
- **FR-007**: A correção MUST ser validada manualmente em host Windows real repetindo o cenário já documentado em `docs/validation/sf-015-default-mic.md` (canal `local_microphone` de um `run` sem `--profile`), com o resultado atualizado nesse mesmo arquivo ou em um novo arquivo de validação referenciado a partir dele, confirmando que o `endpointId` do canal de microfone default agora corresponde ao dispositivo `isDefault: true` do host API WASAPI.

### Key Entities

- **Canal de microfone default**: canal de captura de áudio configurado com o seletor `default: true` (sem `endpointId`/`index`/`nameRegex` explícitos), cujo dispositivo de entrada é resolvido em tempo de execução.
- **Host API WASAPI**: namespace de dispositivos do PortAudio correspondente ao Windows Audio Session API; único host API considerado pela correlação de `endpointId` (ADR-0011).
- **`endpointId`**: identificador estável de dispositivo MMDevice, usado para correlação de hot-plug (SF-019) e propagado no evento `transcript-event.v2`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em host Windows real com um dispositivo de entrada marcado `isDefault: true` no WASAPI, o canal de microfone configurado com `default: true` recebe um `endpointId` não nulo e idêntico ao reportado por `list-devices` para esse dispositivo, em 100% das execuções testadas.
- **SC-002**: 100% da suíte automatizada de captura/endpoints continua passando após a correção, incluindo os novos testes de regressão de FR-005.
- **SC-003**: O evento `transcript-event.v2` do canal de microfone default passa a carregar `endpointId` preenchido, eliminando a lacuna registrada em `docs/validation/sf-015-default-mic.md` (limitação 1).
- **SC-004**: Zero regressão observada no comportamento do canal de loopback (`default_loopback()`) após a correção, confirmado pela suíte automatizada existente.

## Assumptions

- O ambiente de validação manual tem `pycaw` disponível e ao menos um dispositivo de entrada WASAPI marcado `isDefault: true`, reproduzindo as mesmas condições já usadas em `docs/validation/sf-015-default-mic.md` (2026-07-20), onde o bug foi confirmado 2x.
- O padrão de resolução de `default_loopback()` (`devices.py:76-86`) é a referência correta de implementação para "WASAPI-aware" nesta correção — não se espera um mecanismo novo, apenas espelhar o padrão já validado em produção para o caminho de saída/loopback.
- SF-020 (captura por processo) e o contrato `transcript-event.v2` não precisam de nenhuma alteração para esta correção, conforme já declarado como fora de escopo em `specs/010-sf-019-callback-notpresent-fix/spec.md` (FR-008).
- Esta spec cobre apenas a resolução do dispositivo default de microfone (issue #27); não reabre o design de hot-plug (`specs/006-sf-019-hotplug-listener/`) nem o de identidade de endpoint MMDevice (`specs/004-sf-018-mmdevice-endpoint-id/`).
