# Data Model — SF-018 MMDevice endpoint identity

## Entidades

### AudioEndpoint (MMDevice)

Identidade estável de um endpoint de áudio no Windows.

| Campo | Tipo | Notas |
|-------|------|-------|
| `endpoint_id` | string | ID MMDevice (`IMMDevice::GetId`); chave de identidade |
| `friendly_name` | string | Nome amigável; pode se repetir entre endpoints |
| `flow` | enum `capture` \| `render` | Direção do fluxo (`eCapture`/`eRender`) |
| `is_active` | bool | Estado do endpoint (ativo vs. desabilitado/desconectado) |

Fornecida por um provider: `MMDeviceEndpointProvider` (Windows) ou `NullEndpointProvider` (demais plataformas — lista vazia, nunca erro).

### PortAudioDevice (enumeração transitória)

| Campo | Tipo | Notas |
|-------|------|-------|
| `index` | int | Volátil — muda após reboot/hot-plug/Bluetooth/driver |
| `name` | string | Nome reportado pela enumeração; loopback carrega sufixo `[Loopback]` |
| `host_api` | string | Apenas WASAPI participa da correlação |
| `flow` | derivado | Captura vs. render/loopback |

### CorrelatedDevice

Resultado de `correlate_devices(portaudio, endpoints)`: `PortAudioDevice` + `endpoint_id` opcional. Regras:

- Casamento estrutural: host API WASAPI + fluxo + FriendlyName; desempate pela ordem de enumeração.
- FriendlyName duplicado ⇒ WARNING no log + desempate determinístico por ordem.
- Dispositivo `[Loopback]` correlaciona ao endpoint **render** original.
- Sem casamento ⇒ `endpoint_id` ausente (dispositivo continua utilizável por seletores legados).

### DeviceSelector (perfil YAML)

| Campo YAML | Campo interno | Tipo |
|------------|---------------|------|
| `endpointId` | `endpoint_id` | string \| null |
| `index` | `index` | int \| null |
| `nameRegex` | `name_regex` | string \| null |
| `default` | `use_default` | bool |

**Validação** (em `profiles.DeviceSelector`):

- Exatamente um seletor definido, com uma exceção: `endpointId` pode coexistir com `index` (agentes antigos ignoram a chave nova e usam `index`; agentes novos preferem `endpointId`).
- `endpointId` em branco é rejeitado; `nameRegex` deve compilar.

**Prioridade de resolução** (P7 / ADR-0011): `endpointId` > `index` > `default`/`nameRegex`.

### TranscriptEvent v2 — `device` (delta aditivo)

| Campo | Tipo | Mudança |
|-------|------|---------|
| `device.index` | integer \| null | existente |
| `device.name` | string \| null | existente |
| `device.endpointId` | string \| null | **novo — opcional/anulável, aditivo** |

`required` do objeto `device` permanece `["index", "name"]`; consumidores antigos ignoram o campo novo.

## Transições de estado — resolução por endpointId

```
perfil com endpointId
        │ início da captura
        ▼
enumerar endpoints (provider) ── endpoint não existe ──► ERRO "endpoint inexistente"
        │
endpoint existe, inativo ────────────────────────────► ERRO "endpoint inativo"
        │
fluxo incompatível com o tipo do canal ──────────────► ERRO "fluxo incompatível"
        │
ativo, sem correlação PortAudio ─────────────────────► ERRO "ativo sem correlação"
        │
        ▼
índice PortAudio ATUAL ──► abre stream ──► endpointId propagado (WS query + evento v2)
```

Todos os erros são fatais para o canal, mencionam `list-devices --json` como diagnóstico e **nunca** degradam para outro seletor.
