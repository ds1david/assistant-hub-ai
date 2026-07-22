# Implementation Plan: Captura de áudio por processo (WASAPI loopback por app)

**Branch**: `009-sf-020-process-capture` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/009-sf-020-process-capture/spec.md`

## Summary

Permitir que um canal do agente de áudio capture, via WASAPI loopback, o áudio de um processo/aplicativo
específico (por PID ou nome) em vez de um dispositivo físico inteiro — isolado por canal (ADR-0007), sem
quebrar `endpointId` (SF-018), hot-plug (SF-019) nem o contrato `transcript-event.v2`. Tecnicamente,
requer declarar manualmente (via `comtypes`, sem SDK de terceiros novo) a API Windows
`ActivateAudioInterfaceAsync`/`AUDIOCLIENT_ACTIVATION_PARAMS` — mesmo padrão arquitetural já validado em
SF-019 para `IMMNotificationClient` — num caminho de captura totalmente separado de
`PyAudioWPatch`/PortAudio, já que essa API não tem equivalente ali. Resolução de processo por PID/nome
usa `psutil` (mesma biblioteca já usada transitivamente por `pycaw`, sem escolha de pacote novo — mas
promovida a dependência direta e sem marcador de plataforma em `pyproject.toml`, já que `pycaw` só
instala em `win32` e `process_resolver.py` precisa ser testável em WSL; research.md §3). Nenhuma mudança
de contrato é necessária (research.md §5): metadados de processo cabem nos campos já existentes e
anuláveis de `device`.

## Technical Context

**Language/Version**: Python 3.11+ (mesmo runtime de `agents/windows-audio-agent`, `pyproject.toml: requires-python = ">=3.11"`) — inalterado.

**Primary Dependencies**: `comtypes` (já transitivo via `pycaw`, win32-only) para declarar manualmente `ActivateAudioInterfaceAsync`/`AUDIOCLIENT_ACTIVATION_PARAMS`/`IActivateAudioInterfaceCompletionHandler` (research.md §1) — sem mudança de declaração em `pyproject.toml`, permanece transitivo/win32-only. `psutil` para resolução de processo por PID/nome e checagem de usuário (research.md §3) — mesma biblioteca já usada por `pycaw`, mas precisa passar a ser declarada como dependência direta e sem marcador de plataforma em `pyproject.toml` (Setup/T001), já que `process_resolver.py` é multiplataforma e testado em WSL, onde `pycaw` (win32-only) não instala hoje.

**Storage**: N/A (estado apenas em memória, por processo worker).

**Testing**: `pytest` (suíte existente). A resolução de processo (PID/nome/usuário, `psutil`) é testável em WSL/Linux com processos reais do próprio processo de teste (`psutil` é multiplataforma) ou fakes. A captura COM real (`ActivateAudioInterfaceAsync`) segue o mesmo padrão de import lazy Windows-only de `mmdevice_notifications.py` — não testável em WSL (P10), só via revalidação manual Windows (US3/FR-009).

**Target Platform**: Windows nativo (captura real via COM) para produção; WSL/Linux para desenvolvimento e testes automatizados (degrade explícito, sem tentar COM real).

**Project Type**: CLI/agent existente (`assistant-hub-audio`) — nova capacidade de captura dentro do worker de canal já existente, sem nova aplicação/serviço.

**Performance Goals**: Nenhum alvo novo além dos já implícitos em captura de áudio em tempo real (mesma cadência de chunk/latência já usada pelos canais por dispositivo); sem requisito de throughput adicional.

**Constraints**: Requer Windows 10 build 20348+ para `PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE` (research.md §1) — versão mínima mais recente que a já exigida por SF-018/SF-019; sem fallback silencioso na seleção de processo (P7/FR-004); restrição de processo à mesma sessão/usuário do operador (FR-011); testes automatizados 100% sem hardware/COM real (P10) — a prova end-to-end da captura por processo só é possível via revalidação manual Windows (US3).

**Scale/Scope**: 1 módulo novo Windows-only (`process_capture.py`, análogo a `mmdevice_notifications.py`) + extensão de `profiles.py` (`DeviceSelector` com `process_id`/`process_name`) + extensão do worker de canal (`capture.py`) para ramificar entre o caminho PyAudioWPatch (dispositivo) e o novo caminho COM (processo). Nenhuma mudança em `contracts/` (research.md §5).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Como esta feature cumpre |
|---|---|---|
| P1 — Spec antes de código | PASS | `spec.md` passou por `/speckit-clarify` (gate G1) antes deste plano; nenhum código foi alterado antes da spec existir. |
| P2 — Core independente de fornecedores | PASS | `ActivateAudioInterfaceAsync` é declarado manualmente via `comtypes` (mesmo padrão de SF-019), sem SDK de terceiros novo (research.md §1, alternativa rejeitada); nenhum código de domínio importa `comtypes`/`psutil` diretamente fora dos módulos de infraestrutura Windows. |
| P3 — WSL-first | PASS | O novo módulo de captura por processo é Windows-only, import lazy, mesmo padrão de `mmdevice_notifications.py`; a resolução de processo (`psutil`) é testável em WSL; a captura COM real não é (documentado, P10). |
| P4 — Contratos versionados | PASS | Nenhuma mudança em `contracts/transcript-event.v2.schema.json` — metadados de processo cabem nos campos já existentes e anuláveis de `device` (research.md §5, `contracts/README.md`). |
| P5 — Separação por canal e origem | PASS | Cada canal por processo mantém seu próprio `channelId`/`sourceType`/`device` isolado, mesmo padrão de canais por dispositivo. |
| P6 — Isolamento de endpoint de áudio | PASS | Um processo de worker isolado por canal continua valendo (ADR-0007) — o "endpoint" de um canal por processo é o PID/nome resolvido, mas a isolação por subprocesso não muda. |
| P7 — Identidade de dispositivo | PASS | FR-004/FR-005/FR-011: sem fallback silencioso na seleção de processo, ambiguidade e escopo de usuário sempre falham explicitamente. |
| P8 — Automação com autorização | N/A | Sem automação de Git/CI nova. |
| P9 — Privacidade | PASS | FR-011 (Clarifications) restringe a captura à mesma sessão/usuário do operador — não é possível alvejar processos de sistema ou de outro usuário. |
| P10 — Qualidade determinística | PASS | Resolução de processo testável sem hardware; captura COM real exige revalidação manual documentada em `docs/validation/` antes do gate G3 (US3/FR-009). |

Nenhuma violação a justificar — tabela de Complexity Tracking permanece vazia.

## Project Structure

### Documentation (this feature)

```text
specs/009-sf-020-process-capture/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command) — README only, sem mudança de schema
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
agents/windows-audio-agent/
├── src/assistant_hub_audio/
│   ├── profiles.py              # MODIFICADO — DeviceSelector ganha process_id/process_name
│   │                              (exclusivos entre si e com endpointId/index/nameRegex/default);
│   │                              _selector_from_dict/channel_to_dict atualizados (processId/
│   │                              processName no YAML)
│   ├── process_resolver.py       # NOVO — puro, sem comtypes: resolve PID/nome via psutil,
│   │                              checa mesmo usuário (FR-011), classifica ambiguidade/ausência
│   │                              (FR-005) e re-seguimento por nome (FR-012); testável em
│   │                              qualquer plataforma (psutil é multiplataforma)
│   ├── process_capture.py        # NOVO — Windows-only, import lazy: declaração manual de
│   │                              ActivateAudioInterfaceAsync/AUDIOCLIENT_ACTIVATION_PARAMS/
│   │                              IActivateAudioInterfaceCompletionHandler (comtypes, mesmo
│   │                              padrão de mmdevice_notifications.py); expõe um provider que
│   │                              entrega um IAudioClient escopado ao processo
│   └── capture.py                # MODIFICADO — capture_channel/_capture_once ramificam para o
│                                   caminho de processo (process_capture.py) quando
│                                   channel.selector.process_id/process_name está definido, em
│                                   vez do caminho PyAudioWPatch existente
└── tests/
    ├── test_process_resolver.py  # NOVO — resolução por PID/nome, ambiguidade, restrição de
    │                              usuário, re-seguimento por nome — sem hardware/COM (fakes de
    │                              psutil)
    └── test_capture_channel.py   # ESTENDIDO — canal por processo integrado ao mesmo laço de
                                    capture_channel (fail-fast vs. transitório, FR-004..FR-006)

docs/validation/
└── sf-020-windows.md             # NOVO — validação manual da captura COM real por processo
                                    (US3/FR-009), mesmo padrão de sf-018-windows.md/sf-019-windows.md
```

**Structure Decision**: projeto único existente (`agents/windows-audio-agent`). Novo módulo puro
(`process_resolver.py`, testável em qualquer plataforma) separado do novo módulo Windows-only
(`process_capture.py`, import lazy) — mesma separação já validada em `endpoints.py`/`mmdevice.py`
(SF-018) e `hotplug.py`/`mmdevice_notifications.py` (SF-019). `capture.py` ganha uma ramificação no
worker de canal (dispositivo vs. processo), não uma reescrita — o laço de retry/backoff/fail-fast já
existente é reaproveitado, só a origem do áudio muda.

## Complexity Tracking

Nenhuma violação da Constitution Check acima requer justificativa; tabela intencionalmente vazia.
