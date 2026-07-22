# Data Model: Correção de aridade do callback COM e de `notpresent` fatal (SF-019, Issue #22)

**N/A** — esta correção não introduz, remove nem altera nenhuma entidade de domínio, campo ou relação.

`HotplugEvent`, `ChannelHotplugSignal`, `NotificationProvider` (Protocol) e as exceções
`EndpointResolutionError`/`EndpointRemovedError` já existem e permanecem com a mesma forma pública
(definidas em `specs/006-sf-019-hotplug-listener/` e `agents/windows-audio-agent/src/assistant_hub_audio/`).

O único estado novo introduzido é `resolved_at_least_once: bool`, uma variável local ao laço de
`capture_channel` (Bug B, research.md §3) — não é uma entidade de domínio, não é persistida, não cruza
processos; é um detalhe de controle de fluxo dentro de uma função já existente, análogo a
`reconnect_delay`/`woke_on_arrival` que já vivem no mesmo escopo.
