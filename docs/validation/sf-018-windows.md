# Validação manual SF-018 — MMDevice endpoint ID

## Ambiente

- Data: 2026-07-20
- Commit testado: 4e38bf9
- Branch: feature/sf-015-sf-015-matriz-manual-de-hardware-r1
- Windows (build):
- Python (Windows): 3.12 (venv `%LOCALAPPDATA%\AssistantHubAI\audio-agent-venv`, `pycaw-20251023`)
- Versão do agente (`assistant-hub-audio` / pyproject): 0.1.8
- WSL / serviço de transcrição (se usado): sim, `transcription-service` (Docker `assistant-hub-transcription`) ativo em `ws://127.0.0.1:8001`

## Dispositivos

| Papel | Friendly name | endpointId | Notas |
|-------|---------------|------------|-------|
| Microfone | Microfone (FHD Camera Audio) [index 9, WASAPI] | `{0.0.1.00000000}.{a71c8798-dab9-4990-8407-65a27a472b40}` | Mesmo nome também em MME (index 1) e DirectSound (index 5), sem endpointId — ver Caso 7 |
| Render / loopback | Alto-falantes (FHD Camera Audio) [Loopback] [index 10, WASAPI] | `{0.0.0.00000000}.{b4557e38-489f-48c6-bdbf-a30ec26e14bd}` | |
| Bluetooth (se houver) | — | — | Sem dispositivo Bluetooth nesta máquina |
| Desabilitado (teste negativo) | _pendente_ | _pendente_ | Requer desabilitar um dispositivo no Gerenciador de Dispositivos — ver Caso 6 |

## Perfil usado

- Path: `samples/audio-profiles/conference-cam-endpointid.yaml`
- Seletores: `endpointId` explícito (prioridade máxima, P7/ADR-0011) — `nameRegex`/`default` se mostraram ambíguos/incompletos nesta máquina (ver Casos 3 e 7)

## Casos

### 1. list-devices

```powershell
assistant-hub-audio list-devices --json
```

- [x] endpointId presente nos dispositivos WASAPI correlacionados — index 9 (mic) e index 10 (loopback), confirmado em múltiplas execuções 2026-07-20
- [x] devices não-WASAPI sem correlação forçada — index 1 (MME) e 5 (DirectSound) do mesmo microfone aparecem com `endpointId: null`, corretamente não correlacionados

### 2. probe com endpointId

```powershell
& "$env:LOCALAPPDATA\AssistantHubAI\audio-agent-venv\Scripts\assistant-hub-audio.exe" probe --profile samples\audio-profiles\conference-cam-endpointid.yaml
```

- [x] resolve o dispositivo correto — `OK channel=local_conference_cam ... device=[9] ...` e `OK channel=remote_conference_output ... device=[10] ...`
- [x] log mostra endpoint_id — ambas as linhas trazem `endpointId={...}`

### 3. run captura

```powershell
.\scripts\windows\run-audio-agent-foreground.ps1 -Session sf015-conference-cam -Profile samples\audio-profiles\conference-cam-endpointid.yaml
```

- [x] stream abre no índice atual correto — index 9 e 10, confirmado no log do agente
- [x] evento v2 contém endpointId — confirmado na URL do WebSocket e no log `Audio channel connected` do `transcription-service`
- [x] dashboard/feed sem regressão de canal — `channelId`/`sourceType` corretos, transcrição chegou no canal certo (ver `sf-015-conference-cam.md`)

### 4. Reboot ou reenumeração

- Índice PortAudio antes: _pendente_
- Índice depois: _pendente_
- [ ] mesmo endpointId continua capturando o dispositivo correto — **pendente**, requer reboot real do Windows

### 5. Hot-plug (parcial; SF-019 cobre listener)

- [ ] após replug, novo run com mesmo perfil/endpointId funciona — **pendente**, requer desconectar/reconectar o dispositivo (ou desabilitar/reabilitar no Gerenciador de Dispositivos como substituto)
- [ ] falha compreensível se endpoint sumiu — coberto indiretamente pelo Caso 6a (endpointId inexistente); reconexão real ainda não testada

### 6. Endpoint desabilitado / inexistente

- [ ] mensagem distinta para desabilitado/unplugged — **pendente**, requer desabilitar o dispositivo no Gerenciador de Dispositivos
- [x] mensagem distinta para ID desconhecido com alternativas — confirmado 2026-07-20 usando `samples/audio-profiles/conference-cam-fake-endpoint.yaml` (endpointId inexistente): `RuntimeError: Endpoint ID '...' was not found for channel kind=input. Available capture endpoints: [lista com state=active/notpresent]. Run 'assistant-hub-audio list-devices --json' and update the profile.`
- [x] sem fallback silencioso para outro device — o erro interrompe a execução, não escolhe outro device automaticamente

### 7. Bluetooth / nomes duplicados (se aplicável)

- [ ] WARNING de enumeration order quando nomes duplicados — **não existe esse WARNING no código atual** (verificado em `endpoints.py`/`devices.py`); achado documentado, não é uma falha desta validação
- [x] comportamento documentado — nomes duplicados entre host APIs (MME index 1, DirectSound index 5, WASAPI index 9, todos "Microfone (FHD Camera Audio)") causam **erro explícito de ambiguidade** ao usar `nameRegex` sem correlação suficiente (`RuntimeError: ... is ambiguous; matched indexes: 1, 5, 9`, observado 2026-07-20 ao testar `samples/audio-profiles/bluetooth-output-usb-mic.yaml`); usar `endpointId` explícito evita o problema inteiramente, consistente com a prioridade de seleção do ADR-0011

## Segurança

- [x] logs sem segredo / token / áudio bruto — revisados os logs do agente e do `transcription-service` usados como evidência nesta sessão

## Resultado

- Resultado: **PASS parcial** — Casos 1, 2, 3, 6 (ID desconhecido) e 7 confirmados com evidência real; Casos 4 (reboot/reenumeração), 5 (hot-plug) e a parte "desabilitado" do Caso 6 seguem **pendentes**, dependem de reiniciar o Windows ou desabilitar o dispositivo no Gerenciador de Dispositivos
- Evidências/anexos: logs de `list-devices`/`probe`/`run` (2026-07-20), logs do `transcription-service` (`docker logs assistant-hub-transcription`), `GET /v1/sessions/.../transcript` e `/metrics`
- Limitações: (1) reboot/hot-plug/desabilitado ainda não executados — placeholder não pode ser considerado 100% fechado até isso ser feito; (2) não há WARNING automático de enumeration order no código, apenas erro de ambiguidade ao usar `nameRegex` (comportamento seguro, mas diferente do descrito literalmente no template); (3) achado à parte, fora do escopo deste resultado: `default_microphone()` (seletor `default` sem `endpointId` explícito) não é WASAPI-aware — ver `docs/validation/sf-015-default-mic.md`, recomenda-se issue de follow-up.
