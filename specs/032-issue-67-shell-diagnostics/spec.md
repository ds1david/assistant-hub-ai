# Feature Specification: Shell diagnostics panel (#67)

**Branch**: `feature/issue-67-shell-diagnostics`  
**Issue**: [#67](https://github.com/ds1david/assistant-hub-ai/issues/67)  
**Epic**: [#63](https://github.com/ds1david/assistant-hub-ai/issues/63)  
**Created**: 2026-07-26  
**Status**: Implemented (P0)

## Objective

Painel unificado no desktop-shell: session-core, STT `/health`, agent/sidecar, URL base, próximos passos e copiar relatório redigido (sem secrets/transcript).

## FR

- FR-001: Seção Diagnóstico com checks UP/DOWN/UNKNOWN
- FR-002: session-core health + STT health (default :8001) + agent binary/source/version
- FR-003: Relatório copiável sem secrets, chaves, texto de transcript
- FR-004: Sugestões de próximo passo por check DOWN
- FR-005: Testes unitários do builder de relatório (sem Tauri)

## Out of scope (P1)

Lista de devices de áudio, deep-link docs, auto-fix drivers.
