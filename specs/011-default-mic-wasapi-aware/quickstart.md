# Quickstart: Validar `default_microphone()` WASAPI-aware

Guia de validação executável para a correção descrita em [spec.md](./spec.md) / [plan.md](./plan.md). Cobre a parte automatizada (WSL, sem hardware) e a validação manual final (Windows real), exigida por P10 e por FR-007.

## Pré-requisitos

- WSL com o toolchain do projeto (Python 3.11+ gerenciado via SDKMAN/ambiente do repo, conforme `AGENTS.md`/ADR-0005).
- Correção implementada em `agents/windows-audio-agent/src/assistant_hub_audio/devices.py` (`default_microphone()`) e testes novos em `agents/windows-audio-agent/tests/test_devices.py`, conforme [data-model.md](./data-model.md) e [research.md](./research.md).
- Para a etapa manual: host Windows real com pelo menos um dispositivo de entrada marcado `isDefault: true` no host API WASAPI (mesmo tipo de ambiente já usado em `docs/validation/sf-015-default-mic.md`).

## Parte 1 — Suíte automatizada (WSL, sem hardware)

Mesmo comando usado pelo job `windows-audio-agent-unit` do CI (`.github/workflows/ci.yml`):

```bash
python -m compileall agents/windows-audio-agent/src
PYTHONPATH=agents/windows-audio-agent/src pytest -q agents/windows-audio-agent/tests
```

**Resultado esperado**:

- `test_devices.py` (novo) passa, cobrindo:
  - Caso 1 (User Story 1 / FR-001): fake de `pyaudio.PyAudio` com host API WASAPI simulado expondo `defaultInputDevice` válido → `default_microphone()` devolve um `Device` cujo `hostApi` é igual ao índice WASAPI simulado, não o índice de um host API não-WASAPI presente no mesmo fake.
  - Caso 2 (User Story 2 / FR-003): fake sem `defaultInputDevice` WASAPI válido → `default_microphone()` levanta `RuntimeError` explícito, sem devolver dispositivo de outro host API.
- Toda a suíte restante (`test_capture.py`, `test_capture_channel.py`, `test_endpoints.py`, `test_hotplug.py`, `test_process_resolver.py`, `test_profiles.py`, `test_run_agent.py`) continua passando sem alteração — confirma SC-002 (zero regressão, incluindo o caminho de `default_loopback()` já coberto indiretamente pelos testes existentes de captura).

## Parte 2 — Validação manual Windows real (FR-007, P10)

Repete o cenário já documentado em `docs/validation/sf-015-default-mic.md`, agora esperando o resultado corrigido.

1. Confirmar o dispositivo marcado default no WASAPI:
   ```powershell
   assistant-hub-audio list-devices
   ```
   Anotar `endpointId` e índice do dispositivo de entrada com `isDefault: true` (host API WASAPI).

2. Rodar a captura sem `--profile` (canal de microfone usa `default: true` implicitamente):
   ```powershell
   assistant-hub-audio run --session issue27-default-mic-wasapi
   ```

3. Inspecionar o log/evento `transcript-event.v2` do canal `local_microphone`:
   - **Esperado agora**: `endpointId` preenchido e igual ao `endpointId` WASAPI anotado no passo 1 (ao contrário do resultado anterior, `endpoint_id=None`).
   - Confirmar também que `channelId`/`sourceType` continuam presentes (já funcionavam antes).

4. Repetir a checagem para o canal de loopback (`remote_audio`) e confirmar que o comportamento não mudou em relação à validação SF-015 original (regra FR-004 / SC-004).

5. Registrar o resultado em `docs/validation/sf-015-default-mic.md` (atualizando a limitação 1 já documentada) ou em um novo arquivo de validação referenciado a partir dele, com data, commit testado e resultado (PASS / PASS parcial, conforme convenção já usada nos arquivos de `docs/validation/`).

**Resultado esperado (critério de saída)**: os quatro Success Criteria da spec (SC-001 a SC-004) confirmados — `endpointId` estável e correto para o canal de microfone default, suíte automatizada 100% verde, evento v2 com `endpointId` preenchido, e nenhuma regressão no loopback.
