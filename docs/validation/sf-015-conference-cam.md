# Validação manual SF-015 — Conference cam

## Ambiente

- Data: 2026-07-20
- Commit testado: 4e38bf9
- Branch: feature/sf-015-sf-015-matriz-manual-de-hardware-r1
- Windows (build):
- Python (Windows): 3.12 (venv `%LOCALAPPDATA%\AssistantHubAI\audio-agent-venv`, reinstalado com `pycaw-20251023`)
- Versão do agente (`assistant-hub-audio` / pyproject): 0.1.8
- WSL / serviço de transcrição (se usado): _a confirmar se estava ativo durante o teste_

## Dispositivos

| Papel | Friendly name | endpointId | Notas |
|-------|---------------|------------|-------|
| Microfone (conference cam) | Microfone (FHD Camera Audio) [index 9, WASAPI] | `{0.0.1.00000000}.{a71c8798-dab9-4990-8407-65a27a472b40}` | Mesmo device também aparece em MME (index 1) e DirectSound (index 5) sem endpointId — por isso `nameRegex` é ambíguo nesta máquina; `endpointId` explícito resolveu certo |
| Render / loopback (conference cam) | Alto-falantes (FHD Camera Audio) [Loopback] [index 10, WASAPI] | `{0.0.0.00000000}.{b4557e38-489f-48c6-bdbf-a30ec26e14bd}` | |

## Perfil usado

- Path: `samples/audio-profiles/conference-cam-endpointid.yaml` (criado manualmente com `endpointId` explícito, já que os samples do repo usam `nameRegex`/`default`, que se mostraram ambíguos/incompletos nesta máquina)
- Canais: `local_conference_cam` (kind `input`), `remote_conference_output` (kind `loopback`)

## Casos

### 1. list-devices

```powershell
assistant-hub-audio list-devices --json
```

- [x] endpointId presente e correlacionado para microfone e render/loopback da conference cam

### 2. probe com endpointId

- [x] resolução validada implicitamente via `run` (ver caso 3) — não foi executado `probe` como comando isolado, mas a mesma resolução por `endpointId` é usada internamente e funcionou para os dois canais

### 3. run captura

```powershell
.\scripts\windows\run-audio-agent-foreground.ps1 -Session sf015-conference-cam -Profile .\samples\audio-profiles\conference-cam-endpointid.yaml
```

- [x] evento v2 de cada canal preserva endpointId/channelId/sourceType — confirmado no log: `local_conference_cam` com `endpoint_id={0.0.1.00000000}...`, `remote_conference_output` com `endpoint_id={0.0.0.00000000}...`; ambos com `endpointId=` presente na URL do WebSocket
- [x] sem regressão de canal em relação aos contratos SF-016/017/018

### 4. Supressão de eco (ADR-0008)

- [x] falar durante playback remoto simultâneo não duplica a fala remota como se fosse local no feed de transcrição — **confirmado**, com uma ressalva de proveniência (ver nota abaixo)
- [x] limitação documentada

**Nota de proveniência**: a evidência de supressão de eco vem da sessão companheira `session-20260720-183342` (perfil `default.yaml`, mesmo hardware físico — conference cam FHD Camera Audio), não da sessão `sf015-conference-cam` com `endpointId` explícito (essa rodou sem áudio tocando, sem eco a suprimir). Confirmado nos logs do `transcription-service` (`docker logs assistant-hub-transcription`), 2026-07-20 21:35–21:36 UTC, 8 ocorrências de `Suppressed microphone echo` com similaridade 0.82–1.00 entre o canal `local_microphone` e `remote_audio` (um vídeo de receita tocava nos alto-falantes durante o teste). O mecanismo de supressão de eco atua sobre similaridade de texto entre canais, independente de `endpointId`/`index` — a evidência é válida para este par físico de dispositivos.

## Latência percebida

- Notas: medida objetivamente via `GET /v1/sessions/sf015-conference-cam-frase/metrics`, canal `local_conference_cam` (5 amostras): **p50=402ms, p95=450ms, min=363ms, max=450ms, avg=398ms** — sub-segundo, consistente com o setup GPU/`small`/`float16` de `r1-audio-validation.md`.

## Frases de referência

| Frase falada | Transcrição | Canal | Resultado |
|---|---|---|---|
| "arquitetura hexagonal, Spring Boot, WSL..." (mencionando Linux/Windows) | "Arquiteturas agonais. Segura hexagonal, Spring Boot. Spring Boot, WSL Livre. Assele, Linux, Windows, Linux, Subsea. Não é subsistente?" | local_conference_cam | PASS — canal e `endpointId` corretos; imprecisão de STT é esperada do modelo `small`, não é defeito de identidade de dispositivo (fora do escopo desta validação) |
| _sem frase própria testada neste canal_ | | remote_conference_output | N/A para esta rodada — endpointId/funcionamento do canal já confirmados no caso 3 e na sessão de supressão de eco |

## Segurança

- [x] logs sem segredo / token / áudio bruto — revisados os logs do agente e do `transcription-service` usados como evidência; contêm apenas `endpointId`, nomes de dispositivo e texto transcrito, sem credenciais

## Resultado

- Resultado: **PASS**
- Evidências/anexos: logs do `run-audio-agent-foreground.ps1` (2026-07-20, sessões `sf015-conference-cam` e `sf015-conference-cam-frase`) + logs do `transcription-service` (`docker logs assistant-hub-transcription`) + `GET /v1/sessions/sf015-conference-cam-frase/transcript` e `/metrics` + sessão companheira `session-20260720-183342` para a evidência de eco
- Limitações: (1) evidência de supressão de eco vem de uma sessão companheira sem `endpointId` explícito no canal de microfone, não da sessão `sf015-conference-cam` propriamente — mecanismo é independente de `endpointId`, mas fica registrado para rastreabilidade; (2) `probe` não foi executado como comando isolado, só validado implicitamente via `run`; (3) transcrição do modelo `small` tem imprecisões esperadas, não relacionadas à identidade de dispositivo; (4) achado à parte, fora do escopo deste PASS: `default_microphone()` não é WASAPI-aware (ver `sf-015-default-mic.md`) — recomenda-se issue de follow-up.
