# Validação manual SF-015 — Microfone default

Este cenário também fecha retroativamente a evidência pendente da SF-018: os 7 casos completos (list-devices, probe, run, reboot/reenumeração, hot-plug parcial, endpoint desabilitado/inexistente, nomes duplicados) são executados e registrados diretamente em [`docs/validation/sf-018-windows.md`](sf-018-windows.md), não duplicados aqui. Este arquivo cobre apenas o caminho de microfone default (sem `--profile` de dispositivo específico).

## Ambiente

- Data: 2026-07-20
- Commit testado: 4e38bf9
- Branch: feature/sf-015-sf-015-matriz-manual-de-hardware-r1
- Windows (build): _a confirmar (rodar `winver` ou `[System.Environment]::OSVersion` no PowerShell)_
- Python (Windows): 3.12.9
- Versão do agente (`assistant-hub-audio` / pyproject): CLI reporta `0.1.7`; `pyproject.toml` declara `0.1.8` — **divergência encontrada**, `main.py` tem `VERSION` hardcoded desatualizada; abrir issue separada, fora do escopo da SF-015
- WSL / serviço de transcrição (se usado): sim, `transcription-service` (Docker `assistant-hub-transcription`) ativo em `ws://127.0.0.1:8001`, confirmado durante testes posteriores desta sessão

## Dispositivo

| Papel | Friendly name | endpointId | Notas |
|-------|---------------|------------|-------|
| Marcado `isDefault: true` no `list-devices` (WASAPI, index 9) | Microfone (FHD Camera Audio) | `{0.0.1.00000000}.{a71c8798-dab9-4990-8407-65a27a472b40}` | **Não foi o device usado pela captura** `run` sem `--profile` |
| Realmente resolvido pelo `run` sem `--profile` (host API MME, index 1) | Microfone (FHD Camera Audio) | _null (sem correlação WASAPI)_ | `default_microphone()` usa `get_default_input_device_info()` do PortAudio, que não força host API WASAPI — ver `devices.py:72-73` |
| Loopback resolvido pelo `run` sem `--profile` (WASAPI, index 10) | Alto-falantes (FHD Camera Audio) [Loopback] | `{0.0.0.00000000}.{b4557e38-489f-48c6-bdbf-a30ec26e14bd}` | Resolvido corretamente via WASAPI — `default_loopback()` força o host API WASAPI (`devices.py:76-86`) |

## Caso

### run captura sem --profile de dispositivo

```powershell
assistant-hub-audio run --session sf015-default-mic
```

- [x] captura *um* microfone default — mas é o default do PortAudio (host API MME, index 1), não o endpoint marcado `isDefault` no WASAPI (index 9)
- [x] canal `remote_audio` (loopback): evento v2 preserva `endpointId`/`channelId`/`sourceType` — URL do worker inclui `&endpointId=%7B0.0.0.00000000%7D...`
- [ ] canal `local_microphone`: evento v2 **não** preserva `endpointId` — `endpoint_id=None` no log, e a URL do worker não tem parâmetro `endpointId` (só `sourceType`/`deviceName`/`deviceIndex`)
- [x] `channelId` e `sourceType` presentes em ambos os canais
- [x] sem regressão nova em relação aos contratos SF-016/017/018 — o caminho `default` sem `--profile` nunca garantiu correlação WASAPI para o canal de microfone; é uma lacuna pré-existente, não algo que quebrou agora

## Latência percebida

- Notas: _a confirmar — falar uma frase e medir tempo até a transcrição aparecer (requer `transcription-service` rodando)_

## Frases de referência

| Frase falada | Transcrição | Canal | Resultado |
|---|---|---|---|
| | | mic_default | _pendente — sessão não incluiu fala com serviço de transcrição confirmado ativo_

## Segurança

- [x] logs sem segredo / token / áudio bruto — revisados os logs do agente e do `transcription-service` usados como evidência nesta sessão

## Resultado

- Resultado: **PASS parcial**
- Evidências/anexos: logs de `run --session sf015-default-mic` (2026-07-20), logs do `transcription-service`; fechamento retroativo dos 7 casos da SF-018 registrado em `docs/validation/sf-018-windows.md`
- Limitações:
  1. Canal `local_microphone` do caminho `default` sem `--profile` não carrega `endpointId` no evento v2 (lacuna pré-existente em `default_microphone()`, não uma regressão desta feature) — recomenda-se abrir issue de follow-up para tornar `default_microphone()` WASAPI-aware como `default_loopback()` já é. **Confirmado reproduzido 2x** (2026-07-20), com `pycaw` presente em ambas as vezes — descarta "ambiente sem pycaw" como causa; é um gap de código em `devices.py::default_microphone()` (usa `get_default_input_device_info()` do PortAudio, não filtra por host API WASAPI), diferente de `default_loopback()` (`devices.py:76-86`), que força WASAPI explicitamente.
  2. Frase de referência e latência **não foram medidas no canal `local_microphone`/`mic_default` especificamente** — a frase de referência real coletada nesta sessão (ver `sf-015-conference-cam.md`) foi no canal `local_conference_cam`, com `endpointId` explícito, não no caminho `default` sem perfil. Ficaria em aberto se esse canal (sem endpointId) também transcreve corretamente — provavelmente sim, já que `channelId`/`sourceType` chegam certos, mas não foi confirmado com fala real.
  3. Fechamento retroativo SF-018 (ver `docs/validation/sf-018-windows.md`) também é PASS parcial: casos 1, 2, 3, 6a (ID desconhecido) e 7 confirmados; casos 4 (reboot), 5 (hot-plug) e 6b (desabilitado) pendentes — dependem de reiniciar o Windows ou desabilitar o dispositivo no Gerenciador de Dispositivos.
