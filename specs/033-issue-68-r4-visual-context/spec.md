# Feature Specification: R4 Visual Context (frame + OCR + sessão)

**Feature Branch**: `feature/issue-68-r4-visual-context`  
**GitHub Issue**: [#68](https://github.com/ds1david/assistant-hub-ai/issues/68)  
**Epic**: [#63](https://github.com/ds1david/assistant-hub-ai/issues/63)  
**Created**: 2026-07-26  
**Status**: Implemented (P0 foundation)

## Objetivo

Captura de contexto visual **com consentimento**, OCR/descrição, evento versionado ligado à sessão, mascaramento PII básico e UI mínima no shell. Sem gravação silenciosa, sem face ID.

## User Stories

### US1 — Consentimento + registrar frame (P1)
Operador ativa consentimento e registra um frame (stub/fixture ou captura futura). Sem consentimento, API rejeita.

### US2 — OCR + máscara PII (P1)
Texto OCR passa por mascaramento (email, telefone, cartão-like) antes de persistir.

### US3 — Listar frames da sessão (P2)
Shell e API listam frames da sessão ativa (metadados + ocrText mascarado).

## Requirements

- **FR-001**: Contrato `visual-frame-event.v1` versionado em `contracts/`.
- **FR-002**: `POST /api/sessions/{id}/visual-frames` exige `consent=true`; cria HubEvent `visual.frame.v1`.
- **FR-003**: OCR via interface pluggable; default **fake** (texto injetado ou fixture) — sem GPU.
- **FR-004**: PII mask determinístico em ocrText antes de persistir.
- **FR-005**: `GET /api/sessions/{id}/visual-frames` lista frames da sessão.
- **FR-006**: Shell painel Visual: toggle consentimento, registrar frame (texto/OCR stub), listar.
- **FR-007**: Logs MUST NOT incluir ocrText completo nem bytes de imagem (P9).
- **FR-008**: Testes JUnit + Vitest com fixtures, sem hardware.

## Out of scope (P1+)

Captura DXGI real, Tesseract nativo, timeline rica, face recognition, remote OCR default.
