# Research: STT UI — sessionId e profile no header

**Feature**: `specs/022-issue-51-stt-ui-header`  
**Date**: 2026-07-25

## Decision 1 — Superfície e arquivo

**Decision**: Alterar apenas `services/transcription-service/app/static/index.html` (markup + CSS + script do header). `main.py` já serve o index via `FileResponse`; não criar SPA nem mexer no desktop-shell.

**Rationale**: Issue #51 mira o dashboard «Streaming Foundation»; a página já consome `/ws/transcripts` e acumula `sessionId` num `Set` sem exibir.

**Alternatives considered**:
- Painel no desktop-shell — fora do escopo (020/021 já cobrem shell).
- Framework UI — overkill para página estática.

## Decision 2 — Fonte do sessionId

**Decision**: Observar **somente** `data.sessionId` nos eventos do WebSocket de transcripts (FR-014). Não ler path de áudio, query string nem inventar id.

**Rationale**: Clarify; o feed já carrega o id alinhado à captura; métricas já usam o mesmo `Set`.

**Alternatives considered**:
- Inferir de `/ws/audio/{sessionId}/...` no browser — a UI de transcript não abre esse path.
- Query param `?session=` — inventaria UX e fora da issue.

## Decision 3 — Primário em multi-session

**Decision**: Manter conjunto ordenado por primeira observação **e** ponteiro `primarySessionId` = **último** sessionId visto no feed. Header destaca o primário; indica contagem/lista se `size > 1`. **Copiar** copia só o primário.

**Rationale**: Clarify FR-010; fluxo típico é um id; multi é edge case operacional.

**Alternatives considered**:
- Só o primeiro id — esconde troca de sessão.
- Copiar lista inteira — confuso para colar no `--session`.

## Decision 4 — Profile sem contrato novo (analyze U2)

**Decision**: Nesta fatia, **não** estender transcript-event.v2 e **não** ler query string. **Fonte de profile = nenhuma.** UI **sempre** mostra a **nota** FR-006 («profile definido no agent / `--profile`»). FR-005 MAY só se, no futuro, um valor já existir na página sem schema — **não** implementar busca de fonte misteriosa agora.

**Rationale**: Clarify + analyze U2; evita aceite ambíguo e schema sneak.

**Alternatives considered**:
- ADR + campo opcional no evento — fora de escopo.
- `?profile=` na URL — rejeitado (inventa canal paralelo ao feed).

## Decision 5 — URL base

**Decision**: Exibir `location.origin` (ou equivalente) no header (FR-011 MUST após clarify). Sem path sensível, sem token.

**Rationale**: Operador confirma host:porta do STT (ex. `http://localhost:8001`).

**Alternatives considered**:
- Omitir (MAY da issue) — clarify optou por incluir (custo baixo).

## Decision 6 — Copiar e feedback

**Decision**: Botão/controle **Copiar** no header; `navigator.clipboard.writeText(primary)` quando disponível; fallback: falha legível + id selecionável. Feedback textual no controle (~2s «copiado» / «falha ao copiar»). Desabilitado ou oculto sem primário.

**Rationale**: FR-003/004/015; SC-002.

**Alternatives considered**:
- Só `document.execCommand('copy')` — fallback opcional se clipboard API falhar.
- Sem feedback — pior UX operacional.

## Decision 7 — Layout e cards

**Decision**: Header flex com título | meta (session + profile note + origin) | status. CSS para ids longos (`overflow-wrap` / `word-break` / mono). **Não** adicionar sessionId/profile em `ensureChannel` / cards.

**Rationale**: FR-007/008; aceite da issue.

## Decision 8 — Testes e fonte da verdade da política (P10 + analyze U1)

**Decision**:

1. **Canônico**: `app/header_session_state.py` implementa observe / primary / multi / blank-ignore / `copy_enabled`. Pytest cobre 100% dessas regras.
2. **UI**: `static/index.html` JS **espelha** as mesmas regras no handler de transcript (comentário: «espelha header_session_state»). Se divergir, **corrige o JS** para bater no Python (não o contrário, salvo mudança de data-model com testes atualizados).
3. `tests/test_stt_dashboard_header.py`: estrutura (marcadores do contract) + política canônica + asserts de que o script referencia update de header a partir de `sessionId`.
4. Quickstart: SC-001/SC-004 manuais; clipboard real se necessário.

**Rationale**: Um lugar testável sem Node; evita drift silencioso (analyze U1).

**Alternatives considered**:
- Só JS + regex no HTML — frágil para FR-010.
- Playwright E2E — pesado e flaky para G2.

## Decision 9 — Docs

**Decision**: Parágrafos curtos em `docs/development/running.md` e/ou `docs/release/min-flow.md`: header mostra sessionId; Copiar; alinhar com `--session` do agent e sessão do shell; profile no agent.

**Rationale**: FR-012 / US4 / SC-006.
