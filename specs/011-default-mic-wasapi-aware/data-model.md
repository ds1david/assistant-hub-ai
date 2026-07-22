# Phase 1 Data Model: Tornar `default_microphone()` WASAPI-aware

Esta correção não introduz entidades novas nem altera schema persistido — reaproveita integralmente as entidades já existentes em `agents/windows-audio-agent/src/assistant_hub_audio/`. O objetivo desta seção é documentar o formato e as regras de validação **como devem passar a se comportar** para o caminho de microfone default, não desenhar algo novo.

## Entidades existentes (inalteradas na forma, afetadas no comportamento)

### Device (dispositivo PortAudio normalizado)

Estrutura já produzida por `_normalized_device()` (`devices.py:20-28`) e devolvida por `default_microphone()`/`default_loopback()`/`device_by_index()`. Nenhum campo novo.

| Campo | Tipo | Descrição |
|---|---|---|
| `index` | `int` | Índice PortAudio do dispositivo na sessão atual (não estável entre execuções) |
| `name` | `str` | Nome amigável reportado pelo PortAudio |
| `hostApi` | `int` | Índice do host API do dispositivo (WASAPI, MME, DirectSound, WDM-KS) |
| `maxInputChannels` | `int` | Canais de entrada suportados |
| `maxOutputChannels` | `int` | Canais de saída suportados |
| `defaultSampleRate` | `int` | Taxa de amostragem default do dispositivo |
| `isLoopbackDevice` | `bool` | Se é um dispositivo de loopback WASAPI |

**Regra de validação alterada por esta feature (FR-001)**: quando `default_microphone()` é chamado, o `Device` devolvido MUST ter `hostApi` igual ao índice do host API WASAPI da sessão (validável comparando com `_wasapi_host_api_index(audio)`, já existente em `devices.py:41-44`). Hoje essa igualdade não é garantida.

### EndpointInfo (identidade MMDevice)

Já definida em `endpoints.py:35-40`, sem alteração de campos:

| Campo | Tipo | Descrição |
|---|---|---|
| `endpoint_id` | `str` | Identificador MMDevice estável (ex.: `{0.0.1.00000000}.{a71c...}`) |
| `friendly_name` | `str` | Nome amigável reportado pelo Windows Core Audio |
| `data_flow` | `DataFlow` (`"render"` \| `"capture"`) | Direção do endpoint |
| `is_default` | `bool` | Se é o default reportado pelo Windows para seu `data_flow` |

**Regra de validação alterada por esta feature (FR-002)**: para um canal com seletor `default: true` de microfone, o resultado combinado de `resolve_device()` (`{**device, **_endpoint_fields(correlation.get(device["index"]))}`, `devices.py:145`) MUST ter `endpointId` preenchido (não `None`) sempre que existir um `EndpointInfo` com `data_flow == "capture"` e `is_default == True` correlacionável ao host API WASAPI. Hoje essa correlação falha porque o `Device` de entrada, resolvido fora do WASAPI, não aparece no dicionário `correlation`.

### AudioChannel / DeviceSelector

Já definidas em `profiles.py`, sem alteração. Relevante apenas o campo `selector.use_default` (mapeado de `default: true` no YAML de perfil), que é o gatilho existente para chamar `default_microphone()` em `resolve_device()` (`devices.py:127`). Nenhuma mudança de schema de perfil.

## Novo comportamento de erro (não é uma entidade, mas parte do "modelo" observável)

| Situação | Comportamento hoje | Comportamento após a correção (FR-003) |
|---|---|---|
| Host API WASAPI presente, com `defaultInputDevice` válido | Devolve o default global do PortAudio (pode ser não-WASAPI) | Devolve o `Device` do `defaultInputDevice` dentro do WASAPI |
| Host API WASAPI ausente ou sem `defaultInputDevice` válido | Devolve o default global do PortAudio (fallback silencioso) | Levanta `RuntimeError` explícito — nenhum dispositivo não-WASAPI é devolvido |

## Relações

Sem mudança no grafo de relações já existente: `AudioChannel` (1) → `DeviceSelector` (1) → resolve para `Device` (0..1 por execução) → correlacionado com `EndpointInfo` (0..1) via `correlate_devices()`. Esta feature apenas corrige qual `Device` é escolhido no caminho `use_default` para canais de entrada (`kind != "loopback"`), tornando essa escolha consistente com a correlação já existente.
