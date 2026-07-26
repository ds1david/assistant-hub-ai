# Feature Specification: Sessão — seleção na lista e alinhar agent ao sessionId ativo

**Feature Branch**: `feature/issue-49-desktop-sess-o-sele-o-na-lista-alinhar-agent-ao`

**Created**: 2026-07-25

**Status**: Clarified

**Input**: User description: "criar/atualizar specs/00x-issue-49-*/" — GitHub issue #49: [desktop] Sessão: seleção na lista + alinhar agent ao sessionId ativo

**Referências**: Issue [#49](https://github.com/ds1david/assistant-hub-ai/issues/49) · Spec de alinhamento agent/Assistente `specs/020-issue-47-sessionid-align` · Assistente e sessão ativa `specs/019-auto-answer-assistant` (US3, FR de sessão) · Shell desktop `specs/014-issue-35-desktop-tauri-shell-local` · Constituição P1 (spec antes de código), P5 (`sessionId` ponta a ponta), P9 (privacidade), P10 (testes sem GPU/WASAPI real) · Docs `docs/development/running.md` e `docs/release/min-flow.md`

## Clarifications

### Session 2026-07-25 (defaults a partir da issue #49 — sem bloqueio)

- **Problema de seleção**: a lista de sessões do session-core pode mostrar itens (ex. rótulo + UUID), mas a UI permanece em «Nenhuma sessão selecionada». Sem `sessão ativa`, Assistente e ações que dependem de sessão ficam bloqueados.
- **Problema de identidade**: o agent Windows pode ser iniciado com um identificador só de caminho STT no formato `session-YYYYMMDD-HHMMSS`. Esse id **não** aparece sozinho em list-sessions (só sessões do session-core, tipicamente UUID). Transcript e Assistente da sessão da lista não recebem o áudio/transcrição dessa captura.
- **Sessão ativa**: é o identificador de sessão do **session-core** escolhido ou criado na UI; deve ser mostrado por completo (UUID ou id canônico retornado pelo core).
- **Selecionar na lista**: clique (ou controle inequívoco) no item → define sessão ativa; criar sessão → torna-se ativa automaticamente.
- **Atualizar lista**: não apaga a seleção sem motivo; se o id ainda existir na lista, permanece ativo; se o id sumiu, UI deixa de afirmar sessão ativa inválida e orienta a escolher/criar.
- **Agent ↔ sessão ativa**: iniciar/reiniciar agent (quando controlável pelo shell) usa o id da sessão ativa; se o agent reportar outro id, mismatch fica explícito (reutiliza superfície e regras de `specs/020-issue-47-sessionid-align`).
- **Docs**: deixar claro que list-sessions só reflete session-core; string `session-2026...` do agent sozinha não lista; shell, agent e STT devem usar o **mesmo** id da sessão do core.
- **Fora de escopo**: aceitar no list-sessions ids arbitrários só do STT sem criar sessão no core (salvo ADR futuro); alterar contrato transcript-event.v2.

### Session 2026-07-25 (clarify — defaults encadeados com plan)

- Q: Quando a lista é atualizada e o id ativo **não** está mais presente, o que acontece com `activeSessionId`? → A: **Limpar para nulo** (estado «Nenhuma sessão selecionada»); MUST NOT manter id órfão como se fosse ativa válida.
- Q: Ao carregar a lista com itens e sem sessão ativa, o shell deve auto-selecionar o primeiro item? → A: **Não**. Seleção só por clique/controle explícito ou por **criar** (create→active). Evita surpresa e alinha à issue (o bug é seleção que não gruda, não falta de auto-pick).
- Q: A sessão ativa precisa persistir entre reinícios do shell? → A: **Não nesta fatia** — estado em memória do processo do shell basta; create/select/refresh no runtime é o escopo.
- Q: Itens da lista com status diferentes (CREATED, etc.) são todos selecionáveis? → A: **Sim**, qualquer item retornado por list-sessions com id não vazio é selecionável; não filtrar por status nesta fatia.
- Q: O id completo precisa aparecer em cada linha da lista ou só no rótulo «Sessão ativa»? → A: **Sessão ativa e `data-session-id` usam id completo**; linhas da lista **podem** truncar para densidade **desde que** a seleção passe o id canônico completo e o operador veja o id integral em «Sessão ativa».

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Selecionar sessão na lista e ver sessão ativa (Priority: P1)

O operador abre o shell com session-core acessível e vê a lista de sessões. Clica (ou usa o controle claro de seleção) em um item e a UI passa a mostrar **Sessão ativa: \<id completo\>**. Assistente e demais ações que exigem sessão ativa deixam de exigir «selecione sessão».

**Why this priority**: É o bloqueio reportado na issue #49 — lista com itens mas estado «nenhuma sessão selecionada» impede o resto do fluxo (feed, Assistente, start do agent com id correto).

**Independent Test**: Fixture de lista com um item → acionar seleção → `activeSessionId` igual ao id do item e texto de sessão ativa com id completo; troca entre dois itens atualiza active e highlight. (Create→active é Independent Test da US2.) Testes do seletor com fakes, sem session-core real.

**Acceptance Scenarios**:

1. **Given** a lista de sessões com pelo menos um item `S` e nenhuma sessão ativa, **When** o operador seleciona o item `S`, **Then** a UI mostra sessão ativa com o **identificador completo** de `S` e o item aparece visualmente como selecionado.
2. **Given** sessão ativa `S`, **When** o operador olha o seletor e o painel do Assistente/agent, **Then** deixa de ver a orientação genérica «Nenhuma sessão selecionada» / «selecione sessão» como se não houvesse escolha (exceto se a ação exigir outro pré-requisito).
3. **Given** duas sessões `S` e `T` na lista com `S` ativa, **When** o operador seleciona `T`, **Then** a sessão ativa passa a ser `T` (id completo), feed e Assistente passam a usar `T`, e `S` deixa de aparecer como selecionada.
4. **Given** sessão ativa `S`, **When** o operador atualiza/recarrega a lista e `S` ainda existe, **Then** `S` permanece a sessão ativa (a atualização **não** “perde” a seleção sem motivo).
5. **Given** sessão ativa `S`, **When** a lista é atualizada e `S` **não** existe mais, **Then** a UI **não** afirma que `S` continua ativa de forma válida; orienta a selecionar ou criar outra sessão.

---

### User Story 2 - Criar sessão e torná-la ativa automaticamente (Priority: P1)

O operador cria uma nova sessão a partir do shell. Ao concluir com sucesso, essa sessão torna-se a **sessão ativa** sem passo extra de clique na lista.

**Why this priority**: Fluxo mínimo de “começar do zero”; evita lista com a sessão nova e UI ainda em «nenhuma selecionada».

**Independent Test**: Lista vazia (ou qualquer lista) → criar sessão com sucesso → active id = id retornado pela criação; UI mostra id completo.

**Acceptance Scenarios**:

1. **Given** session-core acessível e lista vazia (ou com itens), **When** o operador cria uma nova sessão com sucesso, **Then** essa sessão torna-se a sessão ativa automaticamente e o id completo fica visível.
2. **Given** falha na criação (session-core indisponível ou erro), **When** a criação falha, **Then** a UI reporta falha legível e **não** inventa sessão ativa nem marca sucesso falso.
3. **Given** uma sessão recém-criada e ativa, **When** o operador atualiza a lista, **Then** a nova sessão aparece na lista (quando o core a retorna) e permanece ativa se ainda existir.

---

### User Story 3 - Iniciar ou reiniciar o agent com a sessão ativa (Priority: P1)

Com uma sessão ativa válida (UUID/id do session-core), o operador inicia ou reinicia o agent de captura de forma que a captura use **esse** id. Se o agent já estiver em outro id, o desalinhamento fica **explícito** na UI (banner/aviso) e, em modo de controle direto, há caminho para realinhar (conforme 020).

**Why this priority**: Segunda metade da issue #49 — sem o mesmo id, transcript/Assistente da sessão da lista não recebem a captura; ids `session-YYYYMMDD-...` só no agent não resolvem sozinhos o list-sessions.

**Independent Test**: Com sessão ativa `S` e fakes de start/status: (a) start recebe `S`; (b) status com agent em `T` ≠ `S` → mismatch visível; (c) sem sessão ativa → start bloqueado ou orienta seleção; (d) comando guiado / guidance contém `--session S` (id completo da sessão ativa).

**Acceptance Scenarios**:

1. **Given** sessão ativa `S` e agent parado em modo de controle direto, **When** o operador aciona **Iniciar agent**, **Then** o agent é iniciado com o identificador `S` (não com id gerado tipo `session-YYYYMMDD-HHMMSS` nem com id antigo).
2. **Given** agent em execução (modo direto) com sessão `A` e sessão ativa `B` (`A` ≠ `B`), **When** o operador aciona **Reiniciar agent com sessão ativa** (ou equivalente de realinhamento da 020), **Then** o agent passa a usar `B`.
3. **Given** nenhuma sessão ativa, **When** o operador tenta iniciar o agent pela UI, **Then** a ação é bloqueada ou orienta a selecionar/criar sessão — **não** inicia com id ambíguo ou só de STT.
4. **Given** sessão ativa `S` e agent reportando sessão `T` (`S` ≠ `T`, ambas conhecidas), **When** o shell atualiza o status, **Then** exibe aviso de desalinhamento visível (regras de mismatch da 020).
5. **Given** modo guiado e sessão ativa `S`, **When** o operador vê o comando orientado, **Then** o comando inclui `--session S` (id da sessão ativa do core) — verificável em teste automatizado de guidance (FR-012).

---

### User Story 4 - Documentação: mesmo sessionId e o que a lista reflete (Priority: P2)

O operador ou desenvolvedor lê running/min-flow e entende: (1) shell, agent e STT devem usar o **mesmo** identificador da sessão do session-core; (2) list-sessions **só** reflete sessões do session-core; (3) string `session-YYYYMMDD-...` usada só no agent **não** faz a sessão aparecer na lista sozinha; (4) selecionar na lista define a sessão ativa da UI mas **não** reconfigura sozinha um agent já em execução (precisa reiniciar com o id ativo).

**Why this priority**: Fecha o anti-padrão operacional da issue e evita regressão de processo.

**Independent Test**: Revisar `docs/development/running.md` e/ou `docs/release/min-flow.md` e localizar as quatro regras acima de forma acionável.

**Acceptance Scenarios**:

1. **Given** a documentação operacional atualizada, **When** o leitor procura list-sessions / sessão ativa / sessionId, **Then** encontra que a lista reflete o **session-core**, não ids arbitrários só do agent/STT.
2. **Given** a mesma documentação, **When** o leitor procura o formato `session-YYYYMMDD` ou exemplo de agent, **Then** encontra aviso de **não** usar esse id sozinho se a intenção é alimentar a sessão da lista/UI.
3. **Given** a mesma documentação, **When** o leitor segue o fluxo do agent, **Then** vê a regra do mesmo id da sessão ativa da UI e o passo de iniciar/reiniciar com esse id.

---

### Edge Cases

- **Clique em item já ativo**: permanece ativo; sem flicker para «nenhuma sessão» nem perda de estado do Assistente/feed.
- **Duplo clique / cliques rápidos** em itens diferentes: a sessão ativa final corresponde ao último item selecionado de forma determinística; sem estado “nenhuma” intermediário persistente.
- **Bootstrap com lista populada e sem ativa**: permanece «Nenhuma sessão selecionada» até select ou create — **sem** auto-selecionar o primeiro item (clarify).
- **Lista com item sem id utilizável** (vazio/malformado): item não é selecionável como ativa, ou falha legível; MUST NOT setar sessão ativa inválida.
- **Id ativo órfão após refresh bem-sucedido**: se a lista retornou com sucesso e o id ativo não está nela, `activeSessionId` → `null`; UI de sessão nenhuma; Assistente/agent voltam a exigir seleção (clarify).
- **Falha ao listar (core down)**: erro legível; não inventar lista; sessão ativa prévia pode permanecer até um refresh bem-sucedido reconcilie — distinto do orphan clear.
- **Atualização de lista concorrente com seleção**: seleção do operador prevalece se o id ainda existir após o refresh; se o id sumiu, aplicar US1 cenário 5.
- **Session-core desconectado**: lista/criação não reportam sucesso falso; ações que dependem do core falham com status claro.
- **Id do agent no formato `session-YYYYMMDD-HHMMSS`**: se legível, conta como sessão do agent para mismatch; **não** é adicionado automaticamente à lista do session-core.
- **Troca de sessão ativa com agent Direct rodando noutro id**: mismatch + CTA de reinício (020); seleção **não** reinicia o agent sozinha.
- **Start falha** (binário, perfil, permissão): erro no painel do agent; não marca alinhamento falso nem limpa a sessão ativa da UI.
- **Privacidade**: ids de sessão operacionais podem aparecer na UI; MUST NOT logar áudio bruto, tokens ou saída completa do modelo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O shell MUST permitir ao operador **selecionar** uma sessão existente a partir da lista retornada pelo session-core (clique no item ou controle inequívoco de seleção). A seleção MUST definir a **sessão ativa** com o identificador canônico do item. MUST NOT auto-selecionar o primeiro item só porque a lista carregou com itens e nenhuma ativa (clarify). Qualquer item da lista com identificador não vazio MUST ser selecionável independentemente do status de domínio da sessão (CREATED, etc.).
- **FR-002**: Com sessão ativa definida, a UI MUST exibir o texto (ou equivalente inequívoco) **Sessão ativa: \<identificador completo\>**. O rótulo de sessão ativa MUST mostrar o id **integral** (copiável/conferível). Linhas da lista MAY truncar o id para densidade, desde que o controle de seleção use o id canônico completo (`data-session-id` ou equivalente) e o operador consiga ver o id integral no rótulo de sessão ativa após selecionar (clarify).
- **FR-003**: Enquanto nenhuma sessão ativa válida estiver definida, a UI MUST mostrar o estado «Nenhuma sessão selecionada» (ou equivalente) e MUST bloquear ou orientar ações que dependem de sessão ativa (Assistente automático, start do agent, etc.).
- **FR-004**: Após seleção bem-sucedida de um item da lista, a UI MUST NOT permanecer no estado «Nenhuma sessão selecionada». Assistente e demais superfícies que só exigiam sessão ativa MUST deixar de exigir seleção.
- **FR-005**: Ao **criar** uma sessão com sucesso no session-core, o shell MUST tornar essa sessão a **sessão ativa** automaticamente (sem exigir segundo clique na lista).
- **FR-006**: Atualizar/recarregar a lista de sessões MUST NOT limpar a sessão ativa se o identificador ativo ainda constar na lista retornada. Se o identificador ativo **não** constar mais, o shell MUST **definir a sessão ativa como nula** (estado «Nenhuma sessão selecionada») e MUST orientar a selecionar ou criar outra — MUST NOT manter id órfão como ativa válida (clarify).
- **FR-007**: A lista de sessões MUST refletir apenas sessões do **session-core**. MUST NOT inventar nem inserir na lista, sem criação no core, identificadores gerados só pelo agent/STT (ex. `session-YYYYMMDD-HHMMSS`).
- **FR-008**: Com sessão ativa e modo de controle **direto**, o shell MUST permitir **iniciar** o agent passando o **identificador da sessão ativa** como sessão da captura. MUST NOT gerar um novo id de caminho STT no lugar do id da sessão ativa quando o operador inicia pela UI.
- **FR-009**: Com agent em execução em modo **direto** e sessão ativa definida, o shell MUST permitir **reiniciar** o agent com o identificador da sessão ativa atual (parar o processo controlado e iniciar de novo), alinhado a `specs/020-issue-47-sessionid-align`.
- **FR-010**: O shell MUST NOT iniciar o agent pela UI sem sessão ativa; MUST orientar a selecionar ou criar sessão.
- **FR-011**: Quando sessão ativa e sessão do agent forem ambas conhecidas e diferentes, o shell MUST exibir **aviso de desalinhamento** visível (regras e resolução de sessão do agent conforme 020). Selecionar outro item na lista MUST NOT, por si só, reiniciar o agent.
- **FR-012**: Em modo **guiado**, o comando de orientação MUST incluir o identificador da sessão ativa (quando houver).
- **FR-013**: A suíte de verificação automatizada do seletor/sessão MUST cobrir, no mínimo: (a) lista com 1 item → selecionar → active id igual ao item e UI de sessão ativa; (b) lista vazia → criar → active id da sessão criada; (c) atualizar lista com id ainda presente → seleção preservada; (d) id ativo ausente após refresh → não permanece como ativa válida; (e) start do agent (fake) recebe o id da sessão ativa; (f) mismatch exibe aviso quando ids divergem (fakes).
- **FR-014**: A documentação operacional (`docs/development/running.md` e/ou `docs/release/min-flow.md`) MUST registrar: mesmo sessionId entre UI, agent e STT; list-sessions só reflete session-core; id `session-YYYYMMDD-...` do agent **não** lista sozinho; selecionar na lista não reconfigura agent em execução — é preciso iniciar/reiniciar com o id ativo.
- **FR-015**: Esta feature MUST NOT alterar o contrato `transcript-event.v2` nem aceitar no list-sessions ids arbitrários só do STT sem criação no session-core, salvo ADR e ciclo de contrato separado.
- **FR-016**: Logs e painéis desta feature MUST NOT incluir segredos, áudio bruto ou saída completa do modelo; ids de sessão operacionais podem aparecer na UI e em logs de diagnóstico de nível apropriado.

### Key Entities

- **Sessão (session-core)**: registro de sessão conhecido pelo session-core; possui identificador canônico (tipicamente UUID) e metadados de listagem (rótulo, datas, etc.).
- **Lista de sessões**: conjunto de sessões retornado pelo session-core para o seletor do shell; fonte da verdade da listagem na UI.
- **Sessão ativa (UI)**: identificador da sessão selecionada ou criada no shell; escopo do feed de transcript, do Assistente e do id passado ao agent no start/restart gerenciado.
- **Sessão do agent**: identificador com o qual a captura/STT está associada (resolução conforme 020: cmdline `--session` → último start gerenciado → desconhecida). Pode divergir do formato/listagem do core.
- **Identificador só de caminho STT**: string no estilo `session-YYYYMMDD-HHMMSS` usada historicamente no agent; **não** equivale a entrada automática em list-sessions.
- **Estado de alinhamento de sessão**: alinhado | desalinhado | agent parado | sessão do agent desconhecida | sem sessão ativa (conforme 020).
- **Seletor de sessão**: superfície de UI (lista + criar + indicação de ativa) no shell desktop.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em **100%** dos testes automatizados do seletor com lista de um ou mais itens, após a ação de seleção o estado de sessão ativa é o id do item escolhido e a UI **não** permanece em «Nenhuma sessão selecionada».
- **SC-002**: Em **100%** dos testes de criação bem-sucedida, a sessão criada é a sessão ativa sem segundo passo de seleção.
- **SC-003**: Em **100%** dos testes de refresh com id ativo ainda presente, a seleção é preservada; com id ausente, a UI não trata o id órfão como ativa válida.
- **SC-004**: Em teste com fake de start e sessão ativa `S`, o start do agent usa **exatamente** `S` (não um id gerado do tipo `session-YYYYMMDD-HHMMSS`).
- **SC-005**: Em **100%** dos casos de teste com sessão ativa ≠ sessão do agent (ambas conhecidas), o aviso de mismatch está presente.
- **SC-006**: Documentação operacional atualizada permite a um revisor localizar em **menos de 2 minutos** as regras: mesmo sessionId; list-sessions = session-core; id só do agent não lista sozinho; seleção ≠ reinício do agent.
- **SC-007**: Com sessão selecionada na lista, ids alinhados e demais pré-condições da 019/020 (finais elegíveis, automático, origem), feed/Assistente **podem** funcionar conforme essas specs — o bloqueio «selecione sessão» e o mismatch por id só de STT deixam de ser a causa.

## Assumptions

- A listagem e criação de sessões no session-core já existem (API/contrato de sessão); esta feature corrige e completa o **comportamento do seletor** e o **uso do id ativo** no agent, não redesenha o modelo de domínio de sessão.
- Preferências do Assistente por sessão e regras de disparo permanecem em `specs/019-auto-answer-assistant`; mismatch detalhado, CTA de reinício e estados vazios do Assistente permanecem em `specs/020-issue-47-sessionid-align`. Esta fatia **não** reespecifica toda a 020 — concentra seleção confiável, create→active, preservação no refresh e o vínculo explícito agent↔id do core.
- Quando 020 e 021 se sobrepõem (start com sessão ativa, mismatch, docs de sessionId único), os requisitos são **compatíveis**; implementação pode reutilizar a mesma superfície de UI e testes, desde que os cenários de FR-013/SC desta spec passem.
- Formato canônico de id de sessão do core é o retornado por list/create (UUID ou string estável do core); a UI não normaliza para o prefixo `session-` do agent.
- Persistência de `activeSessionId` entre reinícios do processo do shell **não** é requisito desta fatia (clarify).
- Testes automatizados usam fakes/fixtures (P10); validação WASAPI real permanece manual em host Windows.

## Out of Scope

- Aceitar no list-sessions ids arbitrários só do STT/agent sem criar sessão no session-core (salvo ADR futuro).
- Alterar contrato `transcript-event.v2` (parcial/final) sem ADR.
- Auto-start de Docker, STT ou session-core a partir do shell.
- Multi-agent / multi-sessão de captura em paralelo no mesmo shell.
- Classificador avançado de pergunta / mudanças na orquestração live-answer além do desbloqueio por sessão ativa.
- Redesign visual completo do shell além do necessário para seleção, indicação de ativa e mismatch.
- Migração em massa de sessões históricas `session-YYYYMMDD-...` para o session-core.

## Dependencies

- Session-core com listagem e criação de sessão e feed por `sessionId`.
- Shell desktop com seletor de sessão e painel de agent (014 / implementação corrente).
- `specs/019-auto-answer-assistant` — sessão ativa como pré-requisito do Assistente.
- `specs/020-issue-47-sessionid-align` — start/restart com sessão ativa, mismatch, CTA, docs de sessionId único (complementar).
- Agent Windows aceitando `--session <id>` (já existente).
- Docs `docs/development/running.md` e `docs/release/min-flow.md` como alvos de atualização documental.
