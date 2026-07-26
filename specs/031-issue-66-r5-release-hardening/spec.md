# Feature Specification: R5 Release hardening (checksums, CI packaging, install validation)

**Feature Branch**: `feature/issue-66-r5-release-hardening`  
**GitHub Issue**: [#66](https://github.com/ds1david/assistant-hub-ai/issues/66)  
**Epic**: [#63](https://github.com/ds1david/assistant-hub-ai/issues/63)  
**Created**: 2026-07-26  
**Status**: Implemented (process/docs/CI)

## Objective

Artefatos de desktop reproduzíveis com **SHA-256**, workflow CI Windows de packaging (ou runbook local), docs de **code signing** sem commitar certificados, e checklist de install/upgrade/uninstall.

## Requirements

- **FR-001**: Script de checksums (`SHA256SUMS` ou equivalente) para artefatos de bundle.
- **FR-002**: Workflow GitHub Actions Windows (`workflow_dispatch` e/ou tags) que tenta `tauri build` e publica artifacts + checksums; falha de assinatura real não bloqueia se cert ausente.
- **FR-003**: Runbook PowerShell local de release no host Windows.
- **FR-004**: Documentação de preparação para assinatura (sem secrets no repo).
- **FR-005**: Checklist de validação install/upgrade/uninstall/rollback em `docs/validation/`.
- **FR-006**: Stub documentado do sidecar quando o agent real não estiver no CI (empacotamento).

## Out of scope

- Microsoft Store, auto-update end-to-end, tray icon, certs reais no CI.
