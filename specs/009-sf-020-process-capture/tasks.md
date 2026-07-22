---

description: "Task list for process-based WASAPI loopback capture (SF-020, Issue #19)"
---

# Tasks: Captura de áudio por processo (WASAPI loopback por app)

**Input**: Design documents from `/specs/009-sf-020-process-capture/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/README.md (sem mudança de
schema), quickstart.md

**Tests**: incluídos abaixo, integrados a cada user story (spec.md exige testabilidade sem hardware —
FR-009 — e critérios de aceite explícitos por cenário).

**Organization**: Tasks agrupadas por user story (spec.md). Feature prospectiva — nenhuma mudança de
código foi aplicada antes da spec/plano/tasks.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependências)
- **[Story]**: A qual user story esta task pertence (US1, US2, US3)
- Caminhos de arquivo exatos incluídos nas descrições

---

## Phase 1: Setup

**Purpose**: Corrigir o escopo de dependência de `psutil` identificado em research.md §3

- [X] T001 Declarar `psutil` como dependência direta, sem marcador de plataforma (diferente de `pycaw`, que é `sys_platform == 'win32'`), em `agents/windows-audio-agent/pyproject.toml` — necessário porque `process_resolver.py` (Foundational/US1) é deliberadamente multiplataforma e testável em WSL, onde `pycaw` (e seu transitivo `psutil`) hoje não é instalado (research.md §3, correção de escopo)

**Checkpoint**: `psutil` instalável e importável em qualquer plataforma antes de qualquer código depender dele.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Permitir declarar um canal por processo no perfil — bloqueia as 3 user stories, já que nenhuma pode ser testada sem uma forma de configurar o seletor

**⚠️ CRITICAL**: Nenhuma user story pode ser implementada/testada sem esta base

- [X] T002 Adicionar campos `process_id: int | None = None` e `process_name: str | None = None` a `DeviceSelector`, e estender `validate()` para incluí-los no conjunto mutuamente exclusivo (`endpointId`/`index`/`nameRegex`/`default`/`processId`/`processName` — exatamente um, sem a exceção de coexistência que só vale para `endpointId`+`index`); `process_id` MUST ser inteiro positivo, `process_name` MUST NOT ser vazio/whitespace — `agents/windows-audio-agent/src/assistant_hub_audio/profiles.py` (data-model.md) (FR-001)
- [X] T003 Atualizar `_selector_from_dict`/`channel_to_dict` em `agents/windows-audio-agent/src/assistant_hub_audio/profiles.py` para (de)serializar `processId`/`processName` no YAML do perfil — `agents/windows-audio-agent/src/assistant_hub_audio/profiles.py` (depends on T002) (FR-001)
- [X] T004 [P] Testes de validação do `DeviceSelector` com `process_id`/`process_name`: exclusividade com os seletores já existentes, PID não positivo rejeitado, nome vazio rejeitado, round-trip de serialização YAML — `agents/windows-audio-agent/tests/test_profiles.py` (depends on T002, T003) (FR-001)

**Checkpoint**: Um canal por perfil já pode ser declarado por PID ou nome — as user stories abaixo podem ser implementadas.

---

## Phase 3: User Story 1 - Operador liga um canal a um processo/aplicativo específico (Priority: P1) 🎯 MVP

**Goal**: Um canal configurado por processo captura, via loopback WASAPI real, apenas o áudio daquele processo (e sua árvore), produzindo eventos de transcrição com os mesmos metadados v2 obrigatórios que canais por dispositivo (FR-001..FR-003)

**Independent Test**: `specs/009-sf-020-process-capture/quickstart.md` §2 (canal real por processo em Windows) — ou, sem hardware, os testes de resolução (T007) e de integração no laço de captura (T012/T013) com um provider de processo fake

### Implementation for User Story 1

- [X] T005 [US1] Criar `agents/windows-audio-agent/src/assistant_hub_audio/process_resolver.py` (puro, sem `comtypes`, testável em qualquer plataforma): `resolve_process(selector: DeviceSelector) -> ProcessResolution` usando `psutil.process_iter`/`psutil.Process`/`psutil.pid_exists`, retornando `pid`/`name`/`username` (mesmo nome de entidade de data-model.md) — checagem de mesmo usuário do processo atual (`psutil.Process().username()`) já incluída (FR-011) (depends on T002) (FR-001, FR-011)
- [X] T006 [US1] Em `resolve_process()`, aplicar a política de falha explícita: PID que não existe, ou nome com zero ou múltiplas correspondências, levanta uma exceção específica e identificável (mesma filosofia de `find_device_for_endpoint`/FR-005) — `agents/windows-audio-agent/src/assistant_hub_audio/process_resolver.py` (depends on T005) (FR-005)
- [X] T007 [P] [US1] Testes de `resolve_process()`: PID existente do mesmo usuário resolve com sucesso; PID inexistente falha explicitamente; nome com exatamente 1 correspondência resolve; nome com 0 ou múltiplas correspondências falha explicitamente (zero incidentes de fallback silencioso) — `agents/windows-audio-agent/tests/test_process_resolver.py` (novo arquivo) (depends on T006) (FR-001, FR-005, SC-004)
- [X] T008 [US1] Em `agents/windows-audio-agent/src/assistant_hub_audio/process_capture.py` (Windows-only, import lazy de `comtypes`, novo arquivo): declarar manualmente `AUDIOCLIENT_ACTIVATION_PARAMS`, `AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS` e a interface COM `IActivateAudioInterfaceCompletionHandler` (research.md §1) — só as declarações de struct/interface, sem lógica de ativação ainda — `agents/windows-audio-agent/src/assistant_hub_audio/process_capture.py` (FR-002)
- [X] T009 [US1] Em `process_capture.py`, implementar a chamada assíncrona a `ActivateAudioInterfaceAsync` com `ActivationType=AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK` e `ProcessLoopbackMode=PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE` por padrão (research.md §1), usando a interface `IActivateAudioInterfaceCompletionHandler` de T008 para obter o `IAudioClient` escopado ao PID resolvido — `agents/windows-audio-agent/src/assistant_hub_audio/process_capture.py` (depends on T008) (FR-002)
- [X] T010 [US1] Em `process_capture.py`, expor um provider que consome o `IAudioClient` de T009 via `IAudioCaptureClient` (loop de leitura de buffers PCM), com uma interface equivalente à já usada pelo caminho `PyAudioWPatch` (abrir/ler/fechar) para simplificar a integração em `capture.py` — `agents/windows-audio-agent/src/assistant_hub_audio/process_capture.py` (depends on T009) (FR-002)
- [X] T011 [US1] Em `agents/windows-audio-agent/src/assistant_hub_audio/capture.py`, ramificar o worker do canal: quando `channel.selector.process_id`/`process_name` estiver definido, usar `process_resolver.resolve_process()` + o provider de `process_capture.py` (T010) em vez de `resolve_device()`/`audio.open()` (PyAudioWPatch), produzindo o mesmo formato de dict de device usado para montar o evento de transcrição (`index=None`, `endpointId=None`, `name=<processo legível>`, data-model.md) — `agents/windows-audio-agent/src/assistant_hub_audio/capture.py` (depends on T005, T010) (FR-002, FR-003)
- [X] T012 [P] [US1] Teste: um evento de transcrição produzido por um canal por processo (fake, sem COM real) preenche `sessionId`/`channelId`/`label`/`sourceType`/`device`/`text`/`latencyMs`/`occurredAt` como qualquer canal por dispositivo, com `device.index=None`, `device.endpointId=None`, `device.name` legível (data-model.md) — `agents/windows-audio-agent/tests/test_capture_channel.py` (depends on T011) (FR-003)
- [X] T013 [P] [US1] Teste: dois canais simultâneos (um por processo fake, um por `endpointId` fake) na mesma sessão nunca misturam áudio/metadados entre si (isolamento por canal, ADR-0007) — `agents/windows-audio-agent/tests/test_capture_channel.py` (depends on T011) (FR-002)
- [X] T014 [P] [US1] Rodar `cd agents/windows-audio-agent && python3 -m compileall -q src && PYTHONPATH=src python3 -m pytest -q tests -k "process_resolver or capture or profiles"` (quickstart.md §1) confirmando ausência de regressão introduzida por T002-T011

**Checkpoint**: Canal por processo configurável e integrado ao worker, coberto por teste automatizado — a prova real da captura COM depende da revalidação manual (Phase 5/US3).

---

## Phase 4: User Story 2 - Falha explícita quando o processo alvo desaparece (Priority: P2)

**Goal**: Canal por PID falha permanentemente quando o processo sai; canal por nome re-segue automaticamente uma única nova instância inequívoca, ou falha explicitamente se a nova instância for ambígua (FR-004..FR-006, FR-012)

**Independent Test**: `quickstart.md` §2 passo 5 — ou, sem hardware, os testes T018/T019/T020 com um provider fake simulando saída/reaparecimento do processo

### Implementation for User Story 2

- [X] T015 [US2] No worker do canal por processo (`capture.py`), detectar quando o PID em uso não existe mais (`psutil.pid_exists`) e ramificar: se o canal foi selecionado por **PID**, propagar falha permanente (mesmo caminho fatal já usado por `EndpointResolutionError` sem `woke_on_arrival`, FR-006); se por **nome**, disparar nova `resolve_process()` (FR-012) — `agents/windows-audio-agent/src/assistant_hub_audio/capture.py` (depends on T006, T011) (FR-004, FR-006)
- [X] T018 [P] [US2] Teste: canal selecionado por **PID** cujo processo sai durante a captura falha de forma explícita e permanente, sem tentar re-seguir — `agents/windows-audio-agent/tests/test_capture_channel.py` (depends on T015) (FR-006, SC-003)
- [X] T016 [US2] Quando a re-resolução por nome (T015) encontrar exatamente uma nova correspondência, retomar a captura no novo PID sem reiniciar o processo do canal — `agents/windows-audio-agent/src/assistant_hub_audio/capture.py` (depends on T015) (FR-012)
- [X] T019 [P] [US2] Teste: canal selecionado por **nome** cujo processo sai e uma única nova instância do mesmo nome aparece em seguida retoma automaticamente a captura no novo PID, sem falha explícita nem reinício manual — `agents/windows-audio-agent/tests/test_capture_channel.py` (depends on T016) (FR-012, SC-003)
- [X] T017 [US2] Quando a re-resolução por nome (T015) encontrar zero ou múltiplas correspondências, tratar como falha explícita permanente para aquele canal (mesma política de ambiguidade de FR-005) — `agents/windows-audio-agent/src/assistant_hub_audio/capture.py` (depends on T015) (FR-012, FR-005)
- [X] T020 [P] [US2] Teste: canal selecionado por **nome** cujo processo sai e múltiplas novas instâncias ambíguas aparecem falha de forma explícita (mesma política de FR-005), em vez de escolher uma arbitrariamente — `agents/windows-audio-agent/tests/test_capture_channel.py` (depends on T017) (FR-012, FR-005, SC-004)
- [X] T021 [P] Rodar `cd agents/windows-audio-agent && python3 -m compileall -q src && PYTHONPATH=src python3 -m pytest -q tests -k "process_resolver or capture or profiles"` confirmando ausência de regressão introduzida por T015-T017 (FR-006)

**Checkpoint**: As duas políticas de falha (PID fatal, nome re-segue ou falha ambígua) cobertas por teste automatizado, sem dependência de hardware.

---

## Phase 5: User Story 3 - Compatibilidade validada com hot-plug e perfis existentes (Priority: P3)

**Goal**: Canal por processo convive com canais por `endpointId` (SF-018) e com o listener de hot-plug (SF-019) na mesma sessão sem interferência, validado em hardware Windows real (FR-007, FR-008)

**Independent Test**: `quickstart.md` §2 passo 7 — perfil misturando canal por processo e canal por `endpointId`, evento de hot-plug provocado no canal por dispositivo

### Implementation for User Story 3

- [X] T022 [P] [US3] Teste: perfil com um canal por processo (fake) e um canal por `endpointId` (fake) na mesma sessão — um evento de hot-plug (arrival/removal) no canal por dispositivo não afeta o canal por processo, e vice-versa — `agents/windows-audio-agent/tests/test_capture_channel.py` (FR-007, FR-008)
- [X] T023 [P] Rodar a suíte completa — `cd agents/windows-audio-agent && python3 -m compileall -q src && PYTHONPATH=src python3 -m pytest -q tests` (não só o filtro por palavra-chave) — confirmando que nenhum outro módulo (`test_hotplug.py`, `test_endpoints.py`, `test_mmdevice_notifications`) regrediu, como baseline antes da revalidação manual (FR-006, SC-002)
- [ ] T024 [US3] Executar a revalidação manual Windows de `specs/009-sf-020-process-capture/quickstart.md` §2 (passos 1–8: canal real por processo, saída de processo por PID/nome, restrição de usuário, coexistência com `endpointId`/hot-plug) em host Windows build ≥ 20348, e registrar o resultado em `docs/validation/sf-020-windows.md` (novo arquivo, mesmo padrão de `sf-018-windows.md`/`sf-019-windows.md`) (FR-009, SC-001, SC-002, SC-003, SC-004, SC-005)

**Checkpoint**: Todas as user stories têm evidência — automatizada (US1/US2) e manual (US3) — antes do gate G3 (Validate).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirmar limites de escopo e preparar o gate G3→G4

- [X] T025 [P] Confirmar que nenhuma mudança desta feature toca UI desktop, persistência de sessão, ou o comportamento de janela adaptativa já entregue (SF-022) — revisão de diff (FR-010)
- [X] T026 [P] Adicionar um perfil de exemplo usando `processName` em `samples/audio-profiles/` (ex.: `process-capture-example.yaml`), ilustrando o novo seletor — documentação, sem mudança de contrato
- [ ] T027 Preparar diff resumido, riscos e evidências de teste (suíte automatizada T014/T021/T023 + resultado manual T024) para o PR draft, conforme regra operacional da constituição ("Ao final do ciclo: diff resumido, riscos, testes executados e evidências") — depends on T024

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — T001 corrige o escopo de `psutil` antes de qualquer código depender dele
- **Foundational (Phase 2)**: Depende de Setup. T002→T003→T004 — bloqueia todas as user stories (nenhuma pode declarar um canal por processo sem isso)
- **User Story 1 (Phase 3)**: Depende de Foundational. T005→T006→T007; T008→T009→T010 independente de T005/T006/T007 (arquivo diferente) até T011 combiná-los; T011 depende de T005 e T010; T012/T013/T014 depois de T011
- **User Story 2 (Phase 4)**: Depende de US1 (T006, T011) — a lógica de falha/re-seguimento se apoia na resolução (T006) e na integração do worker (T011) já existirem
- **User Story 3 (Phase 5)**: Depende de US1 (T011) e US2 (T015-T017) estarem aplicados — a revalidação manual (T024) prova as três user stories juntas
- **Polish (Phase 6)**: T027 depende de T024; T025/T026 independentes (revisão de escopo e documentação)

### Parallel Opportunities

- T005 (`process_resolver.py`) e T008-T010 (`process_capture.py`) tocam arquivos diferentes e podem avançar em paralelo antes de T011 combiná-los
- T012 e T013 (US1, mesmo arquivo de teste, casos distintos) podem ser escritos em paralelo
- T018, T019 e T020 (US2, mesmo arquivo de teste, casos distintos) podem ser escritos em paralelo
- T014, T021 e T023 (execuções de suíte) podem rodar em paralelo com T025/T026 (revisão de escopo/documentação)
- T024 (revalidação manual, requer host Windows build ≥ 20348) é o único item que não pode ser automatizado — bloqueia T027

---

## Parallel Example: User Story 1

```bash
# Após Foundational (T002-T004), process_resolver.py e process_capture.py avançam em paralelo:
Task: "Create resolve_process() in process_resolver.py using psutil"   # T005-T007 (US1)
Task: "Declare AUDIOCLIENT_ACTIVATION_PARAMS/IActivateAudioInterfaceCompletionHandler in process_capture.py"  # T008 (US1)
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T004) — CRITICAL, bloqueia todas as stories
3. Complete Phase 3: User Story 1 (T005-T014) — canal por processo captura de verdade
4. **STOP and VALIDATE**: testar User Story 1 independentemente (suíte automatizada; revalidação manual fica para US3)
5. Deploy/demo se pronto

### Incremental Delivery

1. Setup + Foundational → perfil já aceita seletor por processo
2. US1 → captura por processo funciona, metadados v2 preservados (MVP)
3. US2 → falhas de processo tratadas explicitamente (PID fatal, nome re-segue)
4. US3 → prova real em hardware Windows + compatibilidade com SF-018/SF-019, fechando a issue #19
5. Polish → revisão de escopo + sample de perfil + diff/riscos/evidências para o PR

### Parallel Team Strategy

Com múltiplos desenvolvedores, após Foundational: um dev em `process_resolver.py` (T005-T007), outro em
`process_capture.py` (T008-T010) — convergem em T011 (`capture.py`).

---

## Notes

- `[P]` tasks = arquivos diferentes ou casos de teste independentes no mesmo arquivo
- `[Story]` mapeia a task à user story correspondente para rastreabilidade
- T024 exige acesso a hardware Windows build ≥ 20348 e não pode ser executada por automação (P10)
- Commit após cada task ou grupo lógico
