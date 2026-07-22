# Validação manual SF-019 — Hot-plug listener (MMDevice)

## Ambiente

| Campo | Valor |
|-------|--------|
| Data | 2026-07-22 |
| Branch | main (código com fixes COM + `resolved_at_least_once` / backoff pós-sucesso) |
| Commit testado | 28ed56d |
| Windows | Host do desenvolvedor (PowerShell nativo) |
| Python Windows | 3.12 |
| Venv | `%LOCALAPPDATA%\AssistantHubAI\audio-agent-venv` |
| Versão do agente | 0.1.8 (`assistant-hub-audio`, install editable) |
| Transcription service | Ativo em `ws://127.0.0.1:8001` (necessário para stream estável) |
| Profile | `samples/audio-profiles/conference-cam-endpointid.yaml` |
| Session | `tests-019-fix` |

### Dispositivos (WASAPI com endpointId)

| Papel | Friendly name | Index | endpointId |
|-------|---------------|-------|------------|
| Microfone | Microfone (FHD Camera Audio) | 9 | `{0.0.1.00000000}.{a71c8798-dab9-4990-8407-65a27a472b40}` |
| Loopback | Alto-falantes (FHD Camera Audio) [Loopback] | 10 | `{0.0.0.00000000}.{b4557e38-489f-48c6-bdbf-a30ec26e14bd}` |

**Nota de hardware:** nesta máquina o FHD Camera Audio é o **único** conjunto de endpoints de áudio relevante. Despluguar o USB remove **todos** os endpoints do profile (`notpresent`). O estímulo continua válido para SC-006.

---

## 1. Suite automatizada (WSL, sem hardware)

```bash
cd agents/windows-audio-agent
PYTHONPATH=src python3 -m pytest -q tests -k "hotplug or capture"
PYTHONPATH=src python3 -m pytest -q tests
```

| Execução | Resultado |
|----------|-----------|
| `pytest -k "hotplug or capture"` (pré-fixes A/B) | 29–30 passed |
| Suíte completa (pré-fixes) | 59–60 passed |
| Suíte completa (pós-fixes A/B + regressões) | **67 passed** |

Cobertura automatizada: FakeNotificationProvider, debounce, endpoint alheio, remoção/chegada simuladas, `NullNotificationProvider` fora do Windows, regressão de aridade de callback, `EndpointResolutionError` fatal só antes do primeiro sucesso / retry após sucesso.

---

## 2. Runtime Windows — evolução da evidência

### 2.1 list-devices

```powershell
assistant-hub-audio list-devices --json
```

- [x] `endpointId` presente nos devices WASAPI (índices 8/9/10)
- [x] Devices não-WASAPI com `endpointId: null` (esperado)

### 2.2 Falha inicial — `comtypes.gen.MMDeviceAPILib` (corrigida)

**Sintoma (primeira tentativa de `run`):**

```text
ModuleNotFoundError: No module named 'comtypes.gen.MMDeviceAPILib'
  em mmdevice_notifications.py → HotplugListener.__init__ → worker exit 1
```

**Causa:** import de typelib gerado; `GetModule('mmdevapi.dll')` falha (`WinError -2147312566` — DLL sem typelib embutido).

**Correção:** `IMMNotificationClient` definido manualmente via comtypes (IID do SDK); degrade em falha de `subscribe()`.

**Status:** resolvido — workers passam a subir e resolver `endpointId`.

### 2.3 Falha intermediária — assinatura COM + notpresent fatal (corrigida)

**Sintoma no unplug:**

```text
TypeError: OnDeviceStateChanged() takes 3 positional arguments but 4 were given
Endpoint resolution failed permanently ... not retrying
Audio worker stopped unexpectedly ... exit=1
All audio channels stopped
```

**Causas:**
- **Bug A:** callback COM com aridade incorreta (evento perdido).
- **Bug B:** `EndpointResolutionError` / `notpresent` após captura bem-sucedida tratado como fatal.

**Correções:**
- Callbacks puros com `this` explícito + try/except (nunca propagar).
- Flag `resolved_at_least_once`: após primeiro sucesso, falha de resolução → backoff/reconnect, não exit permanente; fail-fast de SF-018 preservado no startup.

### 2.4 Validação PASS — unplug / replug (2026-07-22 ~14:51–14:52)

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& "$env:LOCALAPPDATA\AssistantHubAI\audio-agent-venv\Scripts\Activate.ps1"
pip install -e "\\wsl.localhost\Ubuntu-24.04\home\david\workspace\assistant-hub-ai\agents\windows-audio-agent"

$repo = "\\wsl.localhost\Ubuntu-24.04\home\david\workspace\assistant-hub-ai"
$profile = "$repo\samples\audio-profiles\conference-cam-endpointid.yaml"
assistant-hub-audio run --session tests-019-fix --profile $profile
```

#### Timeline

| Hora | Observação |
|------|------------|
| 14:51:34–35 | Canais `local_conference_cam` e `remote_conference_output` ativos com `endpointId` corretos |
| 14:51:53 | Unplug → `OSError: [Errno -9999] Unanticipated host error` / `Stream not open` |
| 14:51:54 | `Endpoint resolution failed for channel=... after a prior successful capture ... falling back to the generic reconnect backoff instead of exiting` |
| 14:51:54–00 | Retries com `notpresent` / correlation degradada — **processo e workers vivos** |
| 14:52:02 | Re-resolve + `Endpoint removed for channel=... was removed while channel=... was capturing` |
| **14:52:13** | **Resume** nos **mesmos** `endpointId` (mic + loopback), sem reiniciar o processo |
| 14:52:25 | Segundo unplug (stream again) |
| 14:52:31 | `Endpoint removed` novamente |
| **14:52:42** | **Segundo resume** nos mesmos `endpointId` |

#### Critérios SC-006 / aceite

| Critério | Status |
|----------|--------|
| Captura inicial com `endpointId` | PASS |
| Unplug não encerra o supervisor/workers de forma permanente | PASS |
| Sem `TypeError` em callbacks COM | PASS |
| Sem `failed permanently` após captura prévia bem-sucedida | PASS |
| Mensagem explícita de endpoint removido / notpresent (sem fallback silencioso para outro device) | PASS |
| Replug → resume no mesmo `endpointId` sem novo `run` | PASS |
| Segundo ciclo unplug/replug | PASS |

#### Trechos de log representativos

**Start:**
```text
channel=local_conference_cam ... endpoint_id={0.0.1.00000000}.{a71c8798-dab9-4990-8407-65a27a472b40}
channel=remote_conference_output ... endpoint_id={0.0.0.00000000}.{b4557e38-489f-48c6-bdbf-a30ec26e14bd}
Capture supervisor is running in FOREGROUND
```

**Unplug → backoff (não exit):**
```text
Endpoint resolution failed for channel=local_conference_cam after a prior successful capture (likely a transient unplug/notpresent); falling back to the generic reconnect backoff instead of exiting.
Endpoint resolution failed for channel=remote_conference_output after a prior successful capture (likely a transient unplug/notpresent); falling back to the generic reconnect backoff instead of exiting.
```

**Sinal de remoção:**
```text
Endpoint removed for channel=remote_conference_output: Endpoint '{0.0.0.00000000}.{b4557e38-489f-48c6-bdbf-a30ec26e14bd}' was removed while channel=remote_conference_output was capturing.
Endpoint removed for channel=local_conference_cam: Endpoint '{0.0.1.00000000}.{a71c8798-dab9-4990-8407-65a27a472b40}' was removed while channel=local_conference_cam was capturing.
```

**Resume (mesmo endpointId):**
```text
channel=local_conference_cam ... endpoint_id={0.0.1.00000000}.{a71c8798-dab9-4990-8407-65a27a472b40}
channel=remote_conference_output ... endpoint_id={0.0.0.00000000}.{b4557e38-489f-48c6-bdbf-a30ec26e14bd}
```

---

## 3. Segurança

- [x] Logs revisados sem áudio bruto / tokens / segredos
- [x] Evidência baseada em metadados de canal, `endpointId` e mensagens de erro de resolução

---

## 4. Resultado final

| Dimensão | Resultado |
|----------|-----------|
| Suite WSL | PASS (67 passed pós-fixes) |
| list-devices / start com endpointId | PASS |
| Provider COM real (sem typelib gen) | PASS |
| Callbacks COM (aridade / sem TypeError) | PASS |
| Política notpresent pós-sucesso (backoff) | PASS |
| Ciclo unplug → espera → replug → resume | **PASS** |
| **Resultado global SF-019 Windows (SC-006)** | **PASS** |

### Limitações / ruído aceitável

1. Durante `notpresent`, logs repetidos de “Endpoint correlation may be degraded” e “No MMDevice endpoint matched…” — esperado; candidata a rebaixamento para DEBUG em melhoria futura.
2. Hardware com um único device de áudio: unplug remove todos os endpoints do profile; não invalida o teste.
3. Device Manager isolado (sem unplug) em sessões anteriores não produziu o mesmo estímulo; evidência decisiva foi unplug físico USB.

### Referências

- Spec: `specs/006-sf-019-hotplug-listener/`
- Quickstart: `specs/006-sf-019-hotplug-listener/quickstart.md` §2
- Código: `hotplug.py`, `mmdevice_notifications.py`, `capture.py`
- Formato alinhado a: `docs/validation/sf-018-windows.md`

### Follow-ups (fora do aceite SF-019)

- [ ] `default_microphone()` WASAPI-aware (issue separada)
- [ ] Alinhar VERSION reportada pelo CLI do agent
- [ ] Opcional: reduzir verbosidade de correlation durante reconnect
```
