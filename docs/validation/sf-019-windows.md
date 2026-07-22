# Validação manual SF-019 — Hot-plug listener

## Ambiente
- Data: 2026-07-22
- Commit: (git rev-parse --short HEAD no main)
- Windows: build do host do usuário
- Python Windows: 3.12 + venv `%LOCALAPPDATA%\AssistantHubAI\audio-agent-venv`
- Agente: 0.1.8 (editable a partir do tree atual)

## Suite automatizada (WSL)
- `pytest -k "hotplug or capture"` → **29 passed**
- suíte completa → **59 passed**

## list-devices (Windows)
- PASS — endpointIds WASAPI presentes (mic index 9, loopback index 10)

## run + hot-plug (Windows)
- FAIL — workers encerram na criação do HotplugListener:
  `ModuleNotFoundError: No module named 'comtypes.gen.MMDeviceAPILib'`
  em `mmdevice_notifications.py:subscribe`
- `GetModule('mmdevapi.dll')` e path System32 → `OSError: [WinError -2147312566]`
- Contorno por reinstall de deps: **não aplicável** (typelib não é gerado pelo pip)

## Resultado
- **FAIL** (runtime Windows do provider real)
- Limitação: SC-006 / T033 bloqueados até corrigir geração/definição de IMMNotificationClient
- Cobertura unitária com FakeNotificationProvider permanece verde

## Correção aplicada (WSL, mesma data)
- `mmdevice_notifications.py`: `IMMNotificationClient` deixou de ser importado de
  `comtypes.gen.MMDeviceAPILib` e passou a ser definido manualmente (IID fixo do SDK +
  `comtypes.STDMETHOD`), eliminando a dependência de geração de typelib que falhava
  (`mmdevapi.dll` não embute typelib).
- `hotplug.py`: `HotplugListener.__init__` agora captura falha de `provider.subscribe(...)`
  e degrada (log de warning, listener inerte) em vez de propagar — mesma política de
  degrade de `get_notification_provider` (FR-006), agora cobrindo também falha na
  subscrição, não só na construção do provider.
- Suíte WSL: `pytest -k "hotplug or capture"` → 30 passed; suíte completa → 60 passed
  (novo teste de regressão `test_listener_subscribe_failure_degrades_without_raising`).

## Pendente
- **Revalidação manual no Windows real** (seção "run + hot-plug" acima) ainda não foi
  refeita — a correção não pôde ser exercitada contra COM real a partir do WSL. Repetir os
  passos 1–8 do quickstart (`specs/006-sf-019-hotplug-listener/quickstart.md`) com a
  correção e atualizar este resultado para PASS/FAIL.