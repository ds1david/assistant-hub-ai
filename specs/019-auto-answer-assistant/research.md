# Research: Assistente de respostas automáticas no desktop (live-answer)

**Feature**: `specs/019-auto-answer-assistant`  
**Date**: 2026-07-25

## Decision 1 — Onde vive a orquestração automática

**Decision**: Orquestração no **shell desktop** (TypeScript puro + comandos Tauri já existentes para transcript/invoke). O session-core **não** ganha um motor de “auto-answer” que dispara sozinho no servidor.

**Rationale**:
- O conflito cancelar/aguardar e os seletores de origem/modo são UX do operador (visão: sugestões sob controle).
- Reaproveita `POST /api/ai-providers/invoke` e o feed de eventos já consumidos pelo shell.
- Testes determinísticos com inject de `invoke` fake e feed sintético (P10), sem GPU/WASAPI.

**Alternatives considered**:
- Motor no session-core com push WebSocket de “suggestion events” — mais correto a longo prazo (R2), mas aumenta superfície, contratos e escopo além do pedido de “ver interação no shell”.
- Polling de um endpoint de sugestões no servidor — duplica estado e ainda exige UI de conflito no cliente.

## Decision 2 — Listagem de sessões

**Decision**: Extensão **aditiva** no session-core: `GET /api/sessions` devolve a lista de sessões conhecidas (cache + rehydrate Memory Hub). Expor `SessionRepository.list()` (ou equivalente) reutilizando `SessionPersistenceStore.findAllSessions()` já existente na rehidratação.

**Rationale**:
- Spec FR-026 exige listar + selecionar + criar; hoje só existem `POST /api/sessions` e `GET /api/sessions/{id}`.
- `findAllSessions()` já existe no store SQLite; falta bridge no repositório e no controller.
- Aditivo, sem mudança de schema de transcript/provedores.

**Alternatives considered**:
- Listar só sessões “vistas” no shell local — incompleto após restart se o core rehydrata do SQLite e o shell não.
- Forçar só “criar sempre” — rejeitado no clarify (opção D).

## Decision 3 — Preferências do Assistente (por sessão)

**Decision**: Persistir no **filesystem do shell** (JSON no diretório de config do app, ao lado de `shell-config.json`), mapa `sessionId → AssistantSessionPreferences`. Não grava no session-core nem no YAML de provedores.

**Rationale**:
- Preferências são de UI/operador (automático, origens, modo de entrada), não de domínio de conversa multi-cliente.
- Evita secrets; arquivo local, sem logar conteúdo de respostas.
- Isolamento S vs T testável com path/temp injetável (SC-010).
- Defaults quando chave ausente: automático off, só `system`, `question-plus-recent-context`.

**Alternatives considered**:
- `metadata` da sessão no core — acopla UI ao backend e exige PATCH de sessão.
- Preferência global do app — rejeitado no clarify Q5.

## Decision 4 — Filtro de origem e heurística de pergunta

**Decision**:
- Origens canônicas apenas: `microphone` | `system` (mesmo vocabulário do transcript / issue #40).
- Default habilitado: `system` apenas.
- Pergunta: trecho `Final` + comprimento **≥ 8** chars (após trim) + (contém `?` **ou** prefixo interrogativo da **lista canônica em FR-004** pt/en). Função pura exportada para testes.

**Rationale**: Alinha P5, defaults do clarify e FR-004/FR-020 (filtro de origem em FR-002). Determinístico para vitest. Lista de prefixos e rejeições: fonte única **FR-004** (não redefinir aqui).

**Alternatives considered**:
- LLM classifica “é pergunta?” — custo, latência, não determinístico (P10).
- Qualquer Final — excesso de disparos.

## Decision 5 — Montagem do pedido (input do invoke)

**Decision**:
- Rota fixa de produto: `live-answer`; capability: `chat`.
- Modo `question-only`: `input` = texto da pergunta candidata.
- Modo `question-plus-recent-context` (default): `input` = bloco estruturado texto simples com (1) janela de trechos **finais** recentes da sessão e (2) a pergunta atual destacada.
- Limites da janela (constantes no módulo de orquestração, cobertos por teste): **até 12** trechos finais **ou** **4000** caracteres de contexto (o que restringir primeiro); ordem cronológica; trechos mais antigos caem fora.
- Invoke **sem** `channelId` nesta fatia (evita 422 de origem quando o operador só quer texto; sourceType no resultado fica N/A — coerente com #40).

**Rationale**: FR-022–024; limites fixos evitam estourar contexto do modelo e mantêm testes estáveis.

**Alternatives considered**:
- Sempre com `channelId` da pergunta — útil para auditoria de origem, mas exige eventos já gravados e pode falhar 422 em corridas; pode ser evolução.
- Transcript completo — rejeitado pelo escopo (não multi-turno completo / risco de payload).

## Decision 6 — Concorrência e cancelamento

**Decision**: No máximo uma geração “ativa” por sessão no controller do shell. Contador de **generation** / id de interação: ao **cancelar**, incrementa generation e marca interação anterior `cancelled`; resultado tardio com generation obsoleto é **descartado** na UI. Abort HTTP real no Tauri é opcional e **não** é gate de aceite (spec Assumptions).

**Rationale**: FR-006–010, SC-002–003; implementável sem mudar session-core.

**Alternatives considered**:
- Fila ilimitada sem diálogo — rejeitado pelo usuário.
- Cancel HTTP no servidor — sem API de cancelamento de invoke hoje.

## Decision 7 — Reconciliação de protótipo

**Decision**: Existe código exploratório (`apps/desktop-shell/src/assistant-auto.ts`, `assistant-panel.ts`, trechos em `main.ts`). O implement **deve** alinhar esse código à spec clarificada (origens, modo de entrada, prefs por sessão, listagem de sessões, defaults) ou substituí-lo; não é aceite “como está”.

**Rationale**: Constituição P1 — spec/plan/tasks mandam; protótipo é input, não fonte de verdade.

## Decision 8 — Superfície de sessão no shell

**Decision**: Painel/controles de sessão no shell: listar, criar com defaults fixos **`title = "Sessão local"`** e **`profileId = "interview-technical"`**, selecionar, exibir id ativo. Agent start continua recebendo o `sessionId` ativo (já previsto no shell).

**Rationale**: US3 / FR-026 / FR-027 / SC-011; defaults fixados no pós-analyze (C5).

## Decision 9 — MVP de produto e persistência de prefs (pós-analyze)

**Decision**:
- **MVP de release** = US1 + US2 (não só US1).
- Prefs: **save em toda mudança de UI** + load na troca de sessão.
- Turns na UI: **mais recente primeiro**; estado `queued` visível.
- Sem sessão ou core down: Assistente não finge automático OK (controles desabilitados + mensagem).

**Rationale**: Findings C1–C6 do `/speckit-analyze`.

## Open items deferred to tasks (not blocking design)

- Persistência do “último sessionId selecionado” entre restarts do app — **fora** desta fatia (FR-026: não restaurar sessão ativa em silêncio); operador sempre escolhe na lista após abrir o app, salvo UX mínima “última usada destacada” sem auto-selecionar (opcional no implement se não violar FR-026).
