# Implementation Plan: STT UI — sessionId e profile no header do Streaming Foundation

**Branch**: `feature/issue-51-stt-ui-exibir-sessionid-e-profile-no-header-do-s` | **Date**: 2026-07-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/022-issue-51-stt-ui-header/spec.md` (clarify 2026-07-25: primary=most recent, URL base included, profile note without v2, feed-only observation)

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Exibir no **header** do dashboard STT «Assistant Hub AI · Streaming Foundation» o **sessionId** em uso (completo e copiável), **profile** quando já conhecido (senão nota de origem no agent), e a **URL base** do STT — sem poluir cards de canal, sem alterar transcript-event.v2 e sem auto-alinhar agent. Fonte do sessionId: eventos do feed `/ws/transcripts` já consumidos pela página. Multi-session: primário = mais recentemente observado; Copiar = primário.

Detalhes: [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/stt-dashboard-header.md](./contracts/stt-dashboard-header.md) · [quickstart.md](./quickstart.md).

## Technical Context

**Language/Version**: HTML/CSS/JS vanilla no dashboard estático; Python 3 + FastAPI (serviço existente que serve `index.html`). Sem TypeScript, sem Tauri nesta fatia.

**Primary Dependencies**: `services/transcription-service/app/static/index.html` (UI); `app/main.py` (FileResponse do index — sem mudança de API esperada). Sem schema transcript v2, sem desktop-shell.

**Storage**: Estado só em memória no browser (Set/lista de sessionIds observados + primário). Sem persistência.

**Testing**: pytest no WSL: estrutura do HTML (marcadores de contrato UI) + política canônica em `app/header_session_state.py` (observe/primary/multi/vazio). JS no `index.html` **espelha** essa política (analyze U1). Sem GPU/WASAPI (P10). SC-001/SC-004 e clipboard real no quickstart manual.

**Target Platform**: Browser no host apontando para STT (`http://localhost:8001` típico); testes de estrutura no WSL.

**Project Type**: Extensão da UI estática do transcription-service + docs operacionais. Nenhum serviço novo.

**Performance Goals**: Atualização do header no mesmo turno do `onmessage` do feed; layout usável com ids ≥64 caracteres.

**Constraints**: P1/G1 antes de Implement; P5 sessionId ponta a ponta (só **exibir**); P9 sem áudio/tokens no header; P4 — **sem** mudança transcript-event.v2; FR-014 feed-only; FR-007 não poluir cards; FR-005 MAY sem fonte nesta fatia → FR-006 nota.

**Scale/Scope**: Um header + Copiar + nota de profile + URL base (MUST) + docs. **MVP = US1 + US2**. US3 (nota profile) + US4 (URL MUST + docs) na mesma entrega preferida (issue #51 completa).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|-----------|-----------|
| P1 — Spec antes de código | PASS. Spec Clarified + requirements checklist 16/16. G1 humano antes de Implement. |
| P2 — Core independente de fornecedores | PASS. Sem STT/LLM novos; só UI de observação. |
| P3 — WSL-first | PASS. pytest no WSL; agent real só no quickstart Windows. |
| P4 — Contratos versionados | PASS. Sem mudança transcript-event.v2; contrato feature-local de header UI. |
| P5 — Canal/origem | PASS. Exibe sessionId já presente nos eventos; não mistura canais. |
| P6 — Isolamento áudio | PASS. UI não toca captura. |
| P7 — Identidade dispositivo | N/A. |
| P8 — Automação com autorização | PASS. Plano não propõe merge/force-push. |
| P9 — Privacidade | PASS. Só ids operacionais + host; sem transcript/áudio no header. |
| P10 — Qualidade determinística | PASS. Estrutura + estado puro; sem hardware. |

Nenhuma violação → Complexity Tracking vazio.

### Post-design re-check (Phase 1)

Gates permanecem PASS. research/data-model/contracts/quickstart:
- não alteram transcript-event.v2;
- profile = nota (FR-006); FR-005 MAY sem fonte;
- primário = mais recente + multi por contagem;
- URL base = origin MUST;
- docs US4.

### Pós-analyze remediação (2026-07-25)

- **I1**: Key Entities / defaults — URL base MUST (não «opcional»).
- **I2**: MVP wording — URL MUST in-scope; MVP código = US1+US2; entrega completa + US3+US4.
- **U1**: Fonte da verdade da política = `header_session_state.py`; JS espelha.
- **U2**: FR-005 MAY sem fonte misteriosa; padrão FR-006 nota.
- **D1**: FR-015 unificado em FR-004 (ID reservado).
- **A1**: reconnect WS não limpa observed; reload limpa.
- **A2**: multi = contagem «N sessões» (+ lista compacta opcional).
- **C1/C2**: SC-001/SC-004 manuais; path parity via pipeline 001.

## Project Structure

### Documentation (this feature)

```text
specs/022-issue-51-stt-ui-header/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── stt-dashboard-header.md
├── checklists/
│   ├── requirements.md
│   └── stt-header.md
├── spec.md
└── tasks.md
```

### Source Code (repository root) — arquivos prováveis

```text
services/transcription-service/
├── app/
│   ├── header_session_state.py   # política canônica (observe/primary/multi) — testada
│   ├── static/
│   │   └── index.html            # header UI; JS espelha política canônica
│   └── main.py                   # serve index (sem mudança de rota esperada)
└── tests/
    └── test_stt_dashboard_header.py   # estrutura + política canônica

docs/development/running.md
docs/release/min-flow.md
```

**Structure Decision**: Dashboard estático do transcription-service + docs. **Política canônica** em Python (`header_session_state.py`); `index.html` implementa UI e **espelha** as regras no `onmessage` (comentário de contrato). Sem desktop-shell, sem schema novo.

## Complexity Tracking

> Nenhuma violação de constituição a justificar.
