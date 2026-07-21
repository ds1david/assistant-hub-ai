# Research: Listener de hot-plug nativo MMDevice (SF-019)

## 1. API nativa para notificações de hot-plug

**Decision**: Implementar um `IMMNotificationClient` (COM) via `comtypes`, registrado no mesmo
`IMMDeviceEnumerator` já obtido por `pycaw.utils.AudioUtilities.GetDeviceEnumerator()` (usado hoje em
`mmdevice.py`), chamando `RegisterEndpointNotificationCallback`. O client escuta `OnDeviceStateChanged`,
`OnDeviceAdded` e `OnDeviceRemoved` e traduz cada callback para um `HotplugEvent` de domínio
(`endpoint_id`, `event_type`, `timestamp`).

**Rationale**: `pycaw` já é dependência Windows do projeto (`pyproject.toml`,
`sys_platform == 'win32'`) e usa `comtypes` internamente para gerar os wrappers de `mmdeviceapi` — a
mesma infraestrutura COM já carregada para `list_endpoints()`/`default_endpoint()` em
`mmdevice.py` cobre `IMMNotificationClient`, sem dependência nova. Reaproveitar o mesmo enumerator
evita um segundo objeto COM por processo.

**Alternatives considered**:
- **Polling periódico** (repetir `list_endpoints()` a cada N segundos e diffar estado): rejeitado — a
  issue #13 pede explicitamente um "listener nativo", e polling reintroduziria a mesma latência que
  esta feature existe para eliminar (o problema central de SF-018/SF-019 é justamente não esperar o
  próximo ciclo).
- **pycaw `AudioUtilities.CoInitialize` + callback de terceiros (ex. `winrt`)**: rejeitado — adicionaria
  uma dependência nova (`winrt`) quando `comtypes`/`pycaw` já resolvem o problema.

## 2. Onde o listener vive (processo)

**Decision**: já fechado em `/speckit.clarify` (spec `## Clarifications`) — um `HotplugListener` por
subprocesso de canal, instanciado dentro de `run_channel_worker`/`capture_channel`, nunca no supervisor
(`run_agent`). Sem IPC novo.

**Rationale**: preserva P6/ADR-0007 (isolamento nativo por endpoint) e evita construir um canal de
IPC supervisor↔worker que hoje não existe (`run_agent` só usa `subprocess.Popen` + `poll()`).

## 3. Como o listener se comunica com o laço de captura existente

**Decision**: o callback COM roda em uma thread nativa própria (thread de callback do Core Audio,
fora do controle direto do Python). O `HotplugListener` traduz cada callback em uma atualização de um
`threading.Event`-like signal por canal (`_ChannelHotplugSignal`), análogo ao `stop_event` já usado em
`capture_channel`/`_capture_once`. Duas reações:
- **Remoção**: o signal de remoção interrompe o `while not stop_event.is_set(): stream.read(...)` de
  `_capture_once` prontamente (checado a cada iteração do loop de leitura, que já roda em chunks
  pequenos de ~64ms a 16kHz/1024 frames — latência de detecção limitada pelo tamanho do chunk, não
  pelo backoff de reconexão).
- **Chegada**: quando `capture_channel` está em `stop_event.wait(reconnect_delay)` (espera de backoff),
  o signal de chegada acorda essa espera antecipadamente (um `threading.Event.wait` adicional
  observado no mesmo loop), disparando nova tentativa de `_capture_once` imediatamente.

**Rationale**: reaproveita o padrão de sinalização já existente (`stop_event`) em vez de introduzir
filas/`asyncio` novos; mínimo de mudança estrutural em `capture.py`.

**Alternatives considered**:
- **Reescrever `capture_channel` em `asyncio`**: rejeitado — mudança estrutural grande e desnecessária
  para o escopo desta feature; o padrão `threading.Event` já resolve o requisito sem reescrever o loop
  de captura síncrono existente (PyAudio/WebSocket síncronos).

## 4. Debounce de rajadas

**Decision**: debounce simples em memória por `endpoint_id`: um evento só é repassado ao canal se
decorreu pelo menos uma janela curta fixa (implementação: constante interna, ordem de poucas centenas
de ms) desde o último evento repassado para aquele `endpoint_id`. Eventos dentro da janela são
descartados (não enfileirados).

**Rationale**: suficiente para absorver bounce de driver (FR-005) sem atrasar perceptivelmente a
detecção real (a janela é bem menor que o backoff genérico de até 10s que esta feature substitui).
Testável deterministicamente com um relógio injetável/fake no teste (sem `time.sleep` real).

**Alternatives considered**:
- **Debounce configurável por perfil**: rejeitado — escopo não pede configurabilidade; constante interna
  é suficiente e mantém a spec livre de detalhe de implementação (Assumptions já registra isso).

## 5. Padrão de testabilidade sem hardware

**Decision**: seguir exatamente o padrão já usado em `endpoints.py` para `EndpointProvider`/
`NullEndpointProvider`/`get_endpoint_provider()`: um `Protocol` `NotificationProvider` (pure, sem
import de `comtypes`/`pycaw`) com `NullNotificationProvider` (não-Windows ou falha de registro COM) e
um provider real Windows-only importado lazily. Testes usam um `FakeNotificationProvider` que permite
injetar eventos programaticamente (`emit(endpoint_id, event_type)`), sem hardware nem COM real.

**Rationale**: consistência arquitetural com o módulo irmão (`endpoints.py`/`mmdevice.py`) já validado
em SF-018; reduz carga cognitiva e reaproveita a mesma convenção de degrade (P3/P10).
