---

description: "Task list template for feature implementation"
---

# Tasks: Tornar `default_microphone()` WASAPI-aware (Issue #27)

**Input**: Design documents from `/specs/011-default-mic-wasapi-aware/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [quickstart.md](./quickstart.md)

**Tests**: Solicitados explicitamente pela spec (User Story 3 / FR-005: cobertura de regressão hoje inexistente) — incluídos como tarefas de teste-primeiro por história.

**Organization**: Tarefas agrupadas por user story (P1/P2/P3 de `spec.md`) para permitir implementação e teste independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: A qual user story a tarefa pertence (US1, US2, US3)
- Caminhos de arquivo exatos incluídos em cada descrição

## Path Conventions

Projeto único existente: `agents/windows-audio-agent/src/assistant_hub_audio/` e `agents/windows-audio-agent/tests/`, conforme `plan.md` § Project Structure. Nenhum caminho novo fora dessa árvore.

---

## Phase 1: Setup

**Purpose**: Confirmar baseline verde antes de qualquer mudança de código

- [X] T001 Rodar a suíte atual como baseline (`python -m compileall agents/windows-audio-agent/src && PYTHONPATH=agents/windows-audio-agent/src pytest -q agents/windows-audio-agent/tests`, mesmo comando do job `windows-audio-agent-unit` do CI) e confirmar que passa 100% antes de iniciar a correção — nenhuma mudança de arquivo nesta tarefa

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura de teste compartilhada por US1 e US2 — sem isso nenhum teste de `default_microphone()` pode ser escrito

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase

- [X] T002 Criar `agents/windows-audio-agent/tests/test_devices.py` com um fake de `pyaudio.PyAudio` (ex.: `_FakeWasapiAudio`) que implementa `get_host_api_info_by_type` (com `index`/`defaultInputDevice` configuráveis) e `get_device_info_by_index`, no mesmo padrão de `_FakePyAudioModule`/`_FakeAudio` já usado em `agents/windows-audio-agent/tests/test_capture_channel.py:59-68` (Decisão 3 de `research.md`)

**Checkpoint**: fixture de teste pronta — implementação das user stories pode começar

---

## Phase 3: User Story 1 - Canal de microfone default recebe `endpointId` estável via WASAPI (Priority: P1) 🎯 MVP

**Goal**: `default_microphone()` resolve o dispositivo de entrada consultando o host API WASAPI (não mais o default global do PortAudio), e esse dispositivo passa a receber `endpointId` preenchido via a correlação já existente

**Independent Test**: em host Windows real com um dispositivo de entrada `isDefault: true` no WASAPI, rodar `assistant-hub-audio run` sem `--profile` e confirmar que o canal de microfone recebe o mesmo `endpointId` reportado por `list-devices` para esse dispositivo (ver `quickstart.md` Parte 2)

### Tests for User Story 1 ⚠️

> Escrever esta tarefa antes de T004 e confirmar que falha contra o `devices.py` atual (que ainda usa `get_default_input_device_info()`)

- [X] T003 [P] [US1] Escrever teste que simula host API WASAPI com `defaultInputDevice` válido e um segundo host API (ex.: MME) marcado como default global do PortAudio, confirmando que `default_microphone()` **deveria** devolver o dispositivo do host API WASAPI (não o do MME) em `agents/windows-audio-agent/tests/test_devices.py::test_default_microphone_resolves_wasapi_default` — depende de T002

### Implementation for User Story 1

- [X] T004 [US1] Implementar em `agents/windows-audio-agent/src/assistant_hub_audio/devices.py` (`default_microphone()`, linhas 72-73) a resolução via `audio.get_host_api_info_by_type(pyaudio.paWASAPI)["defaultInputDevice"]` + `audio.get_device_info_by_index(...)`, espelhando o padrão já usado por `default_loopback()` (linhas 76-86) — depende de T003 (teste deve ficar verde após esta tarefa)
- [X] T005 [US1] Adicionar teste confirmando que `resolve_device()`/`correlate_devices()` preenchem `endpointId` (não `None`) para um canal com seletor `default: true` de microfone, usando o dispositivo resolvido em T004 (Acceptance Scenario 2 da User Story 1) em `agents/windows-audio-agent/tests/test_devices.py::test_default_microphone_channel_gets_endpoint_id` — depende de T004

**Checkpoint**: User Story 1 completa e testável de forma independente (MVP)

---

## Phase 4: User Story 2 - Ausência de default WASAPI de entrada falha de forma explícita (Priority: P2)

**Goal**: quando o host API WASAPI não existe ou não tem `defaultInputDevice` válido, `default_microphone()` levanta um erro explícito em vez de qualquer fallback silencioso para outro host API

**Independent Test**: em teste automatizado (WSL, sem hardware), simular ausência de `defaultInputDevice` WASAPI e confirmar que `default_microphone()` levanta erro claro, sem devolver dispositivo de outro host API

### Tests for User Story 2 ⚠️

> Escrever antes de T007 e confirmar que falha contra o `devices.py` de T004 (que ainda não trata esse caso)

- [X] T006 [P] [US2] Escrever teste que simula host API WASAPI sem `defaultInputDevice` válido (ausente ou `-1`) e confirma que `default_microphone()` levanta `RuntimeError` com mensagem explícita, sem devolver um dispositivo de outro host API — `agents/windows-audio-agent/tests/test_devices.py::test_default_microphone_raises_without_wasapi_default` — depende de T002

### Implementation for User Story 2

- [X] T007 [US2] Adicionar em `default_microphone()` (`agents/windows-audio-agent/src/assistant_hub_audio/devices.py`) o `raise RuntimeError("Default WASAPI input device was not found")` quando o host API WASAPI não expõe `defaultInputDevice` válido (Decisão 2 de `research.md`, mesmo estilo de `default_loopback()` linha 86) — depende de T004 e T006 (teste deve ficar verde após esta tarefa)

**Checkpoint**: User Stories 1 e 2 funcionam de forma independente

---

## Phase 5: User Story 3 - Cobertura de teste automatizado para `default_microphone()` (Priority: P3)

**Goal**: fechar a lacuna de cobertura zero já confirmada na investigação da issue, garantindo que a suíte completa protege o comportamento corrigido e não regride `default_loopback()`

**Independent Test**: rodar a suíte automatizada completa do `windows-audio-agent` e confirmar que os testes novos de `default_microphone()` (T003, T005, T006) passam junto com o restante da suíte, sem regressão em `default_loopback()`

### Implementation for User Story 3

- [X] T008 [P] [US3] Adicionar teste confirmando que `default_loopback()` continua devolvendo o mesmo resultado de antes da correção (mesmo fake de host API WASAPI, sem alteração de comportamento — SC-004) em `agents/windows-audio-agent/tests/test_devices.py::test_default_loopback_unaffected` — depende de T002 (independente de T004/T007, arquivo/função não tocados por esta correção)
- [X] T009 [US3] Rodar a suíte completa (`python -m compileall agents/windows-audio-agent/src && PYTHONPATH=agents/windows-audio-agent/src pytest -q agents/windows-audio-agent/tests`) e confirmar 100% verde, incluindo T003, T005, T006 e T008 (SC-002) — depende de T005, T007, T008

**Checkpoint**: todas as user stories funcionais, cobertura de regressão fechada

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: validação manual obrigatória (P10) que fecha o critério de saída da feature

- [ ] T010 Executar a Parte 2 de `specs/011-default-mic-wasapi-aware/quickstart.md` em host Windows real (`list-devices`, `run` sem `--profile`, inspecionar `endpointId` no evento `transcript-event.v2` do canal `local_microphone`, confirmar canal de loopback inalterado) e registrar o resultado (PASS/PASS parcial, data, commit) em `docs/validation/sf-015-default-mic.md`, atualizando a limitação 1 já documentada — depende de T009
- [X] T011 Confirmar que a suíte de contrato de `services/transcription-service` (`PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests/test_ws_audio_contract.py`) permanece verde após a correção, evidenciando que `contracts/transcript-event.v2.schema.json` não foi impactado (FR-006) — depende de T009

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — T001 pode rodar imediatamente
- **Foundational (Phase 2)**: depende de T001 — BLOQUEIA todas as user stories
- **User Story 1 (Phase 3)**: depende de T002
- **User Story 2 (Phase 4)**: depende de T002; T007 depende também de T004 (mesma função, mesmo arquivo — sequencial após US1)
- **User Story 3 (Phase 5)**: T008 depende só de T002 (paralelizável com US1/US2); T009 depende de T005, T007 e T008 (roda por último entre as histórias)
- **Polish (Phase 6)**: T010 depende de T009; T011 depende de T009 (paralelizável com T010, arquivos/hosts diferentes)

### Parallel Opportunities

- T003 [US1] e T006 [US2] e T008 [US3] podem ser escritos em paralelo por pessoas diferentes logo após T002 (todos tocam o mesmo arquivo `test_devices.py`, mas em funções de teste distintas — coordenar merge se paralelizado por múltiplos devs)
- T004 e T007 são sequenciais entre si (mesma função `default_microphone()` no mesmo arquivo `devices.py`) — não paralelizáveis

---

## Parallel Example: Foundational → User Stories

```bash
# Após T002 (fixture pronta), escrever os três testes em paralelo:
Task: "T003 [US1] Escrever test_default_microphone_resolves_wasapi_default em tests/test_devices.py"
Task: "T006 [US2] Escrever test_default_microphone_raises_without_wasapi_default em tests/test_devices.py"
Task: "T008 [US3] Escrever test_default_loopback_unaffected em tests/test_devices.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 1: Setup (T001)
2. Completar Phase 2: Foundational (T002) — bloqueia tudo
3. Completar Phase 3: User Story 1 (T003-T005)
4. **PARAR e VALIDAR**: `default_microphone()` já resolve corretamente via WASAPI no caso feliz — é o MVP que fecha a causa raiz principal da issue #27
5. Seguir para US2 (fail-fast explícito) e US3 (rede de segurança de teste) antes de considerar a issue fechável, já que FR-003/FR-005 da spec exigem ambas

### Incremental Delivery

1. Setup + Foundational → base pronta (T001-T002)
2. US1 → testar independentemente → resolve o bug principal (T003-T005)
3. US2 → testar independentemente → fecha o caso de borda sem fallback silencioso (T006-T007)
4. US3 → suíte completa verde, sem regressão em `default_loopback()` (T008-T009)
5. Polish → validação manual Windows real (T010) + confirmação do contrato `transcript-event.v2` em `services/transcription-service` (T011), critérios de saída da feature

---

## Notes

- [P] = arquivos/funções diferentes ou testes independentes dentro do mesmo arquivo, sem dependência de tarefa incompleta
- [Story] mapeia cada tarefa para a user story correspondente em `spec.md`, para rastreabilidade
- Escrever os testes antes da implementação de cada história e confirmar que falham contra o código atual, antes de implementar a correção correspondente
- T004 e T007 alteram a mesma função (`default_microphone()`) — não devem ser paralelizados nem divididos entre pessoas diferentes sem coordenação
- T010 (validação manual Windows) é o único critério de saída que depende de hardware real; todo o resto roda no WSL com fakes (P10)
