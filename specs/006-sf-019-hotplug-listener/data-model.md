# Data Model: Listener de hot-plug nativo MMDevice (SF-019)

Nenhuma persistência é introduzida (sem banco de dados, sem schema de contrato novo). As entidades
abaixo são estruturas em memória, internas ao processo worker de um canal.

## HotplugEvent

Evento de domínio traduzido a partir de um callback nativo (ou emitido por um fake em teste).

| Campo | Tipo | Notas |
|---|---|---|
| `endpoint_id` | `str` | Identificador MMDevice do endpoint afetado; comparado case-insensitively, como em `find_device_for_endpoint`. |
| `event_type` | `Literal["arrived", "removed", "state_changed"]` | `state_changed` para transições ex.: `unplugged`/`disabled` que não chegam como remoção explícita. |
| `timestamp` | `float` (monotonic) | Usado para debounce; não é um relógio de parede. |

**Regras de validação**: `endpoint_id` não vazio. `state_changed` para um estado que não seja
`active` é tratado como `removed` para efeito de reação do canal (edge case da spec); `state_changed`
para `active` é tratado como `arrived`.

## NotificationProvider (Protocol)

Interface pura (sem `comtypes`/`pycaw`), análoga a `EndpointProvider` em `endpoints.py`.

| Membro | Assinatura | Notas |
|---|---|---|
| `subscribe(on_event)` | `(Callable[[HotplugEvent], None]) -> None` | Registra o callback; chamado uma vez por listener. |
| `close()` | `() -> None` | Desregistra/libera recursos nativos (COM), idempotente. |

### Implementações

- **`MMDeviceNotificationProvider`** (Windows-only, `mmdevice.py` ou módulo irmão): implementa
  `IMMNotificationClient` via `comtypes`, registrado no `IMMDeviceEnumerator` de `pycaw`. Import lazy,
  só dentro de `get_notification_provider()`.
- **`NullNotificationProvider`** (não-Windows ou falha ao registrar COM): `subscribe` é no-op, `close`
  é no-op. Nunca emite eventos.
- **`FakeNotificationProvider`** (só em testes, `tests/`): expõe `emit(endpoint_id, event_type)` para
  injetar eventos síncronos e determinísticos no callback registrado.

## ChannelHotplugSignal

Estado de coordenação entre o `HotplugListener` (thread de callback nativo) e o laço de captura
existente em `capture.py` (`capture_channel`/`_capture_once`), por canal.

| Campo | Tipo | Notas |
|---|---|---|
| `configured_endpoint_id` | `str \| None` | `endpointId` do `AudioChannel` deste worker; eventos de outros endpoints são ignorados (FR-004). |
| `removed` | `threading.Event` | Setado quando um `HotplugEvent(removed/state_changed→inativo)` do endpoint configurado chega durante captura ativa; verificado no loop de leitura de `_capture_once`. |
| `arrived` | `threading.Event` | Setado quando um `HotplugEvent(arrived/state_changed→active)` do endpoint configurado chega enquanto o worker está em `stop_event.wait(reconnect_delay)`; usado para acordar a espera antes do teto do backoff. |
| `last_event_at` (por tipo) | `float` (monotonic) | Base do debounce (Research §4); não repassa evento se dentro da janela curta desde o último repassado. |

**Transições relevantes**:
- Captura ativa + `removed` setado → `_capture_once` interrompe o loop de leitura → `EndpointResolutionError`-like sinal específico de "endpoint removido" (distinto de exceção genérica de stream) propaga para `capture_channel`.
- Aguardando reconexão (`stop_event.wait(reconnect_delay)`) + `arrived` setado → tentativa imediata de `_capture_once` (re-chama `resolve_device`); se a resolução falhar mesmo assim, cai de volta no backoff genérico (FR-003, sem estado dedicado adicional — `arrived` é apenas consumido e descartado).
- Worker parado deliberadamente (`stop_event` setado) → `HotplugListener` não reage a `arrived` (FR-008).
