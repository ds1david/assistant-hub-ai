# Implementation Plan: Tornar `default_microphone()` WASAPI-aware (Issue #27)

**Branch**: `011-default-mic-wasapi-aware` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-default-mic-wasapi-aware/spec.md`

## Summary

`default_microphone()` (`agents/windows-audio-agent/src/assistant_hub_audio/devices.py:72-73`) hoje resolve o microfone default via `pyaudio.get_default_input_device_info()`, o default global do PortAudio, agnóstico de host API. Isso pode devolver um dispositivo MME/DirectSound/WDM-KS em vez do default WASAPI, e como `correlate_devices()` só correlaciona dispositivos WASAPI (ADR-0011), o canal de microfone `default: true` fica sem `endpointId` — bug já reproduzido 2x em `docs/validation/sf-015-default-mic.md`. A correção espelha o padrão já correto de `default_loopback()` (linhas 76-86): consultar `get_host_api_info_by_type(pyaudio.paWASAPI)` e resolver o `defaultInputDevice` dentro desse host API, com erro explícito (sem fallback silencioso) quando não houver default WASAPI de entrada. Acompanha testes de regressão novos em `tests/test_devices.py` (hoje inexistente) e validação manual Windows repetindo o cenário já documentado na SF-015.

## Technical Context

**Language/Version**: Python 3.11+ (`agents/windows-audio-agent/pyproject.toml`: `requires-python = ">=3.11"`)

**Primary Dependencies**: `PyAudioWPatch` (PortAudio + extensões WASAPI loopback/host-API), `pycaw` (MMDevice/Core Audio, usado por `endpoints.py` para a correlação já existente); nenhuma dependência nova

**Storage**: N/A — nenhuma persistência envolvida, apenas resolução de dispositivo em memória por execução

**Testing**: `pytest`, executado no WSL com objetos fake de `pyaudio.PyAudio` (mesmo padrão de `_FakePyAudioModule`/`_FakeAudio` já usado em `tests/test_capture_channel.py`); sem hardware real em CI (P10)

**Target Platform**: processo nativo Windows (`assistant-hub-audio` CLI/agent) para execução real; testes automatizados rodam no WSL com fakes (ADR-0005), validação manual final em host Windows real

**Project Type**: single project — biblioteca/agente CLI existente (`agents/windows-audio-agent`); nenhuma estrutura nova

**Performance Goals**: N/A — resolução de dispositivo ocorre uma vez por canal por start/reload, não é caminho sensível a throughput

**Constraints**: sem fallback silencioso para host API não-WASAPI quando `default: true` é o seletor de microfone (P7); testes automatizados não podem depender de hardware Windows real (P10); comportamento de `default_loopback()` e do contrato `transcript-event.v2` não pode mudar (FR-004/FR-006 da spec)

**Scale/Scope**: correção pontual de uma função (`default_microphone()`) + testes de regressão novos; nenhuma mudança de schema, contrato ou módulo novo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Aplicação nesta feature | Status |
|-----------|--------------------------|--------|
| P1 — Spec antes de código | `specs/011-default-mic-wasapi-aware/spec.md` aprovado antes deste plano | PASS |
| P2 — Core independente de fornecedores | Nenhuma dependência de provedor STT/LLM tocada; apenas captura de áudio local via PyAudioWPatch/pycaw já usados | PASS (N/A) |
| P3 — WSL-first | Fix e testes automatizados no WSL com fakes; validação real em Windows nativo, sem venv compartilhada | PASS |
| P5 — Separação por canal e origem | `endpointId` é exatamente o metadado de dispositivo que esta correção passa a propagar corretamente ponta a ponta (agente → evento `transcript-event.v2`) para o canal de microfone default; nenhum campo `channelId`/`sourceType` é alterado | PASS (objetivo direto da feature) |
| P6 — Isolamento de endpoint | Nenhuma mudança no modelo de um processo por endpoint WASAPI; resolução de dispositivo permanece por canal | PASS (N/A) |
| P7 — Identidade de dispositivo | É o princípio que esta feature corrige: `default_microphone()` passa a respeitar o host API WASAPI, e FR-003 exige erro explícito em vez de fallback silencioso quando não há default WASAPI de entrada | PASS (objetivo direto da feature) |
| P9 — Privacidade | Nenhum log novo expõe áudio bruto/segredos; apenas metadados de dispositivo já logados hoje | PASS |
| P10 — Qualidade determinística | Testes novos usam fakes (sem hardware); validação manual real documentada em `docs/validation/` (FR-007) | PASS |

Nenhuma violação identificada. Seção "Complexity Tracking" não se aplica.

**Re-check pós Fase 1 (design)**: `research.md` e `data-model.md` confirmam que nenhuma entidade nova, dependência nova ou mudança de contrato externo foi introduzida — a correção permanece contida em `devices.py` mais o novo `tests/test_devices.py`, sem contradizer nenhuma das linhas do gate acima. PASS mantido, sem necessidade de nova entrada em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/011-default-mic-wasapi-aware/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

Sem `contracts/`: a correção não expõe nem altera nenhuma interface externa (CLI flags, schema de evento, API) — `default_microphone()` mantém a mesma assinatura (`audio: pyaudio.PyAudio) -> dict[str, Any]`) e o mesmo formato de retorno já normalizado por `_normalized_device`/`_endpoint_fields`. O único contrato observável (`transcript-event.v2`) já existe e não muda (FR-006); o efeito da correção é que um campo já presente no schema (`endpointId`) passa a ser preenchido em vez de `None` para esse caminho específico.

### Source Code (repository root)

```text
agents/windows-audio-agent/
├── src/assistant_hub_audio/
│   ├── devices.py        # ALTERADO: default_microphone() passa a resolver via WASAPI host API,
│   │                      # espelhando o padrão já existente em default_loopback() (linhas 76-86);
│   │                      # levanta erro explícito quando não há defaultInputDevice WASAPI válido
│   ├── endpoints.py       # NÃO ALTERADO: correlate_devices()/find_device_for_endpoint() já filtram
│   │                      # por host API WASAPI (comportamento de referência, não muda)
│   └── profiles.py        # NÃO ALTERADO: AudioChannel/DeviceSelector (default: true → use_default)
└── tests/
    ├── test_devices.py    # NOVO: cobertura de regressão para default_microphone()
    │                      # (resolução correta via WASAPI + erro explícito sem default WASAPI)
    └── test_endpoints.py  # NÃO ALTERADO: referência de padrão de fakes para correlação WASAPI
```

**Structure Decision**: projeto único existente (`agents/windows-audio-agent`), sem novos módulos ou diretórios. A correção fica inteiramente contida em `devices.py`; a única adição estrutural é o arquivo de teste `tests/test_devices.py`, hoje inexistente (gap de cobertura confirmado na investigação da issue).

## Complexity Tracking

*Não aplicável — nenhuma violação de constituição identificada no Constitution Check.*
