# Tasks: SF-015 — Matriz manual de hardware R1

**Input**: Design documents from `/specs/005-sf-015-hardware-matrix/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Não solicitados na spec — esta feature é validação manual/documentação; a suíte automatizada existente (`agents/windows-audio-agent/tests`) é usada apenas como baseline de regressão, não como novo teste.

**Organização**: Tarefas agrupadas por cenário (user story), conforme spec.md. Cada cenário produz seu próprio arquivo de evidência e pode ser executado de forma independente, sem depender dos outros dois.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode ser feito em paralelo (arquivos/ambientes diferentes, sem dependência)
- **[Story]**: US1 = conference cam, US2 = Bluetooth+USB, US3 = microfone default + fechamento SF-018
- Caminhos de arquivo exatos em cada descrição

## Path Conventions

Projeto de documentação/validação — sem `src/`. Artefatos ficam em `docs/validation/` (evidência) e `specs/005-sf-015-hardware-matrix/` (spec kit).

---

## Phase 1: Setup

**Purpose**: Preparar os três arquivos de evidência a partir do template já validado na SF-018

- [X] T001 [P] Criar `docs/validation/sf-015-conference-cam.md` copiando o esqueleto de `docs/validation/sf-018-windows.md` (Ambiente, Dispositivos, Perfil, Casos, Segurança, Resultado), acrescentando as seções "Latência percebida" e "Frases de referência" (tabela, nos moldes de `docs/validation/r1-audio-validation.md`), e ajustar o título para "SF-015 — Conference cam"
- [X] T002 [P] Criar `docs/validation/sf-015-bluetooth-usb.md` com o mesmo esqueleto + seções "Latência percebida" e "Frases de referência", título "SF-015 — Bluetooth output + microfone USB"
- [X] T003 [P] Criar `docs/validation/sf-015-default-mic.md` com o mesmo esqueleto + seções "Latência percebida" e "Frases de referência", título "SF-015 — Microfone default"

**Checkpoint**: Os três arquivos existem como templates prontos para preenchimento.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Confirmar que a base da SF-018 está estável antes de rodar hardware novo

**⚠️ CRITICAL**: Nenhum cenário deve começar antes desta fase, para não gastar tempo de hardware sobre uma regressão de contrato já existente

- [X] T004 Rodar `PYTHONPATH=agents/windows-audio-agent/src pytest -q agents/windows-audio-agent/tests` no WSL como baseline de regressão dos contratos SF-016/017/018 antes da matriz manual — 36 passed em 2026-07-20
- [X] T005 [P] Confirmar `python -m pip install -e agents/windows-audio-agent` aplicado no Python **nativo do Windows** (nunca WSL — ADR-0003/ADR-0005), rodando `assistant-hub-audio --version` — achado: existe um venv oficial em `%LOCALAPPDATA%\AssistantHubAI\audio-agent-venv` gerenciado por `scripts/windows/run-audio-agent-foreground.ps1`; estava com `pycaw` desatualizado/ausente, corrigido com a flag `-Reinstall` do script

**Checkpoint**: Suíte automatizada verde e CLI instalada no Windows — pronto para os três cenários.

---

## Phase 3: User Story 1 - Conference cam (Priority: P1) 🎯 MVP

**Goal**: Provar que microfone e loopback da mesma conference cam preservam `endpointId`/`channelId`/`sourceType` e que a supressão de eco evita duplicação óbvia da fala remota.

**Independent Test**: Conectar apenas a conference cam, rodar os três comandos e preencher `sf-015-conference-cam.md` — não depende dos outros cenários.

### Implementation for User Story 1

- [X] T006 [US1] Rodar `assistant-hub-audio list-devices --json` (Windows) e registrar `endpointId`/friendly name do microfone e do render/loopback da conference cam em `docs/validation/sf-015-conference-cam.md`
- [X] T007 [US1] Criar perfil YAML com dois canais apontando os `endpointId` do passo anterior — feito como `samples/audio-profiles/conference-cam-endpointid.yaml` (schema real usa `kind: input`/`kind: loopback`, não `sourceType`; corrigido no quickstart.md)
- [X] T008 [US1] Confirmar resolução correta de ambos os canais por `endpointId` — validado implicitamente via `run` (ver T009); samples do repo (`nameRegex`/`default`) se mostraram ambíguos/incompletos nesta máquina
- [X] T009 [US1] Rodar `run --session sf015-conference-cam --profile samples/audio-profiles/conference-cam-endpointid.yaml` e confirmar que o evento v2 de cada canal preserva `endpointId`/`channelId`/`sourceType` — confirmado em 2026-07-20
- [X] T010 [US1] Falar frases de referência durante playback remoto simultâneo e registrar em `sf-015-conference-cam.md` se a supressão de eco evitou duplicação óbvia da fala remota no canal local (ADR-0008) — confirmado via sessão companheira `session-20260720-183342` (mesmo hardware): 8 supressões de eco corretas, similaridade 0.82-1.00, ver logs do `transcription-service`
- [X] T010a [US1] Registrar latência percebida entre fala e transcrição em `docs/validation/sf-015-conference-cam.md` (seção "Latência percebida") — medido objetivamente via `/v1/sessions/.../metrics`: p50=402ms, p95=450ms
- [X] T011 [US1] Preencher o campo `Resultado` (PASS/FAIL/BLOCKED) e `Limitações` em `docs/validation/sf-015-conference-cam.md`, garantindo que nenhum checkbox do template fique em branco — **Resultado: PASS**

**Checkpoint**: Cenário 1 tem resultado definitivo e é revisável isoladamente em PR.

---

## Phase 4: User Story 2 - Bluetooth output + microfone USB (Priority: P2)

**Goal**: Provar que dois dispositivos de tecnologias diferentes (Bluetooth + USB) não se confundem na correlação por `endpointId`, incluindo o caso de reconexão Bluetooth durante a sessão.

**Independent Test**: Parear apenas o dispositivo Bluetooth e conectar o microfone USB, rodar a mesma sequência de comandos e preencher `sf-015-bluetooth-usb.md` — independente do cenário 1.

### Implementation for User Story 2

- [X] T012 [US2] Rodar `assistant-hub-audio list-devices --json` e registrar `endpointId`/friendly name do dispositivo Bluetooth output e do microfone USB em `docs/validation/sf-015-bluetooth-usb.md`, observando nomes duplicados/genéricos — feito; nenhum dispositivo Bluetooth ou USB mic dedicado presente nesta máquina
- [X] T013 [US2] Criar perfil YAML com os dois canais (Bluetooth output como `system`/loopback se aplicável, microfone USB como `microphone`) apontando os `endpointId` correspondentes — usado o sample `samples/audio-profiles/bluetooth-output-usb-mic.yaml`; `nameRegex` não encontrou hardware compatível (ver Resultado)
- [ ] ~~T014 [US2] Rodar `probe` e `run --session sf015-bluetooth-usb --profile <perfil>`~~ — BLOCKED, sem hardware Bluetooth/USB disponível
- [ ] ~~T015 [US2] Provocar reconexão do dispositivo Bluetooth durante a sessão de captura~~ — BLOCKED, sem hardware
- [ ] ~~T015a [US2] Falar frase de referência em cada canal~~ — BLOCKED, sem hardware
- [X] T016 [US2] Preencher o campo `Resultado` e `Limitações` em `docs/validation/sf-015-bluetooth-usb.md` — Resultado: BLOCKED

**Checkpoint**: Cenário 2 tem resultado definitivo, independente do cenário 1.

---

## Phase 5: User Story 3 - Microfone default + fechamento retroativo da SF-018 (Priority: P1)

**Goal**: Provar a captura sem seleção explícita de dispositivo (microfone default) e, no mesmo ciclo, fechar a lacuna de evidência pendente em `docs/validation/sf-018-windows.md` reexecutando seus 7 casos.

**Independent Test**: Sem hardware adicional (usa o microfone default), roda `run` sem `--profile` apontando dispositivo específico e os 7 casos do template SF-018 — independente dos cenários 1 e 2.

### Implementation for User Story 3

- [X] T017 [US3] Rodar `assistant-hub-audio run --session sf015-default-mic` sem `--profile` de dispositivo específico e confirmar que o microfone default do Windows é capturado, com `endpointId`/`channelId`/`sourceType` presentes no evento v2; registrar em `docs/validation/sf-015-default-mic.md` — feito em 2026-07-20; achado: canal `local_microphone` não carrega `endpointId` (ver Limitações)
- [ ] T017a [US3] Falar frase de referência no microfone default e registrar transcrição + latência percebida em `docs/validation/sf-015-default-mic.md` — pendente (canal `local_microphone` sem `endpointId`; frase real ainda não coletada nesse canal específico)
- [X] T018 [US3] Executar o caso 1 (`list-devices`) do template em `docs/validation/sf-018-windows.md` e marcar seus checkboxes
- [X] T019 [US3] Executar o caso 2 (`probe` com `endpointId`) do template em `docs/validation/sf-018-windows.md` e marcar seus checkboxes
- [X] T020 [US3] Executar o caso 3 (`run` captura) do template em `docs/validation/sf-018-windows.md` e marcar seus checkboxes
- [ ] T021 [US3] Executar o caso 4 (reboot ou reenumeração) do template em `docs/validation/sf-018-windows.md`, registrando índice PortAudio antes/depois, e marcar seus checkboxes — pendente, requer reboot real
- [ ] T022 [US3] Executar o caso 5 (hot-plug parcial) do template em `docs/validation/sf-018-windows.md` e marcar seus checkboxes, deixando explícito que o listener completo é escopo da SF-019 — pendente, requer desconectar/reconectar ou desabilitar/reabilitar
- [X] T023 [US3] Executar o caso 6 (endpoint desabilitado/inexistente) do template em `docs/validation/sf-018-windows.md` e marcar seus checkboxes, confirmando mensagens distintas sem fallback silencioso — sub-item "ID desconhecido" confirmado; sub-item "desabilitado" segue pendente (requer Gerenciador de Dispositivos)
- [X] T024 [US3] Executar o caso 7 (Bluetooth/nomes duplicados, se aplicável) e a seção de Segurança do template em `docs/validation/sf-018-windows.md` e marcar seus checkboxes — achado: sem WARNING automático no código, mas erro de ambiguidade explícito confirmado (comportamento seguro)
- [X] T025 [US3] Preencher o campo `Resultado` (substituindo o placeholder `PASS | FAIL | BLOCKED`) em `docs/validation/sf-018-windows.md` com o resultado definitivo e evidências/limitações — **Resultado: PASS parcial**, com Casos 4/5/6b pendentes explicitados
- [ ] T026 [US3] Preencher o campo `Resultado` e `Limitações` em `docs/validation/sf-015-default-mic.md`

**Checkpoint**: Cenário 3 concluído e `docs/validation/sf-018-windows.md` deixa de ser template em branco — fecha o gap do checkpoint pós SF-018.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Consistência entre os quatro arquivos de evidência e encerramento do ciclo SDD

- [X] T027 [P] Revisar os quatro arquivos (`sf-015-conference-cam.md`, `sf-015-bluetooth-usb.md`, `sf-015-default-mic.md`, `sf-018-windows.md`) confirmando ausência de áudio bruto, segredos ou tokens (P9 da constituição; CHK016 do checklist evidence.md) — revisado, sem achados
- [X] T028 Confirmar que nenhum dos três cenários ficou com `Resultado` em branco ou placeholder; cenários BLOCKED têm limitação explicada (FR-008) — confirmado: US1=PASS, US2=BLOCKED (limitação explicada), US3=PASS parcial, SF-018=PASS parcial (limitações explicadas em ambos)
- [X] T029 Atualizar `specs/001-streaming-foundation/tasks.md` marcando a linha da SF-015 como `[x]`, no mesmo padrão usado para a SF-018 — feito, com nota de PASS parcial e follow-ups
- [ ] T030 Rodar `git add docs/validation/sf-015-*.md docs/validation/sf-018-windows.md specs/001-streaming-foundation/tasks.md` e commitar com mensagem `docs(validation): record R1 hardware matrix SF-015 and close SF-018 evidence gap`
- [ ] T031 Rodar `./scripts/wsl/spec-cycle.sh test --scope auto` (Gate G3) e depois `./scripts/wsl/spec-cycle.sh finalize 11 --draft` para abrir o PR draft

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: depende do Setup — bloqueia todos os cenários
- **Cenários (Phase 3-5)**: todos dependem da Foundational; podem ser executados em qualquer ordem entre si, mas a ordem sugerida é P1 (US1) → P2 (US2) → P1 (US3), pois US3 fecha o gap de checkpoint mais urgente
- **Polish (Phase 6)**: depende dos três cenários estarem concluídos

### Story Dependencies

- **US1 (conference cam)**: sem dependência de US2/US3
- **US2 (Bluetooth+USB)**: sem dependência de US1/US3
- **US3 (microfone default + SF-018)**: sem dependência de US1/US2 — pode inclusive ser feito primeiro, já que é o gate mais urgente do checkpoint pós SF-018

### Parallel Opportunities

- T001/T002/T003 (criação dos três templates) são independentes entre si — `[P]`
- T004 (pytest no WSL) e T005 (confirmar CLI no Windows) tocam ambientes diferentes — `[P]`
- Uma vez concluída a Fase 2, US1/US2/US3 podem ser executados em qualquer ordem — mas como todos usam o mesmo executor humano e podem compartilhar o mesmo bloco de tempo com hardware, a paralelização real depende de haver mais de uma pessoa/máquina disponível
- T027 é revisão cross-cutting e pode ser feita em paralelo a T029 (arquivos diferentes) — `[P]`

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Fase 1: Setup
2. Completar Fase 2: Foundational (bloqueia os três cenários)
3. Completar Fase 3: Cenário 1 (conference cam)
4. **PARAR e VALIDAR**: `sf-015-conference-cam.md` com resultado definitivo já é um incremento útil e revisável isoladamente

### Entrega incremental

1. Setup + Foundational → base pronta
2. Cenário 3 (US3) primeiro se a prioridade for fechar o gap de checkpoint da SF-018 o quanto antes — recomendado, apesar de aparecer como Fase 5 no documento
3. Cenário 1 (US1) → conference cam
4. Cenário 2 (US2) → Bluetooth + USB
5. Polish → commit único cobrindo os quatro arquivos de evidência + atualização do umbrella `tasks.md`

---

## Notes

- Nenhuma tarefa de código-fonte: todos os arquivos afetados são Markdown em `docs/validation/` e `specs/005-sf-015-hardware-matrix/` (mais uma linha em `specs/001-streaming-foundation/tasks.md`).
- Nenhum teste automatizado novo — T004 apenas reexecuta a suíte já existente como baseline, conforme constituição P10.
- Itens abertos do checklist `checklists/evidence.md` (CHK003, CHK013, CHK016) ainda não foram resolvidos no `spec.md` — considerar tratá-los no `/speckit.analyze` antes do `/speckit.implement`, ou aceitar como limitação documentada.
