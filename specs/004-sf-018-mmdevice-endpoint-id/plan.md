# Implementation Plan: Identidade persistente de dispositivos via MMDevice endpoint ID (SF-018)

**Branch**: `feature/sf-018-sf-018-identidade-persistente-de-dispositivos-co` | **Date**: 2026-07-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-sf-018-mmdevice-endpoint-id/spec.md`

**Nota**: Plano de formalização retrospectiva — a implementação piloto já existe no código. Este documento descreve a arquitetura adotada para que os gates G2 (Plan/Analyze) e G3 (Validate) sejam avaliados sobre uma base explícita.

## Summary

Canais de áudio passam a ser resolvidos pelo MMDevice endpoint ID do Windows (identidade estável) em vez de depender do índice PortAudio (volátil após reboot, hot-plug, Bluetooth e atualização de driver). A abordagem: um provider MMDevice exclusivo do Windows enumera endpoints, uma camada pura de correlação casa endpoint ↔ dispositivo PortAudio (fluxo WASAPI, FriendlyName, ordem de enumeração), e o seletor de perfil `device.endpointId` resolve o índice atual no início de cada captura — com prioridade sobre `index` e `default`/`nameRegex`, falha explícita sem fallback, e propagação aditiva do `endpointId` no WebSocket de áudio e no evento `transcript-event.v2`.

### Fluxo de resolução

```
Profile YAML (endpointId)
        │
        ▼
profiles.DeviceSelector ──► devices.resolve_device
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              endpointId     index      default/regex
                    │
                    ▼
         endpoints.find_device_for_endpoint
                    │
         correlate_devices(PortAudio, MMDevice)
                    │
         mmdevice.MMDeviceEndpointProvider (Windows)
         NullEndpointProvider (Linux/CI)
                    │
                    ▼
         capture WebSocket query + transcript-event.v2.device.endpointId
```

## Technical Context

**Language/Version**: Python >= 3.11 (agente Windows, executado com Python nativo do Windows); serviço de transcrição em Python no WSL

**Primary Dependencies**: PyAudioWPatch (enumeração/captura WASAPI), `pycaw`/`comtypes` (MMDevice — restrito a `sys_platform == 'win32'`, import tardio), PyYAML (perfis), websockets (feed de áudio)

**Storage**: N/A (perfis em YAML; nenhum estado persistente novo)

**Testing**: pytest com fakes de provider e de enumeração PortAudio (Linux/CI, sem hardware); smoke de import/CLI no Windows; validação manual documentada em `docs/validation/sf-018-windows.md`

**Target Platform**: Windows nativo (provider MMDevice); Linux/WSL/CI com `NullEndpointProvider` (degradação sem dependências win32)

**Project Type**: agente CLI (monorepo — `agents/windows-audio-agent`) + campo aditivo em contrato versionado + query param no serviço WebSocket

**Performance Goals**: resolução de endpoint no início da captura sem atraso perceptível na inicialização do canal (< 1s adicional); nenhuma mudança de latência no streaming

**Constraints**: mudança de schema estritamente aditiva (campo opcional/anulável); sem fallback silencioso quando `endpointId` não resolve; testes CI sem GPU/hardware; um subprocesso por endpoint WASAPI preservado (ADR-0007)

**Scale/Scope**: poucos canais simultâneos por host (mic + loopback típico); enumeração de dezenas de endpoints no máximo

## Constitution Check

*GATE: avaliado antes da Phase 0 e reavaliado após a Phase 1.*

| Princípio | Avaliação |
|-----------|-----------|
| P1 Especificação antes de código | ⚠️ Retrospectivo: código piloto precedeu a spec formal. Mitigação: spec/plan/tasks formalizados agora; gates G1/G2 avaliados antes de Analyze/Validate/PR. Desvio registrado em Complexity Tracking. |
| P2 Core independente de fornecedores | ✅ Nenhum serviço de domínio importa SDK externo; `pycaw`/`comtypes` ficam confinados ao agente Windows atrás do protocolo de provider. |
| P3 WSL-first, Windows quando necessário | ✅ COM/MMDevice apenas no Python nativo do Windows; testes de lógica rodam no WSL com fakes; venvs não compartilhados. |
| P4 Contratos versionados | ✅ `transcript-event.v2` ganha campo aditivo opcional/anulável `device.endpointId`; ADR-0011 aprovado; testes de contrato incluídos. |
| P5 Separação por canal e origem | ✅ `endpointId` viaja junto de `channelId`/`sourceType`/metadados ponta a ponta, sem misturar canais. |
| P6 Isolamento de endpoint de áudio | ✅ Resolução ocorre dentro do worker do canal; um processo por endpoint WASAPI preservado; sem PyAudio compartilhado. |
| P7 Identidade de dispositivo | ✅ Núcleo da feature: prioridade `endpointId` > `index` > `default`/`nameRegex`; falha explícita sem fallback silencioso. |
| P8 Automação com autorização | ✅ Fluxo prevê PR draft; merge/close manuais. |
| P9 Privacidade por padrão | ✅ Logs contêm apenas identificadores de dispositivo e nomes amigáveis; sem segredos/áudio bruto. |
| P10 Qualidade determinística | ✅ CI Linux com fakes; validação manual Windows gera evidência em `docs/validation/sf-018-windows.md`. |

**Resultado pré-Phase 0**: PASS com desvio justificado em P1 (ver Complexity Tracking).
**Resultado pós-Phase 1**: PASS — o design registrado em research/data-model/contracts não introduziu novas violações.

## Project Structure

### Documentation (this feature)

```text
specs/004-sf-018-mmdevice-endpoint-id/
├── spec.md              # Especificação (formalizada)
├── plan.md              # Este arquivo
├── research.md          # Phase 0 — decisões e alternativas
├── data-model.md        # Phase 1 — entidades e regras
├── quickstart.md        # Phase 1 — guia de validação
├── contracts/           # Phase 1 — delta de contrato (referencia contracts/ raiz)
├── checklists/
│   └── requirements.md  # Checklist de qualidade da spec
└── tasks.md             # Tarefas (T1–T7 concluídas; T8–T12 pendentes)
```

### Source Code (repository root)

```text
agents/windows-audio-agent/
├── src/assistant_hub_audio/
│   ├── mmdevice.py      # MMDeviceEndpointProvider (win32) + NullEndpointProvider
│   ├── endpoints.py     # correlate_devices, find_device_for_endpoint (lógica pura)
│   ├── devices.py       # resolve_device — prioridade endpointId > index > default/regex
│   ├── profiles.py      # DeviceSelector, validação de combinações de seletores
│   ├── capture.py       # abertura de stream + query endpointId no WebSocket
│   └── main.py          # CLI (list-devices com endpointId)
└── tests/
    ├── test_endpoints.py       # correlação e erros de resolução (fakes)
    ├── test_profiles.py        # round-trip YAML, prioridade, combinações inválidas
    ├── test_capture.py         # normalização PCM, resample, noise gate (sem endpointId)
    ├── test_capture_channel.py # classificação erro permanente (não retry) vs. transitório (retry)
    └── test_run_agent.py       # isolamento de falha por canal no supervisor (P6)

contracts/
└── transcript-event.v2.schema.json  # device.endpointId: ["string", "null"]

services/transcription-service/
├── app/main.py          # lê query param endpointId (normalizado p/ null se vazio) e propaga no evento v2
└── tests/
    └── test_ws_audio_contract.py  # contrato WS com endpointId (ausente/presente/vazio)

docs/
├── adr/0011-mmdevice-endpoint-identity.md
└── validation/sf-018-windows.md
```

**Structure Decision**: monorepo existente; a feature vive quase inteira no agente `agents/windows-audio-agent` (novo módulo `mmdevice.py` + `endpoints.py`, ajustes em `devices.py`/`profiles.py`/`capture.py`), com delta aditivo no contrato raiz `contracts/transcript-event.v2.schema.json` e leitura do query param no serviço `services/transcription-service/app/main.py`.

## Estratégia de testes

1. **Linux/CI (pytest, sem hardware)**: fakes de provider e de enumeração; correlação estrutural; os quatro modos de erro de `find_device_for_endpoint`; round-trip de perfil com `endpointId`+`index`; isolamento de falha por canal no supervisor (`test_run_agent.py`) e classificação erro permanente vs. transitório (`test_capture_channel.py`); contrato do WebSocket com `endpointId` (ausente/presente/vazio) em `services/transcription-service/tests/test_ws_audio_contract.py`.
2. **Windows smoke (CI)**: import do provider e CLI sem hardware obrigatório.
3. **Manual Windows**: roteiro em `docs/validation/sf-018-windows.md` — list-devices/probe/run, reboot, hot-plug, dispositivo desabilitado, Bluetooth; evidência com ambiente, commit e resultado (P10).

## Riscos de implementação

- Correlação por nome + ordem é heurística — não apresentar como garantia absoluta; nomes duplicados geram WARNING e desempate por ordem de enumeração.
- Não degradar para `index` quando `endpointId` falhar (P7).
- Manter a mudança de schema estritamente aditiva (P4).
- TOCTOU entre enumeração e abertura do stream: aceito nesta feature; mitigação na SF-019.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| P1 — código piloto antes da spec formal | A investigação da instabilidade de índices exigiu experimentação direta com WASAPI/MMDevice no Windows; o piloto validou a viabilidade da correlação antes de fixar requisitos | Especificar às cegas produziria requisitos especulativos sobre comportamento COM/WASAPI; o desvio é fechado agora com a formalização retrospectiva completa (spec → plan → analyze → validate) antes de qualquer PR |
