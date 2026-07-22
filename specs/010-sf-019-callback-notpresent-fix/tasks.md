---

description: "Task list for the COM callback arity + notpresent fatal fix (SF-019, Issue #22)"
---

# Tasks: Correção de aridade do callback COM e de `notpresent` fatal (SF-019, Issue #22)

**Input**: Design documents from `/specs/010-sf-019-callback-notpresent-fix/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md (N/A — sem entidades), quickstart.md

**Tests**: FR-006 exige explicitamente testes de regressão para os Bugs A e B; incluídos abaixo junto da
implementação de cada user story.

**Organization**: Tasks agrupadas por user story (spec.md). Diferente de
`specs/009-issue-20-mmdevice-notification-fix/`, esta correção é **prospectiva** — nenhuma mudança de
código para os Bugs A/B foi aplicada antes desta spec/plano/tasks.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependências)
- **[Story]**: A qual user story esta task pertence (US1, US2, US3)
- Caminhos de arquivo exatos incluídos nas descrições

---

## Phase 1: Setup

**Purpose**: Confirmar que nenhuma dependência nova é necessária

- [X] T001 Confirmar que `agents/windows-audio-agent/pyproject.toml` não precisa de nenhuma dependência nova — `comtypes`/`pycaw` já presentes; a correção do Bug A mantém `STDMETHOD` em vez de trocar para `COMMETHOD` (research.md §1, alternativa rejeitada) — checagem de diff, sem alteração de arquivo

**Checkpoint**: Nenhuma instalação nova necessária.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Confirmar que a base de SF-019/#20 sobre a qual esta correção se apoia está intacta

**⚠️ CRITICAL**: Nenhuma user story desta correção pode ser avaliada sem esta base

- [X] T002 Confirmar que `HotplugListener`, `ChannelHotplugSignal`, `EndpointResolutionError`, `EndpointRemovedError` e o laço principal de `capture_channel` em `agents/windows-audio-agent/src/assistant_hub_audio/{hotplug.py,capture.py}` permanecem com a mesma interface pública de `specs/006-sf-019-hotplug-listener/`/`specs/009-issue-20-mmdevice-notification-fix/` (nenhuma mudança de assinatura antes desta correção) — checagem de diff

**Checkpoint**: Base intacta — as user stories abaixo podem ser implementadas.

---

## Phase 3: User Story 1 - Callback COM de mudança de estado chega ao listener sem erro (Priority: P1) 🎯 MVP (parte 1/2)

**Goal**: Os 5 callbacks `IMMNotificationClient_On*` aceitam a convenção real de chamada do `comtypes` (`this` + argumentos declarados) sem `TypeError` de aridade, e o evento de `notpresent`/removido chega ao `ChannelHotplugSignal` (FR-001/FR-002/FR-003)

**Independent Test**: `specs/010-sf-019-callback-notpresent-fix/quickstart.md` §2 passos 3-4 (unplug real, sem `TypeError` nos logs) — ou, sem hardware, o teste de T007 simulando a convenção de chamada real do comtypes

### Tests for User Story 1

- [X] T007 [P] [US1] Teste de regressão simulando a convenção de chamada real do comtypes (`mth(this, *args_declarados)`, conforme `hack()`/`catch_errors` em `comtypes/_vtbl.py`, research.md §1) para os 5 callbacks `IMMNotificationClient_On*`, confirmando ausência de `TypeError` de aridade e que `OnDeviceStateChanged` com estado `notpresent` produz um `HotplugEvent(event_type="removed")` entregue ao callback `on_event` — `agents/windows-audio-agent/tests/test_hotplug.py` (novo bloco de testes) (FR-001, FR-003, FR-006)
- [X] T008 [P] [US1] Teste de regressão: uma exceção arbitrária levantada dentro do corpo de qualquer callback `IMMNotificationClient_On*` não propaga para o chamador — `agents/windows-audio-agent/tests/test_hotplug.py` (FR-002, FR-006)

### Implementation for User Story 1

- [X] T003 [US1] Adicionar o parâmetro `this` explícito (sem uso) como segundo argumento posicional em `IMMNotificationClient_OnDeviceStateChanged` — `agents/windows-audio-agent/src/assistant_hub_audio/mmdevice_notifications.py` (FR-001)
- [X] T004 [P] [US1] Adicionar o parâmetro `this` explícito (sem uso) em `IMMNotificationClient_OnDeviceAdded` e `IMMNotificationClient_OnDeviceRemoved` — `agents/windows-audio-agent/src/assistant_hub_audio/mmdevice_notifications.py` (FR-001)
- [X] T005 [P] [US1] Normalizar `IMMNotificationClient_OnDefaultDeviceChanged` e `IMMNotificationClient_OnPropertyValueChanged` para aceitar `this` explícito em vez de `*_args` (Edge Case da spec — auditoria de aridade) — `agents/windows-audio-agent/src/assistant_hub_audio/mmdevice_notifications.py` (FR-001)
- [X] T006 [US1] Envolver o corpo de cada um dos 5 callbacks `IMMNotificationClient_On*` com `try/except Exception`, logando aviso e retornando sem propagar — `agents/windows-audio-agent/src/assistant_hub_audio/mmdevice_notifications.py` (depends on T003, T004, T005) (FR-002)
- [X] T009 [P] [US1] Rodar `cd agents/windows-audio-agent && python3 -m compileall -q src && PYTHONPATH=src python3 -m pytest -q tests -k "hotplug or capture or mmdevice_notifications"` (quickstart.md §1) confirmando ausência de regressão introduzida por T003-T006 (FR-006, SC-004)

**Checkpoint**: Callback COM aceita a chamada real sem `TypeError`; evento de remoção chega ao signal — coberto por teste automatizado (a prova real end-to-end depende da revalidação manual — Phase 5/US3).

---

## Phase 4: User Story 2 - `notpresent` transitório não encerra o worker permanentemente (Priority: P1) 🎯 MVP (parte 2/2)

**Goal**: Uma falha de resolução de endpoint por `notpresent`, após o canal já ter resolvido com sucesso ao menos uma vez, é tratada como transitória (retry/backoff) em vez de fatal; o fail-fast de SF-018 permanece para um `endpointId` nunca resolvido (FR-004/FR-005)

**Independent Test**: `specs/010-sf-019-callback-notpresent-fix/quickstart.md` §2 passo 5 (worker não encerra "failed permanently" por notpresent transitório) — ou, sem hardware, os testes de T012/T013

### Tests for User Story 2

- [X] T012 [P] [US2] Teste: `EndpointResolutionError` levantada após uma resolução bem-sucedida anterior no mesmo canal não encerra o worker — dispara `_retry_after_wait()` (mesmo caminho de `EndpointRemovedError`) — `agents/windows-audio-agent/tests/test_capture_channel.py::test_endpoint_resolution_error_after_prior_success_is_retried` (FR-004, FR-006)
- [X] T013 [P] [US2] Teste: `EndpointResolutionError` levantada **antes** de qualquer resolução bem-sucedida (`endpointId` nunca existiu desde o startup) continua fatal/permanente — fail-fast de SF-018 preservado, sem regressão — já coberto pelo teste pré-existente `test_endpoint_resolution_error_is_not_retried` em `agents/windows-audio-agent/tests/test_capture_channel.py` (confirmado passando após T010/T011, sem necessidade de teste duplicado) (FR-005, FR-006)

### Implementation for User Story 2

- [X] T010 [US2] Introduzir a flag local `resolved_at_least_once: bool` (inicia `False`) no laço de `capture_channel`, setada para `True` via um callback `on_resolved` passado a `_capture_once` e invocado logo após `resolve_device(...)` suceder (não no retorno de `_capture_once` inteira — corrigido após revalidação manual Windows expor que o retorno normal só ocorre no shutdown por `stop_event`, ver `docs/validation/sf-019-windows.md` e `research.md` §3) — `agents/windows-audio-agent/src/assistant_hub_audio/capture.py` (depends on T002) (FR-004)
- [X] T011 [US2] No bloco `except EndpointResolutionError`, ramificar por `resolved_at_least_once`: se `True`, tratar como transitório (log de aviso + `_retry_after_wait()`); se `False`, manter o comportamento fatal/permanente já existente (log de erro + `raise`) — `agents/windows-audio-agent/src/assistant_hub_audio/capture.py` (depends on T010) (FR-004, FR-005)
- [X] T014 [US2] Teste de integração (pós-implementação, não TDD-first): após uma espera motivada por `notpresent` transitório (T011), um `arrived` subsequente acorda a espera e retoma a captura no mesmo `endpointId` (integração do fix do Bug B com o mecanismo de `woke_on_arrival` já existente de FR-003/spec 006) — `agents/windows-audio-agent/tests/test_capture_channel.py` (depends on T011) (FR-004)
- [X] T015 [P] Rodar `cd agents/windows-audio-agent && python3 -m compileall -q src && PYTHONPATH=src python3 -m pytest -q tests -k "hotplug or capture or mmdevice_notifications"` confirmando ausência de regressão introduzida por T010/T011 (FR-006, SC-004)

**Checkpoint**: As duas causas do sintoma da issue #22 estão corrigidas e cobertas por teste automatizado, sem dependência de hardware — MVP completo (US1 + US2, ambas P1, necessárias juntas para o comportamento real observado).

---

## Phase 5: User Story 3 - Evidência de validação manual em Windows real atualizada (Priority: P3)

**Goal**: `docs/validation/sf-019-windows.md` reflete o resultado real das correções dos Bugs A e B contra hardware/COM Windows real (FR-007/SC-001..SC-003/SC-005)

**Independent Test**: seguir os "Critérios de validação Windows" da issue #22 em host real (run, unplug, replug) e registrar o resultado

### Implementation for User Story 3

- [X] T016 [P] Rodar a suíte completa — `cd agents/windows-audio-agent && python3 -m compileall -q src && PYTHONPATH=src python3 -m pytest -q tests` (não só `-k "hotplug or capture or mmdevice_notifications"`) — confirmando que nenhum outro módulo regrediu, como baseline antes da revalidação manual (FR-006, SC-004)
- [ ] T017 [US3] Executar a revalidação manual Windows de `specs/010-sf-019-callback-notpresent-fix/quickstart.md` §2 (passos 1–8: `run --profile <perfil-com-endpointId>`, unplug sem `TypeError`, worker vivo aguardando notpresent transitório, replug resume no mesmo `endpointId`) com as correções aplicadas, e atualizar `docs/validation/sf-019-windows.md` com ambiente, commit, passos e resultado (PASS, PASS parcial explícito, ou nova causa raiz), referenciando a issue #22 (FR-007, SC-001, SC-002, SC-003, SC-005)

**Checkpoint**: Todas as user stories têm evidência — automatizada (US1/US2) e manual (US3) — antes do gate G3 (Validate).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirmar limites de escopo e preparar o gate G3→G4

- [X] T018 [P] Confirmar que nenhuma mudança desta correção toca código de SF-020 (captura por processo), `default_microphone()` WASAPI-aware, ou o contrato `transcript-event.v2` — revisão de diff (FR-008)
- [ ] T019 Preparar diff resumido, riscos e evidências de teste (suíte automatizada T009/T015/T016 + resultado manual T017) para o PR draft, conforme regra operacional da constituição ("Ao final do ciclo: diff resumido, riscos, testes executados e evidências") — depends on T017

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — T001 é uma checagem, não bloqueia nada
- **Foundational (Phase 2)**: Depende de Setup. T002 confirma a base antes de qualquer user story
- **User Story 1 (Phase 3)**: Depende de Foundational. T003/T004/T005 (mesmo arquivo, métodos distintos) → T006 → T007/T008/T009
- **User Story 2 (Phase 4)**: Depende de Foundational. Independente de US1 no código (arquivo diferente: `capture.py` vs `mmdevice_notifications.py`), mas ambas são necessárias juntas para o comportamento real de ponta a ponta (spec.md, User Story 2 "Why this priority")
- **User Story 3 (Phase 5)**: Depende de US1 (T003-T006) e US2 (T010-T011) estarem aplicados — a revalidação manual (T017) prova as duas correções juntas
- **Polish (Phase 6)**: T019 depende de T017

### Parallel Opportunities

- T004 e T005 (US1, mesmo arquivo `mmdevice_notifications.py` mas métodos distintos) podem ser escritas em paralelo antes de mesclar; T007 e T008 (testes) podem rodar em paralelo
- T012 e T013 (US2, `test_capture_channel.py`) podem ser escritas em paralelo — casos de teste distintos
- T009 (US1) e T015 (US2) podem rodar em paralelo depois que cada implementação estiver pronta
- T016 (US3, suíte completa) pode rodar em paralelo com T018 (revisão de escopo)
- T017 (revalidação manual, requer host Windows real) é o único item que não pode ser automatizado — bloqueia T019

---

## Parallel Example: User Story 1 + User Story 2

```bash
# Após Foundational (T002), US1 e US2 tocam arquivos diferentes e podem avançar em paralelo:
Task: "Add `this` param to IMMNotificationClient_On* in mmdevice_notifications.py"       # T003-T005 (US1)
Task: "Add resolved_at_least_once flag in capture.py's capture_channel"                   # T010 (US2)
```

---

## Implementation Strategy

### MVP = User Story 1 + User Story 2 juntas

Diferente de um MVP tipicamente single-story, a própria spec declara que as duas User Stories P1 são
necessárias em conjunto para o comportamento real observado no Windows (o Bug B só se manifesta como
"worker morre" *porque* o Bug A impede o evento de remoção de chegar a tempo). Entregar só uma das duas
não resolve o sintoma relatado na issue #22 de ponta a ponta.

1. Setup + Foundational (T001-T002)
2. User Story 1 completa (T003-T009) — callback aceita chamada real sem erro
3. User Story 2 completa (T010-T015) — notpresent transitório não é mais fatal
4. **STOP and VALIDATE**: suíte automatizada completa (T016) antes da revalidação manual
5. User Story 3 (T017) — prova real em hardware Windows
6. Polish (T018-T019) — fechamento do gate G3/G4

### Incremental Delivery

1. Setup + Foundational → base intacta
2. US1 → callback COM não quebra mais com `TypeError` (cobertura automatizada)
3. US2 → `notpresent` transitório não mata mais o worker (cobertura automatizada) — MVP completo
4. US3 → prova real em hardware Windows, fechando a issue #22
5. Polish → diff/riscos/evidências para o PR

---

## Notes

- `[P]` tasks = arquivos diferentes ou métodos independentes no mesmo arquivo, sem dependência sequencial real
- `[Story]` mapeia a task à user story correspondente para rastreabilidade
- T017 exige acesso a hardware Windows real e não pode ser executada por automação (P10)
- Commit após cada task ou grupo lógico
