# Quickstart de validação — SF-015 Matriz manual de hardware R1

Guia para executar os três cenários e registrar evidência. Estrutura dos registros em [data-model.md](data-model.md); decisões de escopo em [research.md](research.md). Sem testes automatizados novos — suíte de regressão de contrato é a existente em `agents/windows-audio-agent/tests` (ver quickstart da SF-018).

Pré-requisito único: `python -m pip install -e agents/windows-audio-agent` no Python **nativo do Windows** (nunca WSL/Linux — ADR-0003/ADR-0005).

## 0. Arquivos de evidência (já criados)

Os três arquivos já existem em `docs/validation/sf-015-conference-cam.md`, `sf-015-bluetooth-usb.md` e `sf-015-default-mic.md` (T001-T003 concluídos). Você só precisa preenchê-los.

## 1. Cenário 1 — Conference cam (P1)

```powershell
assistant-hub-audio list-devices --json
```

**Esperado**: microfone e saída/loopback da conference cam aparecem com `endpointId` próprio e correto.

```yaml
version: 1
name: conference-cam
channels:
  - id: mic_local
    kind: input       # microfone -> sourceType "microphone" no evento v2
    device:
      endpointId: "<endpointId do microfone da conference cam>"
  - id: loopback_remoto
    kind: loopback     # loopback/render -> sourceType "system" no evento v2
    device:
      endpointId: "<endpointId do render/loopback da conference cam>"
```

```powershell
assistant-hub-audio probe --profile conference-cam.yaml
assistant-hub-audio run --session sf015-conference-cam --profile conference-cam.yaml
```

**Esperado**: evento v2 de cada canal preserva `endpointId`/`channelId`/`sourceType`; falar durante playback remoto não duplica a fala remota como se fosse local (supressão de eco no feed — ADR-0008). Registrar em `sf-015-conference-cam.md`.

## 2. Cenário 2 — Bluetooth output + microfone USB (P2)

Repetir os mesmos três comandos (`list-devices`, `probe`, `run`) com um perfil de dois canais: saída Bluetooth pareada + microfone USB. Casos extras a observar:

- Nomes duplicados/genéricos entre dispositivos Bluetooth e USB de fabricantes diferentes.
- Reconexão do Bluetooth durante a sessão — comportamento deve ser explícito (sucesso ou erro claro), nunca fallback silencioso para outro device (P7).

Registrar em `sf-015-bluetooth-usb.md`.

## 3. Cenário 3 — Microfone default + fechamento retroativo da SF-018 (P1)

```powershell
assistant-hub-audio run --session sf015-default-mic
```

(sem `--profile` apontando dispositivo específico — valida o caminho de microfone default do Windows.)

Em seguida, executar **os mesmos 7 casos já listados em `docs/validation/sf-018-windows.md`** (list-devices, probe com endpointId, run captura, reboot/reenumeração, hot-plug parcial, endpoint desabilitado/inexistente, nomes duplicados) e usar os resultados para:

1. Preencher `sf-015-default-mic.md` (Cenário 3 desta matriz).
2. Preencher `docs/validation/sf-018-windows.md` original, substituindo o placeholder `PASS | FAIL | BLOCKED` por um resultado definitivo.

## 4. Consolidar e comitar

```bash
git add docs/validation/sf-015-conference-cam.md docs/validation/sf-015-bluetooth-usb.md docs/validation/sf-015-default-mic.md docs/validation/sf-018-windows.md
git commit -m "docs(validation): record R1 hardware matrix SF-015 and close SF-018 evidence gap"
```

**Esperado (SC-001..SC-004)**: os três cenários têm resultado PASS/FAIL/BLOCKED definitivo; nenhum dispositivo teve fallback silencioso de `endpointId`/`channelId`/`sourceType`; `sf-018-windows.md` não contém mais o placeholder; qualquer regressão de eco/noise gate está documentada explicitamente, não omitida.
