---

description: "Task list for the MMDevice notification provider fix (Issue #20)"
---

# Tasks: Correção do provider real de notificação MMDevice (Issue #20)

**Input**: Design documents from `/specs/009-issue-20-mmdevice-notification-fix/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md (N/A — sem entidades), quickstart.md

**Tests**: FR-004 exige explicitamente um teste de regressão; os demais testes já existentes cobrem o
comportamento tocado por esta correção — incluídos abaixo.

**Organization**: Tasks agrupadas por user story (spec.md). Esta é uma correção retroativa (issue #20,
"próximo ciclo SDD curto"): a correção de código já está aplicada na árvore de trabalho. As tasks abaixo
refletem esse estado — marcadas `[X]` onde o diff já satisfaz o requisito, `[ ]` onde o trabalho ainda
está pendente (revalidação manual Windows, FR-005).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependências)
- **[Story]**: A qual user story esta task pertence (US1, US2, US3)
- Caminhos de arquivo exatos incluídos nas descrições

---

## Phase 1: Setup

**Purpose**: Confirmar que nenhuma dependência/infraestrutura nova é necessária (FR-006)

- [X] T001 Confirmar que `agents/windows-audio-agent/pyproject.toml` não precisa de nenhuma dependência nova (`pycaw`/`comtypes` já presentes, `sys_platform == 'win32'`) para esta correção — checagem de diff, sem alteração de arquivo (FR-006, SC-003)

**Checkpoint**: Nenhuma instalação nova necessária; ambiente WSL existente já serve para a suíte automatizada.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Confirmar que a base de SF-019 (`specs/006-sf-019-hotplug-listener/`) sobre a qual esta correção se apoia está intacta

**⚠️ CRITICAL**: Nenhuma user story desta correção pode ser avaliada sem esta base

- [X] T002 Confirmar que `HotplugListener`, `ChannelHotplugSignal`, `NotificationProvider` (Protocol), `NullNotificationProvider` e `get_notification_provider()` em `agents/windows-audio-agent/src/assistant_hub_audio/hotplug.py` permanecem com a mesma interface pública de `specs/006-sf-019-hotplug-listener/` (nenhuma mudança de assinatura) — checagem de diff

**Checkpoint**: Base de SF-019 intacta — as user stories abaixo podem ser avaliadas.

---

## Phase 3: User Story 1 - Worker de captura sobrevive à inicialização do listener em Windows real (Priority: P1) 🎯 MVP

**Goal**: `HotplugListener.__init__` não derruba mais o worker em host Windows real por falta do módulo `comtypes.gen.MMDeviceAPILib` (FR-001)

**Independent Test**: `specs/009-issue-20-mmdevice-notification-fix/quickstart.md` §2 (revalidação manual Windows) — worker permanece ativo após a construção do listener, sem `ModuleNotFoundError`

### Implementation for User Story 1

- [X] T003 [US1] Substituir o import de `IMMNotificationClient` a partir de `comtypes.gen.MMDeviceAPILib` por uma declaração estática (IID fixo `{7991EEC9-7E89-4D85-8390-6C703CEC60C0}` + `comtypes.STDMETHOD` para `OnDeviceStateChanged`/`OnDeviceAdded`/`OnDeviceRemoved`/`OnDefaultDeviceChanged`/`OnPropertyValueChanged`) em `_build_notification_client_interface()` — `agents/windows-audio-agent/src/assistant_hub_audio/mmdevice_notifications.py` (FR-001)
- [X] T004 [US1] Atualizar `MMDeviceNotificationProvider.subscribe()` para usar a interface declarada em T003 ao construir `_NotificationClient(COMObject)` e registrar via `RegisterEndpointNotificationCallback`, sem chamar `comtypes.client.GetModule` em nenhum ponto — `agents/windows-audio-agent/src/assistant_hub_audio/mmdevice_notifications.py` (depends on T003) (FR-001)
- [X] T005 [P] [US1] Rodar `cd agents/windows-audio-agent && python3 -m compileall -q src && PYTHONPATH=src python3 -m pytest -q tests -k "hotplug or capture"` (quickstart.md §1) confirmando ausência de regressão introduzida por T003/T004, incluindo debounce/isolamento por canal/tradução de eventos já especificados em SF-019 (baseline registrado: 30 passed, `docs/validation/sf-019-windows.md`) (FR-007, SC-002)

**Checkpoint**: Correção de FR-001 aplicada e coberta pela suíte automatizada disponível (a prova real depende da revalidação manual — Phase 5/US3).

---

## Phase 4: User Story 2 - Falha de assinatura degrada sem derrubar o canal (Priority: P2)

**Goal**: Qualquer falha em `provider.subscribe(...)` — inclusive além do `ModuleNotFoundError` original — deixa o listener inerte de forma permanente e local, sem derrubar o worker (FR-002/FR-003/FR-004, Clarifications 2026-07-22)

**Independent Test**: `tests/test_hotplug.py::test_listener_subscribe_failure_degrades_without_raising` — injeta falha em `subscribe()` e confirma que `HotplugListener.__init__` não propaga exceção

### Tests for User Story 2

- [X] T006 [P] [US2] Teste de regressão `test_listener_subscribe_failure_degrades_without_raising`: `subscribe()` levantando `ModuleNotFoundError` não propaga para `HotplugListener.__init__`, listener fica inerte e `close()` continua delegando ao provider — `agents/windows-audio-agent/tests/test_hotplug.py` (FR-004)

### Implementation for User Story 2

- [X] T007 [US2] Envolver a chamada `self._provider.subscribe(self.signal.handle_event)` em `HotplugListener.__init__` com `try/except Exception`, logando aviso explícito (log local do worker, sem sinalização cross-processo) e deixando o listener inerte de forma permanente para o tempo de vida do processo do canal, sem retry — `agents/windows-audio-agent/src/assistant_hub_audio/hotplug.py` (depends on T002) (FR-002)
- [X] T008 [US2] Confirmar que a política de degrade de T007 é consistente com a política já existente em `get_notification_provider` para falha de construção do provider (mesmo nível de log, sem retry em nenhuma das duas) — revisão cruzada em `agents/windows-audio-agent/src/assistant_hub_audio/hotplug.py` (depends on T007) (FR-003)

**Checkpoint**: Falha de assinatura (qualquer causa) não derruba mais o worker do canal — coberto integralmente por teste automatizado, sem dependência de hardware.

---

## Phase 5: User Story 3 - Evidência de validação manual em Windows real atualizada (Priority: P3)

**Goal**: `docs/validation/sf-019-windows.md` reflete o resultado real da correção (T003/T004/T007) contra hardware/COM Windows, fechando a pendência de revalidação (FR-005/SC-004)

**Independent Test**: repetir os passos 1–8 de `specs/009-issue-20-mmdevice-notification-fix/quickstart.md` §2 em host Windows real e registrar o resultado

### Implementation for User Story 3

- [X] T009 [P] [US3] Rodar a suíte completa — `cd agents/windows-audio-agent && python3 -m compileall -q src && PYTHONPATH=src python3 -m pytest -q tests` (não só `-k "hotplug or capture"`) — confirmando que nenhum outro módulo (`test_capture.py`, `test_endpoints.py`, `test_profiles.py`, `test_run_agent.py`) regrediu (baseline registrado: 60 passed, `docs/validation/sf-019-windows.md`) (FR-007, SC-002)
- [ ] T010 [US3] Executar a revalidação manual Windows de `specs/009-issue-20-mmdevice-notification-fix/quickstart.md` §2 (passos 1–8: `run --profile <perfil-com-endpointId>`, confirmar ausência de `ModuleNotFoundError`/`OSError`, replug físico, retomada automática) com a correção aplicada, e atualizar a seção "Pendente"/"run + hot-plug" de `docs/validation/sf-019-windows.md` com ambiente, commit, passos e resultado (PASS ou nova causa raiz), substituindo a pendência atual (FR-005, SC-001, SC-004)

**Checkpoint**: Todas as user stories têm evidência — automatizada (US1/US2) e manual (US3) — antes do gate G3 (Validate).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Fechar o ciclo SDD curto (P1 da constituição) e preparar o gate G3→G4

- [X] T011 [P] Confirmar que `specs/006-sf-019-hotplug-listener/research.md` (seção "Correção (SF-019, validação Windows 2026-07-22)") permanece consistente com `specs/009-issue-20-mmdevice-notification-fix/research.md` — sem contradição entre os dois registros de decisão técnica
- [ ] T012 Preparar diff resumido, riscos e evidências de teste (suíte automatizada T005/T009 + resultado manual T010) para o PR draft, conforme regra operacional da constituição ("Ao final do ciclo: diff resumido, riscos, testes executados e evidências") — depends on T010

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — T001 já satisfeito (nenhuma dependência nova)
- **Foundational (Phase 2)**: Depende de Setup. T002 confirma a base de SF-019 antes de qualquer user story
- **User Story 1 (Phase 3)**: Depende de Foundational. T003→T004→T005
- **User Story 2 (Phase 4)**: Depende de Foundational. Independente de US1 (arquivo/método diferente: `hotplug.py` vs `mmdevice_notifications.py`)
- **User Story 3 (Phase 5)**: Depende de US1 (T003/T004) e US2 (T007) estarem aplicados — a revalidação manual (T010) prova as duas correções juntas
- **Polish (Phase 6)**: T012 depende de T010

### Parallel Opportunities

- T005 (US1) e T006 (US2) podem rodar em paralelo — arquivos/áreas de teste diferentes dentro da mesma suíte
- T009 (US3, suíte completa) pode rodar em paralelo com T011 (revisão cruzada de research.md)
- T010 (revalidação manual, requer host Windows real) é o único item verdadeiramente pendente nesta correção — bloqueia T012

---

## Parallel Example: User Story 1 + User Story 2

```bash
# Após Foundational (T002), US1 e US2 tocam arquivos diferentes e podem ser conferidas em paralelo:
Task: "Confirm static IMMNotificationClient declaration in mmdevice_notifications.py"  # T003/T004 (US1)
Task: "Confirm subscribe() try/except degrade policy in hotplug.py"                    # T007/T008 (US2)
```

---

## Implementation Strategy

### Estado atual (correção retroativa)

Esta correção já foi implementada no working tree antes deste ciclo formal de SDD (issue #20, "próximo
ciclo SDD curto"). T001–T009 e T011 estão marcadas `[X]` porque o diff atual já as satisfaz — confirmado
por leitura de código e pela suíte automatizada (`docs/validation/sf-019-windows.md`: 30 passed no
filtro hotplug/capture, 60 passed na suíte completa).

### Trabalho restante (MVP para fechar o ciclo)

1. **T010** — única task genuinamente pendente: revalidação manual em host Windows real (requer
   hardware/COM real, fora do alcance de execução automatizada por P10).
2. **T012** — preparar diff resumido/riscos/evidências para o PR draft, uma vez que T010 tenha um
   resultado (PASS ou nova causa raiz documentada).

### Incremental Delivery

1. Setup + Foundational confirmados (T001–T002) → base intacta
2. US1 confirmada (T003–T005) → causa raiz corrigida, sem regressão automatizada
3. US2 confirmada (T006–T008) → rede de segurança de degrade coberta por teste
4. US3 pendente (T009 feito, T010 em aberto) → falta a prova real em hardware Windows
5. Polish (T011 feito, T012 aguardando T010) → fechamento do gate G3/G4

---

## Notes

- `[P]` tasks = arquivos diferentes, sem dependências
- `[Story]` mapeia a task à user story correspondente para rastreabilidade
- T010 exige acesso a hardware Windows real e não pode ser executada por automação (P10) — é a única
  task que bloqueia o fechamento formal deste ciclo SDD curto
- Commit após cada task ou grupo lógico
