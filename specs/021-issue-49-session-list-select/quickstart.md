# Quickstart validation: session list select & agent sessionId

**Feature**: `specs/021-issue-49-session-list-select`  
**Date**: 2026-07-25

Validação determinística no WSL + roteiro manual Windows. Contratos: [session-picker-shell.md](./contracts/session-picker-shell.md). Modelo: [data-model.md](./data-model.md). Alinhamento agent: reutiliza [020 quickstart](../020-issue-47-sessionid-align/quickstart.md).

## Prerequisites

- Repo em WSL: `/home/david/workspace/assistant-hub-ai`
- Node + npm para vitest do shell
- (Manual Windows) stack STT + session-core + shell + agent conforme `docs/development/running.md`

## Automated (WSL) — gate padrão

```bash
cd /home/david/workspace/assistant-hub-ai/apps/desktop-shell
npx vitest run
# focar seletor + agent:
npx vitest run tests/session-picker.test.ts tests/session-selection.test.ts tests/agent-session-actions.test.ts tests/agent-panel.test.ts tests/session-alignment.test.ts
```

### Expected coverage (post-implement)

| Area | Checks |
|------|--------|
| Select 1 item | click `session-item` → callback com id completo; com active setado, `session-active-id` contém UUID completo (FR-013a / SC-001) |
| Create → active | fluxo create success seta active = created.id (FR-013b / SC-002) |
| Refresh preserve | reconcile: id ainda na lista → active inalterado (FR-013c / SC-003) |
| Refresh orphan | reconcile: id ausente → `null` (FR-013d / SC-003) |
| No auto-select | list non-empty + active null → permanece null |
| Select ≠ agent restart | `onSessionSelected` não recebe/chama stop/start (020/021) |
| Start usa active | fake start recebe `activeSessionId` (FR-013e / SC-004) — regressão 020 |
| Guidance usa active | comando / `agent-guidance` contém `--session <active>` (021 FR-012) |
| Mismatch fakes | ids divergentes → banner (FR-013f / SC-005) — regressão 020 |

## Manual Windows — seleção + agent

1. Subir STT + session-core (`./scripts/wsl/start-assistant-hub.sh --no-build` ou fluxo documentado).
2. Abrir shell desktop.
3. Com lista **com itens** e estado «Nenhuma sessão selecionada», **clicar** um item → «Sessão ativa: \<uuid completo\>»; Assistente deixa de exigir só seleção.
4. Clicar **Atualizar lista** → mesma sessão permanece ativa.
5. **Criar sessão** → nova sessão fica ativa sem segundo clique.
6. **Iniciar agent pela UI** → agent usa o **mesmo** UUID (não `session-YYYYMMDD-…`); sem mismatch se só esse processo.
7. (Opcional) Iniciar agent no PowerShell com `--session session-2026…` e sessão UI UUID → mismatch banner; list-sessions **não** ganha o id `session-2026…` sozinho.
8. Conferir docs: list-sessions = core; mesmo sessionId; select ≠ reconfig agent.

### Pass criteria (manual)

- [ ] Select gruda active com id completo  
- [ ] Create → active automático  
- [ ] Refresh preserva; orphan limpa  
- [ ] Start UI usa UUID da sessão ativa  
- [ ] Id só STT não aparece na lista  
- [ ] Docs `running.md` / `min-flow.md` cobrem list-sessions vs agent path id  

## Failure diagnosis

| Symptom | Check |
|---------|--------|
| Lista com itens, active permanece «Nenhuma» após clique | Listener `onSelect` / `selectSession` / re-paint sobrescrevendo active; testid `session-item` e `data-session-id` |
| Active some após Atualizar | Bug em reconcile (deve preservar se id ∈ lista) |
| Active órfão após sessão apagada no core | Deve ir a null no refresh OK |
| Agent com session-YYYYMMDD, feed vazio | Mismatch 020; reiniciar agent com UUID da UI |
| Esperava id do agent na lista | Fora de escopo — criar sessão no core e usar esse id |

## Out of scope for this quickstart

- GPU Whisper quality  
- Import de ids STT no session-core  
- Persistência de active entre restarts do shell  
