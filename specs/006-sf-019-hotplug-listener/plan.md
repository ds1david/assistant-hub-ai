# Implementation Plan: Listener de hot-plug nativo MMDevice (SF-019)

**Branch**: `feature/sf-019-sf-019-listener-de-hot-plug-nativo-mmdevice` | **Date**: 2026-07-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/006-sf-019-hotplug-listener/spec.md`

## Summary

Detectar chegada/remoção de endpoints WASAPI via notificação COM nativa (`IMMNotificationClient`),
em vez de depender do backoff genérico de reconexão. Cada worker de canal (subprocesso isolado,
ADR-0007) instancia seu próprio listener para o seu `endpointId` configurado: remoção interrompe a
captura imediatamente com erro distinto; chegada dispara re-resolução e retomada automática. Segue o
padrão já estabelecido em `endpoints.py`/`mmdevice.py` (Protocol + provider nulo + import lazy
Windows-only) para permanecer testável sem hardware (P10).

## Technical Context

**Language/Version**: Python 3.11+ (mesmo runtime de `agents/windows-audio-agent`, `pyproject.toml: requires-python = ">=3.11"`)

**Primary Dependencies**: `pycaw>=20240210` (já dependência `win32`-only) e seu `comtypes` transitivo, para implementar `IMMNotificationClient` sobre o mesmo `IMMDeviceEnumerator` já usado em `mmdevice.py`; `PyAudioWPatch` e `websockets` (já em uso em `capture.py`) permanecem inalterados; nenhuma dependência nova é adicionada ao `pyproject.toml`.

**Storage**: N/A (estado apenas em memória, por processo worker)

**Testing**: `pytest` (suíte existente em `agents/windows-audio-agent/tests/`), com um `FakeNotificationProvider` injetável — mesmo padrão de fakes já usado em `tests/test_endpoints.py` para `EndpointProvider`.

**Target Platform**: Windows nativo (listener real, via COM) para produção; WSL/Linux para desenvolvimento e CI (degrade para `NullNotificationProvider`, sem `comtypes`/COM carregado).

**Project Type**: CLI/agent existente (`assistant-hub-audio`), sem nova aplicação ou serviço — extensão do pacote `assistant_hub_audio` já publicado.

**Performance Goals**: detecção de remoção limitada pelo tamanho do chunk de leitura já em uso (~64ms a 16kHz/1024 frames), não pelo backoff de reconexão (hoje até 10s); não é um alvo de throughput.

**Constraints**: sem IPC novo entre supervisor (`run_agent`) e workers (decisão fechada em `/speckit.clarify`); sem fallback silencioso de endpoint (P7); testes 100% sem hardware/COM real (P10); sem breaking change em contratos v2 (P4) — esta feature não introduz nem altera schema de evento.

**Scale/Scope**: 1 módulo novo (listener + providers), alterações localizadas em `capture.py` (integração com o loop de reconexão existente); ordem de grandeza de canais por perfil é pequena (poucas unidades), sem impacto de escala.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Como esta feature cumpre |
|---|---|---|
| P1 — Spec antes de código | PASS | `spec.md` com critérios de aceite e fora de escopo já passou por `/speckit.clarify` (gate G1) antes deste plano. |
| P2 — Core independente de fornecedores | PASS | Listener fica atrás de um `Protocol` (`NotificationProvider`), com provider nulo por padrão; nenhum código de domínio importa `comtypes`/`pycaw` diretamente fora do módulo de infraestrutura Windows. |
| P3 — WSL-first | PASS | Import de `comtypes`/COM é lazy e Windows-only (mesmo padrão de `endpoints.get_endpoint_provider()`); toda a suíte automatizada roda em WSL/Linux via `NullNotificationProvider`/`FakeNotificationProvider`. |
| P4 — Contratos versionados | N/A | Nenhum schema de evento ou contrato é criado/alterado por esta feature. |
| P5 — Separação por canal e origem | PASS | Um `HotplugListener` por worker reage só ao `endpointId` do seu próprio canal (FR-004); nenhuma mistura entre canais. |
| P6 — Isolamento de endpoint de áudio | PASS | Listener instanciado dentro do subprocesso isolado do canal (decisão de clarify), nunca no supervisor; nenhuma instância COM/PyAudio compartilhada entre canais. |
| P7 — Identidade de dispositivo | PASS | Remoção/chegada nunca trocam de `endpointId`; falha de re-resolução após chegada cai no backoff genérico do mesmo endpoint, nunca em fallback para outro dispositivo. |
| P8 — Automação com autorização | N/A | Sem automação de Git/CI nova nesta feature. |
| P9 — Privacidade | PASS | Nenhum dado novo sensível é logado; nomes de dispositivo já são logados hoje em `_capture_once`. |
| P10 — Qualidade determinística | PASS | FR-007 exige testabilidade integral via fake, sem hardware; SC-006 exige validação manual Windows documentada em `docs/validation/sf-019-windows.md`. |

Nenhuma violação a justificar — tabela de Complexity Tracking permanece vazia.

## Project Structure

### Documentation (this feature)

```text
specs/006-sf-019-hotplug-listener/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

Sem `contracts/`: esta feature não expõe nem altera nenhuma interface externa (API, schema de
evento, CLI nova) — é puramente interna ao processo worker existente. O ponto de integração externo
já existente (evento de transcrição v2, query WebSocket) foi fechado em SF-018 e não é tocado aqui.

### Source Code (repository root)

```text
agents/windows-audio-agent/
├── src/assistant_hub_audio/
│   ├── endpoints.py        # EXISTENTE — lógica pura de correlação (inalterado)
│   ├── mmdevice.py          # EXISTENTE — provider Windows real de endpoints (inalterado)
│   ├── hotplug.py            # NOVO — HotplugEvent, NotificationProvider (Protocol),
│   │                          # NullNotificationProvider, get_notification_provider(),
│   │                          # HotplugListener (debounce + ChannelHotplugSignal)
│   ├── mmdevice_notifications.py  # NOVO — MMDeviceNotificationProvider (IMMNotificationClient
│   │                          # via comtypes), Windows-only, import lazy
│   ├── capture.py            # MODIFICADO — capture_channel/_capture_once passam a consultar o
│   │                          # ChannelHotplugSignal do HotplugListener além do stop_event
│   └── devices.py, profiles.py, main.py  # inalterados
└── tests/
    ├── test_hotplug.py       # NOVO — FakeNotificationProvider, debounce, filtragem por endpointId
    └── test_capture_channel.py  # ESTENDIDO — remoção/chegada integradas ao loop de captura
```

**Structure Decision**: projeto único existente (`agents/windows-audio-agent`), sem nova aplicação,
serviço ou diretório de topo. A separação `hotplug.py` (puro, testável) / `mmdevice_notifications.py`
(Windows-only, import lazy) espelha exatamente a separação já validada `endpoints.py` / `mmdevice.py`
de SF-018 — mesma convenção, sem abstração nova.

## Complexity Tracking

Nenhuma violação da Constitution Check acima requer justificativa; tabela intencionalmente vazia.
