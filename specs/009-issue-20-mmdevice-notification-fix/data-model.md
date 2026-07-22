# Data Model: Correção do provider real de notificação MMDevice (Issue #20)

**N/A** — esta correção não introduz, remove nem altera nenhuma entidade de domínio, campo ou relação.

`HotplugEvent`, `ChannelHotplugSignal` e o `Protocol NotificationProvider` já existem e permanecem
inalterados (definidos em `specs/006-sf-019-hotplug-listener/data-model.md`, se aplicável, e em
`agents/windows-audio-agent/src/assistant_hub_audio/hotplug.py`). O único tipo tocado é a interface COM
interna `IMMNotificationClient` (declaração estática de método/IID em `mmdevice_notifications.py`), que
é um detalhe de implementação de infraestrutura Windows, não uma entidade de domínio — não é modelada
aqui, consistente com FR-001 e com a separação `hotplug.py` (puro) / `mmdevice_notifications.py`
(Windows-only) já estabelecida.
