# Implementation Plan: Correção de aridade do callback COM e de `notpresent` fatal (SF-019, Issue #22)

**Branch**: `010-sf-019-callback-notpresent-fix` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/010-sf-019-callback-notpresent-fix/spec.md`

## Summary

Dois bugs independentes revelados pela primeira validação manual Windows real de SF-019 (issue #22):
**(A)** os callbacks `IMMNotificationClient_On*` (`mmdevice_notifications.py`) levantam `TypeError` de
aridade porque a interface é declarada via `comtypes.STDMETHOD` (sem `paramflags`), e o comtypes sempre
invoca esses callbacks passando o ponteiro `this` como argumento extra — confirmado lendo o código-fonte
do `comtypes` (`_vtbl.py::hack()`) e seu próprio teste oficial (`test_comobject.py`). Fix: aceitar `this`
explicitamente como segundo parâmetro em cada método, sem usá-lo. **(B)** sem o evento de remoção
chegando (efeito do Bug A), o unplug físico aparece como uma falha comum de `resolve_device` com estado
`notpresent`, hoje tratada com a mesma política fatal/permanente reservada a erro de configuração — fix:
rastrear se o canal já resolveu com sucesso ao menos uma vez (`resolved_at_least_once`) e, nesse caso,
tratar a falha como transitória (mesmo caminho de retry de `EndpointRemovedError`), preservando o
fail-fast de SF-018 para um `endpointId` nunca resolvido.

## Technical Context

**Language/Version**: Python 3.11+ (mesmo runtime de `agents/windows-audio-agent`, `pyproject.toml: requires-python = ">=3.11"`) — inalterado.

**Primary Dependencies**: `comtypes` (transitivo de `pycaw`, win32-only) — nenhuma dependência nova. A correção não troca `STDMETHOD` por `COMMETHOD` (ver research.md §1, alternativa rejeitada) — mantém a declaração manual da interface já decidida em `specs/009-issue-20-mmdevice-notification-fix/`.

**Storage**: N/A (estado apenas em memória, por processo worker; `resolved_at_least_once` é uma flag local ao laço de `capture_channel`, não persistida)

**Testing**: `pytest` (suíte existente em `agents/windows-audio-agent/tests/`). Bug A é testável em WSL simulando a convenção de chamada real do comtypes (invocar o método bound com um `this` de posição, ex. `None`/sentinel, mais os argumentos declarados) sem precisar de COM real. Bug B é testável em WSL com um `resolve_device` fake que falha após uma resolução prévia bem-sucedida, e outro fake que nunca resolve (fail-fast).

**Target Platform**: Windows nativo (provider real, via COM) para produção; WSL/Linux para desenvolvimento e CI (P10 — sem hardware/COM real na suíte automatizada).

**Project Type**: CLI/agent existente (`assistant-hub-audio`) — correção pontual em módulos já existentes de `specs/006-sf-019-hotplug-listener/`/`specs/009-issue-20-mmdevice-notification-fix/`, sem nova aplicação/serviço.

**Performance Goals**: Nenhum alvo novo; não altera debounce nem latência de detecção já especificados em SF-019.

**Constraints**: Sem IPC novo; sem fallback silencioso de endpoint (P7 — FR-005 preserva fail-fast de SF-018); testes automatizados 100% sem hardware/COM real (P10) — a prova end-to-end dos Bugs A/B só é possível via revalidação manual Windows (FR-007); `resolved_at_least_once` é estado interno ao processo do canal, sem sinalização cross-processo (mesmo padrão de escopo já usado em `specs/009-.../Clarifications`).

**Scale/Scope**: Correção localizada em 2 arquivos existentes (`mmdevice_notifications.py` para Bug A, `capture.py` para Bug B) + testes; nenhum módulo novo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Como esta correção cumpre |
|---|---|---|
| P1 — Spec antes de código | PASS | `spec.md` escrita e validada (checklist 16/16) antes de qualquer alteração de código para os Bugs A/B — ordem normal, sem necessidade de aprovação retroativa (diferente de `specs/009-.../`). |
| P2 — Core independente de fornecedores | PASS | `IMMNotificationClient`/`comtypes` continuam isolados em `mmdevice_notifications.py` (Windows-only, import lazy); `resolved_at_least_once` é lógica pura em `capture.py`, sem import de provedor. |
| P3 — WSL-first | PASS | Bug A e Bug B são ambos testáveis em WSL sem COM/hardware real (research.md §1, §3); import de `comtypes` continua lazy e Windows-only. |
| P4 — Contratos versionados | N/A | Nenhum schema de evento ou contrato é criado/alterado (FR-008 preserva `transcript-event.v2`). |
| P5 — Separação por canal e origem | PASS | `resolved_at_least_once` é estado local ao laço de `capture_channel` de um único canal; nenhuma mistura entre canais. |
| P6 — Isolamento de endpoint de áudio | PASS | Ambas as correções continuam dentro do processo isolado do canal; nenhuma delas introduz estado compartilhado entre canais/supervisor. |
| P7 — Identidade de dispositivo | PASS | FR-004/FR-005: a distinção "já resolveu antes" vs. "nunca resolveu" preserva o fail-fast de SF-018 sem introduzir fallback para outro dispositivo. |
| P8 — Automação com autorização | N/A | Sem automação de Git/CI nova. |
| P9 — Privacidade | PASS | Nenhum dado novo sensível é logado; os logs de callback/degrade (FR-002) registram apenas exceção técnica e `endpointId`, já expostos hoje. |
| P10 — Qualidade determinística | PASS | FR-006 exige testes 100% sem hardware; FR-007 exige revalidação manual documentada em `docs/validation/sf-019-windows.md` antes do gate G3. |

Nenhuma violação a justificar — tabela de Complexity Tracking permanece vazia.

## Project Structure

### Documentation (this feature)

```text
specs/010-sf-019-callback-notpresent-fix/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command) — N/A, ver nota abaixo
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

Sem `contracts/` e sem `data-model.md` com entidades: ambos os bugs são correções pontuais de
comportamento interno ao worker (convenção de chamada de callback COM; classificação de uma exceção já
existente) — nenhuma interface externa (API, schema de evento, CLI nova) é criada ou alterada.

### Source Code (repository root)

```text
agents/windows-audio-agent/
├── src/assistant_hub_audio/
│   ├── mmdevice_notifications.py   # MODIFICADO — Bug A: `this` explícito em
│   │                                 # IMMNotificationClient_On{DeviceStateChanged,DeviceAdded,
│   │                                 # DeviceRemoved,DefaultDeviceChanged,PropertyValueChanged};
│   │                                 # try/except por callback (FR-001/FR-002)
│   ├── capture.py                  # MODIFICADO — Bug B: flag `resolved_at_least_once` em
│   │                                 # capture_channel; EndpointResolutionError após resolução
│   │                                 # prévia tratada como transitória (FR-004/FR-005)
│   └── hotplug.py, endpoints.py, mmdevice.py, devices.py, profiles.py, main.py  # inalterados
└── tests/
    ├── test_mmdevice_notifications.py  # NOVO (ou test_hotplug.py, se preferir manter num só
    │                                     # arquivo) — simula a convenção real de chamada do
    │                                     # comtypes (this + args) para os 5 callbacks (FR-006)
    └── test_capture_channel.py     # ESTENDIDO — notpresent após resolução prévia → espera;
                                       # arrival → resume; endpointId nunca resolvido → fatal (FR-006)

docs/validation/
└── sf-019-windows.md               # ATUALIZADO — revalidação manual Windows real (FR-007/SC-005)
```

**Structure Decision**: projeto único existente (`agents/windows-audio-agent`), mesma estrutura de
`specs/006-sf-019-hotplug-listener/`/`specs/009-issue-20-mmdevice-notification-fix/`. Nenhum arquivo
novo de produção é criado — apenas os dois módulos que a issue #22 aponta como causa raiz (mais um
arquivo de teste novo, opcional, dedicado ao Bug A).

## Complexity Tracking

Nenhuma violação da Constitution Check acima requer justificativa; tabela intencionalmente vazia.
