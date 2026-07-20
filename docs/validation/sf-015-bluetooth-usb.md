# Validação manual SF-015 — Bluetooth output + microfone USB

## Ambiente

- Data: 2026-07-20
- Commit testado: 4e38bf9
- Branch: feature/sf-015-sf-015-matriz-manual-de-hardware-r1
- Windows (build):
- Python (Windows): 3.12 (venv `%LOCALAPPDATA%\AssistantHubAI\audio-agent-venv`)
- Versão do agente (`assistant-hub-audio` / pyproject): 0.1.8
- WSL / serviço de transcrição (se usado):

## Dispositivos

| Papel | Friendly name | endpointId | Notas |
|-------|---------------|------------|-------|
| Saída Bluetooth | — | — | Sem dispositivo Bluetooth pareado nesta máquina no momento do teste |
| Microfone USB | — | — | Sem microfone USB dedicado conectado — só "Microfone (FHD Camera Audio)" (webcam), que não é um microfone USB dedicado |

## Perfil usado

- Path: `samples/audio-profiles/bluetooth-output-usb-mic.yaml` (sample genérico do repo)
- Canais: `local_usb_microphone` (kind `input`, `nameRegex: "USB|Conference|Microphone|Microfone"`), `remote_bluetooth_audio` (kind `loopback`, `nameRegex: "Bluetooth|Headphones|Stereo.*(Loopback|loopback)"`)

## Casos

### 1. list-devices

```powershell
assistant-hub-audio list-devices --json
```

- [ ] endpointId presente e correlacionado para o dispositivo Bluetooth e o microfone USB
- [ ] nomes duplicados/genéricos entre os dois dispositivos observados e documentados (WARNING de enumeration order, se aplicável)

### 2. probe com endpointId

```powershell
assistant-hub-audio probe --profile "<path-do-perfil>"
```

- [ ] resolve ambos os canais para o dispositivo correto

### 3. run captura

```powershell
assistant-hub-audio run --session sf015-bluetooth-usb --profile "<path-do-perfil>"
```

- [ ] evento v2 de cada canal preserva endpointId/channelId/sourceType
- [ ] sem regressão de canal em relação aos contratos SF-016/017/018

### 4. Reconexão Bluetooth durante a sessão

- [ ] comportamento explícito (sucesso ou erro claro) após reconexão
- [ ] sem fallback silencioso para outro dispositivo (P7/ADR-0011)

## Latência percebida

- Notas:

## Frases de referência

| Frase falada | Transcrição | Canal | Resultado |
|---|---|---|---|
| | | bluetooth_output | |
| | | mic_usb | |

## Segurança

- [ ] logs sem segredo / token / áudio bruto

## Resultado

- Resultado: **BLOCKED**
- Evidências/anexos: tentativa em 2026-07-20 com `run-audio-agent-foreground.ps1 -Profile samples\audio-profiles\bluetooth-output-usb-mic.yaml` — `local_usb_microphone` falhou com `nameRegex` ambíguo (casou índices 1, 5, 9 — todos "FHD Camera Audio", nenhum é um USB mic dedicado); `remote_bluetooth_audio` falhou com `nameRegex` sem match (nenhum dispositivo Bluetooth presente). Ambas as falhas são explícitas (sem fallback silencioso — comportamento correto do agente, P7/ADR-0011), só não há hardware compatível.
- Limitações: esta máquina não tem microfone USB dedicado nem dispositivo de saída Bluetooth pareado no momento do teste. Cenário permanece BLOCKED até haver esse hardware disponível.
- Nota separada: a mesma sessão de teste revelou que o venv usado por `run-audio-agent-foreground.ps1` (`%LOCALAPPDATA%\AssistantHubAI\audio-agent-venv`) estava sem `pycaw` instalado ("MMDevice endpoint provider unavailable"), desligando toda a correlação de `endpointId` nesta tentativa — corrigido com `-Reinstall` antes de repetir o Cenário 1.
