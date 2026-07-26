# Implementation Plan: R5 — Audio Agent como sidecar supervisionado

**Branch**: `025-r5-audio-agent-sidecar` | **Date**: 2026-07-26 | **Spec**: [spec.md](./spec.md)

## Summary

Evoluir o shell desktop (`apps/desktop-shell`) para resolver e supervisionar o binário `assistant-hub-audio` como **sidecar de produto**: priorizar binário empacotado, expor origem/versão/saúde no `AgentStatus`, e encerrar processos **gerenciados** no shutdown do shell. Preservar modo Developer (PATH/venv) e modo Guided (processo externo intocado). Não empacotar STT, JVM nem provider-gateway.

## Technical Context

**Language/Version**: Rust (Tauri 2 lib `desktop_shell`) + TypeScript webview; script PowerShell de packaging no Windows.

**Primary Dependencies**: Tauri 2 `externalBin`; `sysinfo` (já usado); CLI agent `--version` existente.

**Storage**: Extensão aditiva opcional `audioAgentBin` em `shell-config.json`; env `ASSISTANT_HUB_AUDIO_BIN`.

**Testing**: `cargo test` com binários fake (`sleep`/scripts); sem WASAPI/GPU (P10). Validação manual Windows em `docs/validation/`.

**Target Platform**: Windows 10/11 para sidecar real; lógica e testes no WSL.

**Project Type**: Evolução de `apps/desktop-shell` + docs/scripts; sem mudança de contratos transcript/session-core.

**Constraints**: P3/P6/P10; FR-010/011; alinhamento sessionId (020); não matar Guided.

## Constitution Check

| Princípio | Avaliação |
|-----------|-----------|
| P1 Spec first | PASS — spec + checklist |
| P2 Vendor-agnostic | PASS — sem SDK de IA |
| P3 WSL-first | PASS — packaging Windows; testes WSL |
| P4 Contracts | PASS — contrato shell aditivo documentado; sem schema JSON de domínio |
| P5 Channel identity | N/A direto — agent preserva canais |
| P6 Endpoint isolation | PASS — shell não toca WASAPI |
| P7 Device identity | N/A |
| P8 Automation auth | PASS — sem merge automático |
| P9 Privacy | PASS — não logar áudio/tokens |
| P10 Deterministic quality | PASS — fakes + docs validation |

## Project Structure

```text
specs/025-r5-audio-agent-sidecar/
  spec.md plan.md research.md data-model.md quickstart.md tasks.md
  contracts/agent-sidecar-shell.md
  checklists/requirements.md

apps/desktop-shell/src-tauri/
  src/agent_control.rs      # estender status + shutdown
  src/sidecar.rs            # resolve + version probe (novo)
  src/config.rs             # audioAgentBin opcional
  src/main.rs               # wire resolve; Exit stop managed
  binaries/.gitkeep         # placeholder externalBin
  tauri.conf.json           # externalBin
  tests/sidecar_tests.rs

apps/desktop-shell/src/
  api-client.ts             # AgentStatus fields
  agent-panel.ts            # exibir source/version/healthy

scripts/windows/build-audio-agent-sidecar.ps1
docs/desktop-shell/packaging.md   # § sidecar
docs/validation/r5-audio-agent-sidecar.md  # template
```

## Implementation Phases (plan)

0. Research — done (`research.md`)
1. Design — data-model, contracts, quickstart
2. Tasks — `tasks.md`
3. Implement — resolver, status, shutdown, UI, docs, tests
4. Manual Windows — residual

## Complexity Tracking

Nenhuma violação constitucional. Mudança de default de shutdown vs 014 documentada em Assumptions da spec.
