# Quickstart: validação — Assistente de respostas automáticas

**Feature**: `specs/019-auto-answer-assistant`  
**Date**: 2026-07-25

Guia de validação (não é o `tasks.md`). Contratos: [contracts/auto-answer-shell.md](./contracts/auto-answer-shell.md). Modelo: [data-model.md](./data-model.md).

## Pré-requisitos

- WSL: monorepo, Java 21/Maven, Node para `apps/desktop-shell`.
- session-core + (opcional) transcription + agent conforme `docs/development/running.md`.
- Pelo menos um provedor na rota `live-answer` com credencial/créditos válidos **para o caminho manual E2E** (OpenAI no sample costuma ser primary).
- Testes automatizados **não** exigem provedor real nem agent (P10).

## 1. Testes automatizados (obrigatório no gate de qualidade)

```bash
# session-core — listagem de sessões + regressão de invoke existente
cd /home/david/workspace/assistant-hub-ai
source "$HOME/.sdkman/bin/sdkman-init.sh" 2>/dev/null
mvn -pl services/session-core test

# desktop-shell — orquestração, painel, prefs por sessão
cd apps/desktop-shell
npx vitest run
npx tsc -b
# Rust (cliente de sessão + prefs se no crate)
cd src-tauri && cargo test
```

**Esperado**: suíte verde; testes novos cobrem no mínimo FR-018 (heurística FR-004, origens, modos de input, cancel/wait, **reabertura de conflito após aguardar** FR-010, prefs S vs T, list sessions client, ordem de turns SC-012).

## 2. API de sessões (sem UI)

```bash
# lista (pode ser vazia no primeiro uso)
curl -sS http://127.0.0.1:8080/api/sessions | python3 -m json.tool

# cria
curl -sS -X POST http://127.0.0.1:8080/api/sessions \
  -H 'Content-Type: application/json' \
  -d '{"title":"validacao-assistente","profileId":"interview-technical"}' \
  | python3 -m json.tool
# anote o id

# lista de novo — id deve aparecer
curl -sS http://127.0.0.1:8080/api/sessions | python3 -m json.tool
```

**Esperado**: `GET` retorna array JSON; `POST` 201 com `id` UUID.

## 3. Invoke manual (sem automático)

Com `SESSION_ID` e rota configurada:

```bash
curl -sS -X POST http://127.0.0.1:8080/api/ai-providers/invoke \
  -H 'Content-Type: application/json' \
  -d "{\"sessionId\":\"$SESSION_ID\",\"route\":\"live-answer\",\"capability\":\"chat\",\"input\":\"Responda em uma frase: o que e um teste unitario?\"}" \
  | python3 -m json.tool
```

**Esperado**: `success: true` e `output` preenchido **ou** erro tipado legível (auth/créditos) sem derrubar o serviço.  
`channelId` omitido ⇒ `sourceType` nulo no resultado (#40).

## 4. Shell — fluxo operador (E2E manual)

1. Suba stack (`./scripts/wsl/start-assistant-hub.sh --no-build` ou equivalente).
2. Abra o desktop shell (`cargo tauri dev --features gui` no Windows, clone em disco Windows).
3. **Lista de sessões**: criar ou selecionar; confirmar id visível (`session-active-id`).
4. Preferências da sessão: automático **off** por default; origens: só sistema; modo: contexto recente.
5. Ligue o automático.
6. Alinhe o agent WASAPI ao **mesmo** `sessionId` e perfil de áudio com canal de sistema.
7. Produza uma pergunta final no canal de sistema (ou injete evento de transcript na sessão via caminho de dev se documentado).
8. Observe painel Assistente: pergunta → gerando → resposta (ou erro).
9. Com geração lenta (provedor lento) ou mock, dispare segunda pergunta e valide diálogo **Cancelar** / **Aguardar**.
10. **Roteiro SC-006 (&lt;1 min)**: sem consultar docs, o operador aponta (a) o painel Assistente como local da resposta automática e (b) as ações Cancelar anterior / Aguardar no conflito.

**Esperado**: SC-001, SC-002, SC-006, SC-011.

## 5. Checks de não-regressão

| Check | Esperado |
|-------|----------|
| Feed de transcript | Continua atualizando se invoke falhar (SC-007) |
| Painel de provedores | Testar conexão ainda funciona |
| Mic com default origens | Pergunta no microfone **não** dispara (SC-008) |
| Troca de sessão S/T | Prefs não vazam (SC-010) |

## 6. Critérios de “quickstart passou”

- [ ] `mvn -pl services/session-core test` verde  
- [ ] `npx vitest run` + `tsc -b` (+ `cargo test` lib) verdes no desktop-shell  
- [ ] `GET /api/sessions` funcional  
- [ ] Invoke `live-answer` responde (sucesso ou erro tipado)  
- [ ] Roteiro manual 4 executado ou justificado se ambiente Windows/agent indisponível (P10: automatizados bastam para CI; E2E manual em `docs/validation/` se feito)
