# Implementation Plan: Correção do provider real de notificação MMDevice (Issue #20)

**Branch**: `009-issue-20-mmdevice-notification-fix` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/009-issue-20-mmdevice-notification-fix/spec.md`

## Summary

Corrigir a quebra do provider real de notificação MMDevice (`HotplugListener.__init__` derrubando o
worker com `ModuleNotFoundError: comtypes.gen.MMDeviceAPILib`, issue #20/SF-019): `IMMNotificationClient`
deixa de depender de geração de typelib em runtime (`comtypes.client.GetModule`) e passa a ser definido
estaticamente (IID fixo do SDK + `comtypes.STDMETHOD`) em `mmdevice_notifications.py`. Falha de
`subscribe(...)` degrada de forma permanente e local (log de warning, sem retry, sem sinalização
cross-processo — Clarifications 2026-07-22), mesma filosofia já usada em `get_notification_provider`.
A correção já está aplicada na árvore de trabalho; este plano cobre o fechamento formal do ciclo
(P1/gate G2) e a revalidação manual em Windows real pendente (FR-005/SC-004).

## Technical Context

**Language/Version**: Python 3.11+ (mesmo runtime de `agents/windows-audio-agent`, `pyproject.toml: requires-python = ">=3.11"`) — inalterado por esta correção.

**Primary Dependencies**: `pycaw>=20240210` (win32-only) e seu `comtypes` transitivo — já dependências existentes de `specs/006-sf-019-hotplug-listener/`. Nenhuma dependência nova (FR-006); a correção troca *como* `IMMNotificationClient` é obtido (declaração manual via `comtypes.STDMETHOD`/`GUID`) em vez de gerado via `comtypes.client.GetModule`.

**Storage**: N/A (estado apenas em memória, por processo worker — inalterado)

**Testing**: `pytest` (suíte existente em `agents/windows-audio-agent/tests/`), incluindo o teste de regressão já presente `test_hotplug.py::test_listener_subscribe_failure_degrades_without_raising` (FR-004) via `FakeNotificationProvider`. Suíte WSL/Linux: `pytest -k "hotplug or capture"` → 30 passed; suíte completa → 60 passed (baseline pós-correção, `docs/validation/sf-019-windows.md`).

**Target Platform**: Windows nativo (provider real, via COM) para produção; WSL/Linux para desenvolvimento e CI (degrade para `NullNotificationProvider`/`FakeNotificationProvider`, sem `comtypes`/COM real carregado — P10).

**Project Type**: CLI/agent existente (`assistant-hub-audio`) — correção pontual em módulos já existentes de `specs/006-sf-019-hotplug-listener/`, sem nova aplicação/serviço.

**Performance Goals**: Nenhum alvo novo; a correção não altera a latência de detecção (limitada pelo chunk de leitura ~64ms a 16kHz/1024 frames, já especificado em SF-019) nem o debounce (`_DEBOUNCE_SECONDS`).

**Constraints**: Sem IPC novo entre supervisor e workers; sem fallback silencioso de endpoint (P7); testes automatizados 100% sem hardware/COM real (P10) — a validação da definição manual do IID/COM só é possível via revalidação manual em Windows real (FR-005); degrade de falha de assinatura é permanente por processo do canal, sem retry, e visível apenas em log local (Clarifications 2026-07-22, sem sinalização cross-processo).

**Scale/Scope**: Correção localizada em 2 arquivos existentes (`mmdevice_notifications.py`, `hotplug.py`) + 1 arquivo de teste (`test_hotplug.py`); nenhum módulo novo, nenhuma mudança de escala.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Como esta correção cumpre |
|---|---|---|
| P1 — Spec antes de código | PASS | `spec.md` (retroativa, ver Assumptions) passou por `/speckit-clarify` (gate G1) antes deste plano; formaliza um código já diagnosticado sem redesenhar a feature. |
| P2 — Core independente de fornecedores | PASS | `IMMNotificationClient` continua declarado só em `mmdevice_notifications.py` (Windows-only, import lazy); nenhum código de domínio passa a importar `comtypes`/`pycaw` diretamente. |
| P3 — WSL-first | PASS | A correção não altera o padrão de import lazy Windows-only; suíte automatizada continua 100% executável em WSL via `Null`/`FakeNotificationProvider`. |
| P4 — Contratos versionados | N/A | Nenhum schema de evento ou contrato é criado/alterado. |
| P5 — Separação por canal e origem | PASS | Inalterado — um `HotplugListener` por worker/canal, sem mistura entre canais. |
| P6 — Isolamento de endpoint de áudio | PASS | FR-002/FR-003: falha de assinatura degrada só o listener daquele processo de canal; nenhum canal derruba outro nem o supervisor. |
| P7 — Identidade de dispositivo | PASS | Sem alteração em resolução/fallback de `endpointId`. |
| P8 — Automação com autorização | N/A | Sem automação de Git/CI nova. |
| P9 — Privacidade | PASS | Nenhum dado novo sensível é logado; o log de degrade (FR-002) registra apenas a exceção técnica, sem áudio/segredos. |
| P10 — Qualidade determinística | PASS | FR-004 mantém cobertura 100% sem hardware; FR-005/SC-004 exigem revalidação manual documentada em `docs/validation/sf-019-windows.md` antes do gate G3. |

Nenhuma violação a justificar — tabela de Complexity Tracking permanece vazia.

## Project Structure

### Documentation (this feature)

```text
specs/009-issue-20-mmdevice-notification-fix/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command) — N/A, ver nota abaixo
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

Sem `contracts/` e sem `data-model.md` com entidades: esta correção não introduz nem altera nenhuma
interface externa (API, schema de evento, CLI nova) nem entidade de domínio — é uma correção pontual de
inicialização/assinatura COM interna ao worker já existente (mesma decisão de SF-019 original).
`data-model.md` é gerado como um registro mínimo apontando para essa ausência, para manter o layout
padrão de artefatos da feature.

### Source Code (repository root)

```text
agents/windows-audio-agent/
├── src/assistant_hub_audio/
│   ├── hotplug.py                  # MODIFICADO — HotplugListener.__init__: try/except em
│   │                                 # provider.subscribe(...) já ajustado (FR-002/FR-003)
│   ├── mmdevice_notifications.py   # MODIFICADO — IMMNotificationClient definido estaticamente
│   │                                 # via comtypes.GUID/STDMETHOD (FR-001), sem GetModule/gen
│   └── capture.py, endpoints.py, mmdevice.py, devices.py, profiles.py, main.py  # inalterados
└── tests/
    └── test_hotplug.py             # ESTENDIDO — test_listener_subscribe_failure_degrades_without_raising
                                       # (FR-004, já presente)

docs/validation/
└── sf-019-windows.md               # ATUALIZADO — revalidação manual Windows real (FR-005/SC-004)
```

**Structure Decision**: projeto único existente (`agents/windows-audio-agent`), mesma estrutura de
`specs/006-sf-019-hotplug-listener/`. Nenhum arquivo novo é criado — a correção altera apenas os dois
módulos que a issue #20 aponta como causa raiz, mantendo a separação já validada `hotplug.py` (puro,
testável, sem `comtypes`/`pycaw`) / `mmdevice_notifications.py` (Windows-only, import lazy).

## Complexity Tracking

Nenhuma violação da Constitution Check acima requer justificativa; tabela intencionalmente vazia.
