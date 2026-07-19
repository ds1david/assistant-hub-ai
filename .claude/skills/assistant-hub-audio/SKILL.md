---
name: assistant-hub-audio
description: Fronteira do Windows Audio Agent — workers isolados, endpointId MMDevice, perfis e captura WASAPI.
---

# Assistant Hub — Audio Agent

## Quando usar

Mudanças em `agents/windows-audio-agent/**`, perfis YAML de áudio, ADR-0003/0007/0011 ou contratos de device metadata.

## Ler primeiro

- Constituição (P6, P7)
- `docs/adr/0003-windows-host-audio-agent.md`
- `docs/adr/0007-isolated-windows-audio-workers.md`
- `docs/adr/0011-mmdevice-endpoint-identity.md`
- Spec ativa em `specs/004-*` quando relacionada a endpointId

## Regras

1. Um subprocesso por endpoint WASAPI; não compartilhar PyAudio entre canais.
2. Prioridade de seletor: `endpointId` > `index` > `default`/`nameRegex`.
3. Sem fallback silencioso quando `endpointId` foi solicitado e falha.
4. Correlação PortAudio↔MMDevice é heurística (nome + fluxo + ordem); documentar WARNING em duplicatas.
5. `pycaw` apenas com marker `sys_platform == 'win32'`; import tardio.
6. Testes automatizados usam fakes; hardware só em `docs/validation/`.

## Comandos Windows (PowerShell nativo)

```powershell
assistant-hub-audio list-devices --json
assistant-hub-audio probe --profile "<perfil.yaml>"
assistant-hub-audio run --session teste --profile "<perfil.yaml>"
```

## Antes de editar

Declarar arquivos afetados, impacto em schema v2 e plano de testes (unit + manual se necessário).
