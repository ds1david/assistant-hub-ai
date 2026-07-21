# Quickstart: validar o listener de hot-plug (SF-019)

## Pré-requisitos

- WSL: ambiente Python do agente já configurado (`agents/windows-audio-agent`, ver `pyproject.toml`).
- Windows (para a validação manual, seção 2): Python nativo com o agente instalado
  (`pip install -e agents/windows-audio-agent`), um dispositivo de áudio USB ou Bluetooth para
  replugar, e um perfil (`profiles/*.yaml`) com um canal configurado por `endpointId` (ver SF-018).

## 1. Validação automatizada (WSL/Linux, sem hardware)

Roda a suíte de testes do listener e do fluxo de captura afetado, usando o `FakeNotificationProvider`
descrito em `data-model.md` — nenhuma dependência de `pywin32`/COM é carregada.

```bash
cd agents/windows-audio-agent
python3 -m compileall -q src
PYTHONPATH=src python3 -m pytest -q tests -k "hotplug or capture"
```

**Resultado esperado**: todos os testes passam, cobrindo (ver `data-model.md` e FR-001..FR-008 em
`spec.md`):

- remoção do `endpointId` em captura ativa → erro específico, sem esperar o backoff (US1);
- chegada do mesmo `endpointId` após remoção → retomada automática (US2);
- notificação de `endpointId` alheio → nenhuma reação (FR-004);
- rajada de eventos duplicados → no máximo uma reação (FR-005, SC-005);
- chegada que ainda falha a re-resolução → cai no backoff genérico, sem encerramento permanente
  (FR-003 / Clarifications Q3);
- plataforma não-Windows → `NullNotificationProvider`, sem exceção (FR-006).

## 2. Validação manual Windows (hot-plug real)

1. Anotar branch e commit (`git rev-parse --short HEAD`).
2. Rodar `assistant-hub-audio run --profile <perfil-com-endpointId>` em foreground.
3. Confirmar nos logs `INFO` que o canal iniciou capturando o `endpointId` esperado (ver formato de
   log existente em `capture.py::_capture_once`).
4. Desconectar fisicamente o dispositivo (USB) ou desligar o Bluetooth.
5. Confirmar que o worker reporta o erro específico de "endpoint removido" quase imediatamente (não
   após ~10s de backoff).
6. Reconectar o mesmo dispositivo físico.
7. Confirmar que o worker retoma a captura automaticamente no mesmo `endpointId`, sem reiniciar o
   processo manualmente.
8. Registrar o resultado em `docs/validation/sf-019-windows.md` (ambiente, commit, passos, resultado
   PASS/FAIL) — formato análogo a `docs/validation/sf-018-windows.md` (constituição P10, SC-006).

## Referências

- Requisitos completos: `spec.md` (FR-001..FR-008, SC-001..SC-006).
- Entidades e sinalização interna: `data-model.md`.
- Decisões técnicas e alternativas rejeitadas: `research.md`.
