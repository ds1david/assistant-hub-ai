# Implementation Plan: Assistente de respostas automáticas no desktop (live-answer)

**Branch**: `019-auto-answer-assistant` | **Date**: 2026-07-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/019-auto-answer-assistant/spec.md` (clarify 2026-07-25, 5 decisões)

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

O shell desktop passa a **mostrar e orquestrar respostas automáticas** a partir de trechos **finais** do transcript reconhecidos como pergunta, usando a rota de política **`live-answer`** do AI Provider Hub já existente. O operador controla automático, **origens de canal** (default só `system`), **modo de entrada** (só pergunta vs contexto recente) e resolve **conflitos** (cancelar resposta anterior vs aguardar) quando uma nova pergunta chega durante geração. Preferências ficam **por sessão** em storage local do shell. O session-core ganha apenas **`GET /api/sessions`** (aditivo) para listar sessões; criação/seleção e o painel Assistente ficam no desktop. Orquestração e UI no TypeScript do shell; invoke sem `channelId` nesta fatia.

Detalhes: [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/auto-answer-shell.md](./contracts/auto-answer-shell.md) · [quickstart.md](./quickstart.md).

## Technical Context

**Language/Version**: Java 21 (session-core / Maven); TypeScript 5 + Vite (webview); Rust (Tauri 2 lib + comandos, mesmo padrão de `specs/014` / `015`).

**Primary Dependencies**: Spring Web (session-core); `reqwest` blocking no Rust; `@tauri-apps/api` no TS. Reuso de `invoke` do hub (015/017). Sem SDK de LLM novo (P2).

**Storage**: Memory Hub SQLite já lista sessões internamente (`findAllSessions`) — expor via API. Preferências do Assistente: JSON local no app config dir do shell (mapa por `sessionId`), via módulo Rust `assistant_prefs` + comandos Tauri load/save consumidos pelo webview (**obrigatório** — FR-025). Sem tabela nova de “answers”.

**Testing**: JUnit 5 no session-core (list sessions). Vitest + jsdom no shell (heurística, controller cancel/wait, prefs isolation, painel). `cargo test` no cliente de list/create session. Sem GPU/WASAPI na suíte padrão (P10).

**Target Platform**: session-core em WSL/Docker; shell validado em Windows com WebView2; lib Rust testável no WSL.

**Project Type**: Extensão de `services/session-core` + `apps/desktop-shell` (nenhum serviço novo).

**Performance Goals**: Orquestração local desprezível frente a `timeoutMs` do provedor; janela de contexto ≤ 12 finais / 4000 chars; UI de conflito imediata ao detectar 2ª pergunta.

**Constraints**: P1/G1 antes de implement oficial; P5 origens canônicas; P9 sem logar output/segredos; uma geração ativa; sem auto-selecionar sessão em silêncio; protótipo exploratório deve ser alinhado ou substituído.

**Scale/Scope**: 1 endpoint GET novo; prefs store no shell (**load + save on change**, por `sessionId`); painel Assistente + seletor de sessão; controller de auto-answer; testes associados. **MVP de produto = US1 + US2** (resposta automática + conflito cancelar/aguardar). Create session defaults (FR-028): `title=Sessão local`, `profileId=interview-technical`. Turns na UI (FR-029): **mais recente primeiro**. Sessão ativa sempre por escolha explícita (curl, botão mínimo ou picker — **sem** auto-select silencioso). Fora: TTS, chat multi-turno completo, motor de sugestões no servidor, abort HTTP obrigatório.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|-----------|-----------|
| P1 — Spec antes de código | PASS. Spec + 5 clarificações + checklist 16/16. Protótipo pré-spec existe e será reconciliado no implement sob G2 — não substitui esta planilha. G1 humano antes de Implement. |
| P2 — Core independente de fornecedores | PASS. Só reutiliza adaptadores/rota do hub; shell não importa SDK de LLM. |
| P3 — WSL-first | PASS. Java/Maven/vitest/cargo test lib no WSL; WASAPI só no E2E Windows opcional. |
| P4 — Contratos versionados | PASS. `GET /api/sessions` aditivo; sem mudança de schema transcript/provedores; contrato feature-local documentado. |
| P5 — Canal/origem | PASS. Filtro por `sourceType` canônico no disparo; invoke sem channelId ⇒ origem N/A no resultado (coerente com #40). |
| P6 — Isolamento áudio | N/A. |
| P7 — Identidade dispositivo | N/A. |
| P8 — Automação com autorização | PASS. Plano não propõe merge/force-push automático. |
| P9 — Privacidade | PASS. Prefs sem segredo; invoke logs existentes sem output; UI escapa HTML. |
| P10 — Qualidade determinística | PASS. Vitest/JUnit sem rede real obrigatória; E2E com provedor real é manual/tag. |

Nenhuma violação → Complexity Tracking vazio.

### Post-design re-check (Phase 1)

Gates permanecem PASS. research/data-model/contracts/quickstart:
- não introduzem SDK de provedor;
- listagem aditiva de sessões;
- prefs locais por sessão (**persistência on change** — pós-analyze C1); módulo Rust `assistant_prefs` **obrigatório** (analyze A3);
- orquestração no shell com conflito explícito (**MVP inclui US2** — pós-analyze C2);
- limites de contexto e defaults do clarify documentados; heurística FR-004 canônica (analyze A1);
- create session e ordem de turns fixados em FR-028/FR-029 (C5/C6 / A2);
- FR-018 cobre reabertura de conflito FR-010 (A5).

## Project Structure

### Documentation (this feature)

```text
specs/019-auto-answer-assistant/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── auto-answer-shell.md
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md                 # /speckit-tasks (não criado por /speckit-plan)
```

### Source Code (repository root) — arquivos prováveis

```text
services/session-core/src/main/java/ai/assistanthub/core/session/
├── SessionRepository.java          # + list()/listSessions()
├── SessionController.java          # + GET /api/sessions
└── ...

services/session-core/src/test/java/ai/assistanthub/core/session/
└── SessionListApiTest.java         # (ou equivalente)

apps/desktop-shell/src-tauri/src/
├── session_core_client.rs          # + list_sessions, create_session (se ainda incompleto)
├── assistant_prefs.rs              # load/save JSON por sessionId (obrigatório — FR-025)
├── config.rs                       # ou módulo irmão de prefs
├── lib.rs
└── main.rs                         # + list_sessions, create_session, prefs commands se necessário

apps/desktop-shell/src/
├── assistant-auto.ts               # orquestração pura (heurística, conflito, input builder)
├── assistant-panel.ts              # render + callbacks (origens, modo, conflito, turns)
├── session-picker.ts               # lista / criar / selecionar / id ativo (ou integrar session-status)
├── assistant-prefs.ts              # tipos + defaults (se FS só no Rust, thin wrapper invoke)
├── api-client.ts                   # listSessions, createSession, invoke…
├── main.ts                         # bootstrap: sessão escolhida, poll feed → ingest, paint
└── ...

apps/desktop-shell/tests/
├── assistant-auto.test.ts
├── assistant-panel.test.ts
├── session-picker.test.ts
└── assistant-prefs.test.ts
```

**Structure Decision**: Estender session-core (list) + desktop-shell (UI + orquestração + prefs). Nenhum crate/serviço novo. Protótipo `assistant-*.ts` existente é ponto de partida sob reconciliação (research Decisão 7).

## Complexity Tracking

> Nenhum desvio constitucional a justificar.
