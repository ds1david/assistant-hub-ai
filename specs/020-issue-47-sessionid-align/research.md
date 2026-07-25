# Research: Alinhar sessionId UI↔agent e estados vazios do Assistente

**Feature**: `specs/020-issue-47-sessionid-align`  
**Date**: 2026-07-25

## Decision 1 — Onde resolver a sessão do agent

**Decision**: Resolver no **lado Rust** (`agent_control` + `get_agent_status` / `start_agent`) e expor no `AgentStatus` para o webview. Comparação visual e CTA de restart no TypeScript.

**Rationale**:
- `sysinfo::Process::cmd()` já está disponível (crate `sysinfo` 0.32 no shell); o agent não expõe health/API (014 research Decisão 5).
- Start gerenciado já grava handle em `AppState.managed_agent` — basta guardar o `session_id` do último start bem-sucedido no mesmo estado.
- Testes de parse/prioridade em `cargo test` sem GUI.

**Alternatives considered**:
- Só no frontend (assumir id do último start que o TS pediu) — falha no caso real da issue #47 (agent iniciado no PowerShell com outro id).
- Pedir API de status ao agent Python — fora de escopo (sem mudança no agent).

## Decision 2 — Prioridade de resolução (clarify Q1)

**Decision**: `agentSessionId` resolvido por:

1. Valor após `--session` na **linha de comando** do processo `assistant-hub-audio` em execução (se legível e não vazio);
2. Senão, `last_managed_session_id` do shell (último `start_agent` bem-sucedido ainda associado ao handle / enquanto Direct);
3. Senão, **desconhecida** (`null`).

Comparação com sessão ativa da UI: **igualdade exata de string**.

**Rationale**: Atende mismatch quando o operador rodou o agent manualmente; mantém fallback para processo spawnado pelo shell se cmdline falhar.

**Alternatives considered**:
- Só managed start — rejeitado no clarify (Q1 = B).
- Nunca mostrar sessão do agent — rejeitado no clarify.

## Decision 3 — Parsing de `--session` na cmdline

**Decision**: Função pura `parse_session_from_cmd(args: &[OsString]) -> Option<String>`:

- Percorre args; se um arg é `--session` (case-sensitive, forma longa usada pelo agent), o **próximo** arg não vazio é o id;
- Também aceita forma `--session=<id>` se aparecer (defensivo; o agent atual usa forma separada);
- Ignora outros flags; se múltiplos `--session`, **último** vence (defensivo);
- Sem inventar id se ausente/ilegível.

Detecção de processo agent: reutilizar `process_matches_agent` existente; entre matches, preferir o primeiro com `--session` parseável; se nenhum, fallback managed/unknown.

**Rationale**: CLI documentada em AGENTS.md / guidance_command: `assistant-hub-audio run --session <id> --profile <path>`. Determinístico e testável com vetores de `OsString`.

**Alternatives considered**:
- Regex na string unida — frágil com espaços em paths de profile.
- Ler só argv[0] — insuficiente.

## Decision 4 — Sem force-kill de agent externo (clarify Q2)

**Decision**: Manter `ControlMode::Guided` quando não há handle gerenciado. `stop_agent` continua falhando se não há handle (mensagem atual). UI mostra: mismatch (se session conhecida via cmdline) + comando guiado com **sessão ativa** + texto de parada **manual**. `start` continua com `AlreadyRunning` se processo existe — sem matar o externo para liberar.

**Rationale**: Clarify Q2 opção A; evita matar processo errado; alinhado a 014.

**Alternatives considered**:
- Kill por nome de processo — rejeitado no clarify (risco e P6/ops).
- Só docs sem CTA/orientação — rejeitado (UX da issue).

## Decision 5 — Restart Direct sem confirm (clarify Q4–Q5)

**Decision**:

- Select de sessão: **nunca** reinicia o agent (FR-009).
- Com mismatch + Direct: banner + CTA **Reiniciar agent com sessão ativa**.
- CTA = `stop_agent` + `start_agent(activeSessionId, profile)` **sem** diálogo de confirmação.
- Profile path: manter `DEFAULT_PROFILE_PATH` existente (`perfil.yaml`) nesta fatia (sem UI de perfil).

**Rationale**: Clarify Q4=B, Q5=A; reutiliza comandos Tauri; um clique realinha.

**Alternatives considered**:
- Auto-restart no select — rejeitado (surpreende captura).
- Confirm dialog — rejeitado no clarify.

## Decision 6 — Superfície UI de alinhamento

**Decision**:

| Elemento | Onde |
|----------|------|
| Sessão ativa (UI) | Já no session-picker (`session-active-id`); reforçar no painel agent se útil |
| Sessão do agent | Painel agent (`data-testid` dedicado) ou “desconhecida” / “parado” |
| Banner mismatch | Painel agent (e opcionalmente eco no Assistente como prioridade de diagnóstico) |
| CTA restart | Painel agent, visível quando `running && Direct && mismatch` |
| Guidance | Sempre com `--session <activeSessionId>` quando há sessão ativa (preenchido no paint do webview se Rust vier vazio) |
| **controlMode (analyze I1)** | `!running` → **Direct** (Start disponível na UI). `running && has_handle` → Direct. `running && !has_handle` → Guided. Nunca `Guided` só porque o processo está parado. |

Estado de alinhamento (puro TS): `aligned | mismatched | agent_stopped | agent_session_unknown | no_active_session`.

**Rationale**: Spec US1–US2; testável sem Tauri real no vitest (status fake + callbacks). Corrige bug pré-existente em que `get_agent_status` com agent parado e sem handle reportava Guided e escondia o botão Iniciar.

## Decision 6b — Empty kinds: feed vazio vs aguardando final (analyze I4)

**Decision**: `awaiting_transcript` = zero entradas no feed. `awaiting_final` = ≥1 Partial e nenhum Final elegível. Nunca mapear feed vazio para `awaiting_final`.

**Rationale**: Alinha FR-010 itens 3–4; evita diagnóstico falso de “só partials” quando não há transcript.

## Decision 7 — Estados vazios do Assistente (clarify Q3)

**Decision**: Função pura `resolveAssistantEmptyKind(...)` (ou equivalente) com precedência:

1. `session_mismatch` — mismatch conhecido (ids ambos conhecidos e ≠)
2. `prefs_auto_off` / `prefs_no_origin` — automático off ou nenhuma origem
3. `awaiting_transcript` — feed vazio
4. `awaiting_final` — há ao menos um Partial (e nenhum Final novo elegível relevante); auto apto
5. `no_eligible_question` — há Final(s) mas nenhum elegível como pergunta+origem

Só aplica empty kind quando `turns.length === 0`. Copy em PT, estável o suficiente para assert de `data-testid` / substring.

**Rationale**: Clarify Q3=B; não muda 019 FR-003 (só Final dispara).

**Alternatives considered**:
- Um único “Nenhuma interação ainda” — rejeitado (não diagnostica issue #47).
- Sempre “aguardando final” com auto on — rejeitado (falso em feed vazio).

## Decision 8 — Validação de finais no pipeline real

**Decision**: Não redesenhar STT. No quickstart / docs: checklist manual Windows — com ids alinhados, confirmar se chegam `transcript.final.v2` no feed do shell; se só partials, empty state `awaiting_final` + nota em running. Fixture vitest com Final sintético garante orquestração (regressão 019).

**Rationale**: Spec Assumptions; issue #47 P1 “confirmar ou documentar”.

## Decision 9 — Documentação

**Decision**: Atualizar `docs/development/running.md` e `docs/release/min-flow.md`:

- Mesmo `sessionId` entre UI, agent e STT;
- Selecionar na lista **não** reconfigura agent em execução;
- Preferir Iniciar/Reiniciar pela UI (Direct);
- Exemplo PowerShell/`run-audio-agent-foreground.ps1` com UUID da sessão ativa;
- Nota Guided: parada manual + comando com id da UI.

**Rationale**: US4 / FR-012; trecho live-answer em running.md já pede mesmo id — reforçar e explicitar armadilha do select.

## Decision 10 — Escopo negativo técnico

**Decision**: Fora desta fatia:

- Mudanças em `agents/windows-audio-agent` ou contratos transcript;
- Endpoints novos no session-core;
- Multi-agent / force-kill;
- UI de escolha de profile path;
- Abort HTTP / mudanças na rota `live-answer`.

**Rationale**: Spec Out of Scope + foco no desalinhamento operacional.
