# Research: R5 — Audio Agent sidecar

**Date**: 2026-07-26  
**Spec**: [spec.md](./spec.md)

## Decision 1 — Ordem de resolução do binário

**Decision**: `sidecar_app` → `config_or_env` → `path` → `missing`.

| Prioridade | Origem | Quando |
|------------|--------|--------|
| 1 | Sidecar empacotado | Arquivo existe junto aos recursos/binários do app Tauri (`externalBin` / resource dir) |
| 2 | Override | `ASSISTANT_HUB_AUDIO_BIN` ou campo em `shell-config.json` |
| 3 | PATH | `assistant-hub-audio` / `assistant-hub-audio.exe` via lookup de PATH |
| 4 | Missing | Nenhuma das anteriores |

**Rationale**: Produto Desktop Lite deve preferir o binário distribuído com a app (reproduzível, versionado com o shell). Developer mode sem sidecar cai no PATH/venv já usado em 014. Override explícito cobre CI e caminhos custom sem recompilar.

**Alternatives considered**:
- Só PATH — rejeitado (não fecha o buraco de 002).
- Só sidecar — quebra Developer WSL (FR-008).
- PATH antes de sidecar — risco de pegar venv antigo em máquina com app instalada.

## Decision 2 — Mecanismo Tauri de empacotamento

**Decision**: Declarar o agent como `bundle.externalBin` no `tauri.conf.json`, com binário preparado em `apps/desktop-shell/src-tauri/binaries/assistant-hub-audio` (sufixo de target triple no build Windows conforme convenção Tauri 2).

**Rationale**: Padrão oficial Tauri para sidecars; o runtime resolve o path relativo ao executável do shell. Documentado em `docs/references.md`.

**Alternatives considered**:
- Copiar só para `resources/` e spawn manual — funciona, mas perde convenções de path do Tauri.
- Instalar agent via MSI separado — fora do escopo (dois instaladores).

## Decision 3 — Como produzir o `.exe` do agent no Windows

**Decision**: Script PowerShell documentado que, no host Windows de referência:
1. Cria/usa venv do agent (padrão já em scripts Windows).
2. Gera um executável one-file (PyInstaller ou equivalente documentado) **ou**, na primeira fatia operacional, copia o launcher `assistant-hub-audio.exe` do venv Scripts **desde que** as deps estejam no mesmo venv referenciado — preferência: **one-file PyInstaller** quando disponível; fallback documentado “Developer-like path” para smoke local.

Para CI Linux/WSL: **não** gera o exe real; testes usam binário fake (`sleep` / script).

**Rationale**: PyAudioWPatch/WASAPI não rodam no WSL; P10 exige testes sem hardware. O artefato real é validação Windows (docs/validation).

**Alternatives considered**:
- Embed CPython completo no instalador — pesado; deferido se one-file falhar em dependências nativas.
- Distribuir só wheel — não atende “sem Python no PATH” para usuário final.

## Decision 4 — Health e versão

**Decision**:
- **Versão**: executar `<bin> --version` (já existe no CLI do agent) com timeout curto; parse da string; se falhar → `version: null` / unknown.
- **Health (gerenciado)**: processo ainda vivo (`try_wait` / sysinfo); se saiu → unhealthy + limpar handle.
- **Health (Guided)**: `running` por enumeração; sem probe de microfone.

**Rationale**: AGENTS.md pede health + versão; probe WASAPI é do agent (`probe`), não do shell.

## Decision 5 — Shutdown coordenado

**Decision**: No evento de saída normal do shell Tauri (`RunEvent::Exit` / drop de AppState), chamar `stop` em todo `ManagedAgentProcess`. **Não** matar processos detectados só por nome (Guided).

**Rationale**: Spec Assumptions — mudança consciente vs 014 para evitar captura órfã do sidecar de produto. Externos continuam soberanos.

**Alternatives considered**:
- Nunca matar (014 soft default) — rejeitado para sidecar de produto.
- Matar qualquer `assistant-hub-audio` — rejeitado (pode matar sessão de debug do operador).

## Decision 6 — Superfície de status (contrato shell)

**Decision**: Estender `AgentStatus` (camelCase) com:
- `binaryPath: string | null`
- `binarySource: "sidecar" | "config" | "path" | "missing"`
- `agentVersion: string | null`
- `healthy: boolean` (false se !running; true se running com handle vivo ou Guided running)

**Rationale**: SC-002/SC-005 exigem observabilidade; frontend já consome `AgentStatus`.

## Decision 7 — Escopo único de sidecar

**Decision**: Somente `assistant-hub-audio`. STT, session-core e provider-gateway ficam de fora (FR-010).

**Rationale**: Fatia vertical entregável; 002 lista vários sidecars — um por vez.
