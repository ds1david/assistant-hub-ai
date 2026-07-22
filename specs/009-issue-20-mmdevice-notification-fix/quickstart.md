# Quickstart: validar a correção do provider real de notificação MMDevice (Issue #20)

## Pré-requisitos

- WSL: ambiente Python do agente já configurado (`agents/windows-audio-agent`, ver `pyproject.toml`).
- Windows (para a revalidação manual, seção 2): Python nativo com o agente instalado
  (`pip install -e agents/windows-audio-agent`), um dispositivo de áudio USB ou Bluetooth para
  replugar, e um perfil (`profiles/*.yaml`) com um canal configurado por `endpointId` (ver SF-018).

## 1. Validação automatizada (WSL/Linux, sem hardware)

Confirma que a correção (FR-001..FR-004) não regrediu a suíte de hot-plug/captura, usando
`FakeNotificationProvider` — nenhuma dependência de `pywin32`/COM real é carregada (P10).

```bash
cd agents/windows-audio-agent
python3 -m compileall -q src
PYTHONPATH=src python3 -m pytest -q tests -k "hotplug or capture"
```

**Resultado esperado**: todos os testes passam (baseline pós-correção: 30 passed no filtro
`hotplug or capture`, 60 passed na suíte completa — ver `docs/validation/sf-019-windows.md`), incluindo
especificamente:

- `test_listener_subscribe_failure_degrades_without_raising` (FR-002/FR-003/FR-004): falha em
  `subscribe(...)` não propaga exceção, listener fica inerte.
- `test_windows_registration_failure_degrades_to_null_without_raising`: falha na construção do provider
  degrada para `NullNotificationProvider` (política já existente, preservada por FR-003).
- Suíte completa de `specs/006-sf-019-hotplug-listener/quickstart.md` (debounce, filtragem por
  `endpointId`, remoção/chegada) permanece verde sem regressão (FR-007).

## 2. Revalidação manual Windows (provider real, hot-plug real) — FR-005/SC-004

Repete especificamente a seção "run + hot-plug" de `specs/006-sf-019-hotplug-listener/quickstart.md`
(passos 1–8) com a correção aplicada, já que a última execução documentada (2026-07-22) resultou em
FAIL (`ModuleNotFoundError: comtypes.gen.MMDeviceAPILib`) e está marcada como pendente de revalidação.

1. Anotar branch e commit (`git rev-parse --short HEAD`) desta correção.
2. Rodar `assistant-hub-audio run --profile <perfil-com-endpointId>` em foreground.
3. Confirmar que `HotplugListener.__init__` **não** derruba o worker (sem `ModuleNotFoundError` /
   `OSError: [WinError -2147312566]`) e que a captura inicia normalmente.
4. Desconectar fisicamente o dispositivo (USB) ou desligar o Bluetooth.
5. Confirmar que o worker reage à remoção do `endpointId` quase imediatamente (comportamento já
   especificado em SF-019, não alterado por esta correção).
6. Reconectar o mesmo dispositivo físico.
7. Confirmar retomada automática da captura no mesmo `endpointId`.
8. Atualizar `docs/validation/sf-019-windows.md` — seção "run + hot-plug" — com ambiente, commit, passos
   e resultado (PASS ou, se ainda falhar, a nova causa raiz), substituindo a pendência atual (FR-005).

## Referências

- Requisitos completos desta correção: `spec.md` (FR-001..FR-007, SC-001..SC-004).
- Decisões técnicas e alternativas rejeitadas: `research.md`.
- Especificação e quickstart completos da feature de hot-plug (comportamento não alterado por esta
  correção): `specs/006-sf-019-hotplug-listener/`.
- Evidência da causa raiz e da correção: `docs/validation/sf-019-windows.md`.
