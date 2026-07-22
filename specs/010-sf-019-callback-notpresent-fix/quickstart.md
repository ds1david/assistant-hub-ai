# Quickstart: validar a correção de aridade do callback COM e de `notpresent` fatal (SF-019, Issue #22)

## Pré-requisitos

- WSL: ambiente Python do agente já configurado (`agents/windows-audio-agent`, ver `pyproject.toml`); não instalar `PyAudioWPatch` (Windows-only, sem marker de plataforma no `pyproject.toml`) — instalar só `pytest`/`numpy`/`scipy`/`pyyaml`/`websockets` num venv local, como já feito para `specs/009-.../`.
- Windows (para a revalidação manual, seção 2): Python nativo com o agente instalado, um dispositivo de áudio USB ou Bluetooth para replugar, e um perfil (`profiles/*.yaml`) com um canal configurado por `endpointId` (ver SF-018).

## 1. Validação automatizada (WSL/Linux, sem hardware)

```bash
cd agents/windows-audio-agent
python3 -m compileall -q src
PYTHONPATH=src python3 -m pytest -q tests -k "hotplug or capture or mmdevice_notifications"
```

**Resultado esperado**: todos os testes passam, cobrindo (FR-001..FR-006):

- os 5 callbacks `IMMNotificationClient_On*` aceitam a convenção real de chamada do comtypes
  (`this` + argumentos declarados) sem `TypeError` de aridade (Bug A, FR-001);
- uma exceção lançada dentro de qualquer callback não propaga para o chamador (FR-002);
- uma falha de resolução (`EndpointResolutionError`) **após** uma resolução bem-sucedida anterior no
  mesmo canal é tratada como transitória — o canal continua vivo aguardando arrival/backoff (Bug B,
  FR-004);
- uma falha de resolução **antes de qualquer resolução bem-sucedida** (`endpointId` nunca existiu desde
  o startup) continua fatal/permanente — fail-fast de SF-018 preservado (FR-005);
- suíte completa de `specs/006-sf-019-hotplug-listener/` e `specs/009-issue-20-mmdevice-notification-fix/`
  permanece verde, sem regressão.

## 2. Revalidação manual Windows (unplug/replug real) — FR-007/SC-001..SC-003/SC-005

Segue os "Critérios de validação Windows" da issue #22.

1. Anotar branch e commit (`git rev-parse --short HEAD`) desta correção.
2. Rodar `assistant-hub-audio run --profile <perfil-com-endpointId>` em foreground; confirmar captura
   normal com `endpointId` estável.
3. Desconectar fisicamente o dispositivo (USB) ou desligar o Bluetooth.
4. Confirmar nos logs que **nenhum** `TypeError` aparece nos callbacks `OnDeviceStateChanged`/demais
   (SC-001) e que o worker reage à remoção (log específico de endpoint removido, não um crash).
5. Confirmar que o worker **não** encerra com "failed permanently"/exit inesperado apenas por
   `notpresent` transitório (SC-002) — deve continuar vivo, aguardando o replug.
6. Reconectar o mesmo dispositivo físico.
7. Confirmar que a captura retoma automaticamente no mesmo `endpointId`, sem reiniciar o processo
   manualmente (SC-003).
8. Atualizar `docs/validation/sf-019-windows.md` com ambiente, commit, passos e resultado (PASS, PASS
   parcial explícito, ou nova causa raiz), referenciando a issue #22 (SC-005).

## Referências

- Requisitos completos desta correção: `spec.md` (FR-001..FR-008, SC-001..SC-005).
- Decisões técnicas (causa raiz do Bug A confirmada no código-fonte do `comtypes`; mecanismo do Bug B):
  `research.md`.
- Feature original de hot-plug (comportamento não alterado por esta correção):
  `specs/006-sf-019-hotplug-listener/`.
- Correção anterior relacionada (typelib/`GetModule`, issue #20): `specs/009-issue-20-mmdevice-notification-fix/`.
- Evidência da causa raiz original e da correção de #20: `docs/validation/sf-019-windows.md`.
