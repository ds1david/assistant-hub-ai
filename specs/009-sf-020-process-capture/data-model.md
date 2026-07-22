# Data Model: Captura de áudio por processo (WASAPI loopback por app, SF-020)

## `DeviceSelector` (existente, estendido)

`agents/windows-audio-agent/src/assistant_hub_audio/profiles.py`

| Campo | Tipo | Novo? | Regra |
|---|---|---|---|
| `endpoint_id` | `str \| None` | não | seletor de dispositivo existente (SF-018) |
| `index` | `int \| None` | não | seletor de dispositivo existente |
| `name_regex` | `str \| None` | não | seletor de dispositivo existente |
| `use_default` | `bool` | não | seletor de dispositivo existente |
| `process_id` | `int \| None` | **sim** | seleção por PID exato (FR-001) |
| `process_name` | `str \| None` | **sim** | seleção por nome de processo/aplicativo, case-insensitive (FR-001) |

**Regra de exclusividade** (`validate()`): exatamente um entre `endpointId`, `index`, `nameRegex`,
`default`, `processId`, `processName` deve estar definido — mesma regra já existente, apenas com dois
membros novos no conjunto mutuamente exclusivo. A exceção já existente (`endpointId` + `index`
coexistindo) permanece só entre esses dois; `processId`/`processName` não coexistem com nenhum outro
campo, nem entre si.

**Validações adicionais**:
- `process_id` MUST ser um inteiro positivo.
- `process_name` MUST NOT ser vazio/whitespace (mesma regra já aplicada a `endpoint_id`).

## `ProcessResolution` (novo, conceitual — não é um dataclass exposto, é o retorno de `process_resolver.py`)

Representa o resultado de resolver um `DeviceSelector` por processo num dado instante:

| Campo | Tipo | Descrição |
|---|---|---|
| `pid` | `int` | PID resolvido no momento da resolução |
| `name` | `str` | Nome do processo (ex.: `chrome.exe`) |
| `username` | `str` | Usuário dono do processo, usado para a checagem de FR-011 |

**Regras de resolução** (`process_resolver.py`, research.md §3):
- Por `process_id`: o PID MUST existir e pertencer ao mesmo usuário do agente (FR-011); caso contrário,
  falha explícita (FR-005/FR-011).
- Por `process_name`: exatamente um processo do mesmo usuário MUST corresponder ao nome
  (case-insensitive); zero ou mais de um resultado é falha explícita (FR-005).
- Re-resolução (FR-012, só para `process_name`): quando o PID atualmente em uso não existe mais
  (`psutil.pid_exists`), repetir a resolução por nome; uma única correspondência nova retoma a captura,
  ambiguidade/ausência é falha explícita permanente para aquele canal.

## `transcript-event.v2` — `device` (existente, sem mudança de schema)

Nenhum campo novo. Para canais por processo:

| Campo do schema | Valor produzido |
|---|---|
| `device.index` | `null` |
| `device.name` | string legível identificando o processo (ex.: `"chrome.exe (pid 8842)"`) |
| `device.endpointId` | `null` |
| `sourceType` (nível superior) | `"system"` |

Ver `research.md` §5 e `contracts/README.md` para a justificativa de não estender o schema.

## Relacionamentos

- `AudioChannel.selector: DeviceSelector` já existente — só ganha os dois campos novos, sem mudança de
  cardinalidade/relacionamento.
- `process_resolver.py` não depende de `process_capture.py` (COM) nem vice-versa — `capture.py` os
  compõe no worker do canal, mesma composição já usada entre `endpoints.py`/`mmdevice.py` (SF-018).
