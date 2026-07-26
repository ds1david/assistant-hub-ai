# Quickstart validation: STT header sessionId / profile

**Feature**: `specs/022-issue-51-stt-ui-header`  
**Date**: 2026-07-25

## Prerequisites

- WSL monorepo checkout on branch of issue #51
- Python env able to run transcription-service tests (`pytest`)
- Optional for full path: STT up (`http://localhost:8001`), Windows agent with known `--session` / `--profile`

## Automated (P10)

```bash
# from repo root
PYTHONPATH=services/transcription-service pytest -q \
  services/transcription-service/tests/test_stt_dashboard_header.py
```

**Expect**:

- Structure: markers from [contracts/stt-dashboard-header.md](./contracts/stt-dashboard-header.md) present in `app/static/index.html`
- Canonical policy (`app/header_session_state.py`): empty → no primary; observe X → primary X; observe Y → primary Y + multi; blank id ignored
- Channel cards HTML template still free of session/profile session fields
- Profile region defaults to agent/`--profile` note (FR-006)

Optional broader suite:

```bash
PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests
```

## Manual (operator path) — SC-001 / SC-004 / clipboard

1. Subir STT (ex. `./scripts/wsl/start-assistant-hub.sh --no-build` ou compose transcription only).
2. Abrir browser em `http://localhost:8001` (ou host configurado).
3. **Antes do agent**: header mostra status de conexão + «aguardando sessão» (ou equivalente); Copiar desabilitado/ausente; **URL base** = origin (MUST).
4. Rodar agent: `assistant-hub-audio run --session <X> --profile <Y.yaml>` (Windows).
5. **SC-001**: em &lt;5s após o primeiro transcript no feed, header mostra **X** completo (sem abrir log PowerShell).
6. **SC-002**: Copiar → colar em editor = **X** (ou falha explícita no controle).
7. Profile: **nota** de origem no agent (não inventar nome a partir do path do yaml).
8. **SC-004**: comparar X no header com sessão ativa do shell / `--session` sem ler log do agent.
9. (Opcional) Segundo agent com session `Z`: multi «2 sessões» (ou equivalente); primário = Z; Copiar = Z.
10. (Opcional) Forçar reconnect do feed: observed/primary **não** some até reload.
11. Confirmar cards de canal **sem** campos de session/profile de sessão (**SC-005**).
12. Docs: buscar em `docs/development/running.md` / `docs/release/min-flow.md` por header/sessionId do Streaming Foundation (**SC-006**).

## Pass criteria

- SC-001–SC-006 mapeáveis (pytest para estrutura/estado; manual para tempo, shell compare, clipboard real).
- Sem mudança de contrato transcript v2 nos diffs.
- Paridade id feed ↔ path de áudio: assumida via pipeline 001 (mesmo `sessionId` no evento).
