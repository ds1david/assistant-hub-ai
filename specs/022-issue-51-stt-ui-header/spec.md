# Feature Specification: STT UI — sessionId e profile no header do Streaming Foundation

**Feature Branch**: `feature/issue-51-stt-ui-exibir-sessionid-e-profile-no-header-do-s`

**Created**: 2026-07-25

**Status**: Clarified

**Input**: User description: "criar/atualizar specs/00x-issue-51-*/" — GitHub issue #51: [stt-ui] Exibir sessionId e profile no header do Streaming Foundation

**Referências**: Issue [#51](https://github.com/ds1david/assistant-hub-ai/issues/51) · Dashboard STT «Assistant Hub AI · Streaming Foundation» (UI estática do serviço de transcrição) · Alinhamento sessionId agent/UI `specs/020-issue-47-sessionid-align` · Seleção de sessão no shell `specs/021-issue-49-session-list-select` · Streaming foundation `specs/001-streaming-foundation` · Constituição P1 (spec antes de código), P5 (`sessionId` ponta a ponta), P9 (privacidade), P10 (testes sem GPU/WASAPI real) · Docs `docs/development/running.md` e `docs/release/min-flow.md`

## Clarifications

### Session 2026-07-25 (defaults a partir da issue #51 — sem bloqueio)

- **Problema**: no dashboard Streaming Foundation o operador vê status «conectado» e cards de canal, mas **não** vê o `sessionId` em uso (o mesmo do path de áudio `/ws/audio/{sessionId}/...`) nem o **profile** do agent. Strings tipo `session-20260725-...` vs UUID do session-core ficam invisíveis na UI de transcript; alinhar agent ↔ shell exige abrir log do PowerShell.
- **Superfície**: somente o **header** da página STT (junto ao status de conexão). Session/profile são da **sessão**, não de cada canal — **não** repetir em cada card de canal.
- **sessionId**: valor completo, legível e **copiável** (ação Copiar). Origem: o identificador já presente nos eventos de transcript / sessões ativas conhecidas pelo feed da UI (o mesmo id que o agent usa no path de áudio).
- **profile**: caminho padrão = **nota** de origem no agent (`--profile`); exibir nome lógico **somente** se já existir na página sem schema novo (ver analyze remediação U2 / FR-005).
- **URL base do STT**: **obrigatória** no header (origem do documento, ex. `http://localhost:8001`); não é opcional nesta fatia (clarify + analyze I1).
- **Fora de escopo**: auto-alinhar agent ao shell; mudança de contrato transcript-event.v2; live-answer / painel Assistente do desktop-shell; seletor de sessão do shell (021).

### Session 2026-07-25 (clarify — defaults encadeados com plan)

- Q: Com vários sessionIds no feed, qual é o id **primário** (destaque + alvo de Copiar)? → A: **Mais recentemente observado** no feed de transcript; ids anteriores permanecem listados com indicação de múltiplos; Copiar usa só o primário.
- Q: A URL base do STT entra nesta fatia ou fica só como MAY futuro? → A: **Incluir** no header (origem da página, ex. `http://localhost:8001`); barata e útil para o operador confirmar o host.
- Q: Nesta fatia o profile deve vir de contrato/eventos novos ou só nota? → A: **Só nota / valor se já disponível sem mudar transcript-event.v2**; MUST NOT inventar profile nem estender schema.
- Q: De onde a UI observa sessionId antes/sem painel de canais? → A: **Somente** do campo `sessionId` dos eventos do feed de transcript da página (mesmo conjunto já usado para métricas); sem inventar a partir da URL do browser.
- Q: Feedback de Copiar e testes automatizados? → A: Feedback textual breve no próprio controle (sucesso/falha, ~2s); testes determinísticos de **estrutura do header + estado puro** (sem GPU/WASAPI); clipboard real no quickstart manual se o ambiente bloquear fakes.

### Session 2026-07-25 (analyze remediação)

- **I1**: URL base no header é **MUST** (FR-011); Key Entities e defaults não usam mais «opcional».
- **U2**: Nesta fatia **não há fonte de profile** (feed/query/schema). FR-005 = **MAY** exibir nome se já presente na página sem contrato novo; caminho **padrão e obrigatório de fallback** = FR-006 nota de agent. Implement **não** procura fonte «misteriosa».
- **U1**: Política canônica de observe/primary/multi = módulo Python `header_session_state.py` (testado); JS no `index.html` **espelha** as mesmas regras (comentário de contrato no script).
- **A2**: Multi-session UI: indicador `#session-multi` com contagem (ex. «N sessões») + primário completo; lista compacta de ids secundários opcional se couber no layout.
- **C1/C2**: SC-001 (≤5s) e SC-004 (comparar com shell) são critérios **manuais** no quickstart; pytest cobre estrutura/estado, não E2E shell nem cronômetro.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver sessionId no header da página STT (Priority: P1)

O operador abre o dashboard Streaming Foundation (página de transcript do STT) com o agent enviando áudio/transcript para um `sessionId` conhecido. No header, ao lado do status de conexão («conectado» / «conectando…» / «reconectando…»), vê o **sessionId completo** em uso — o mesmo identificador do path de captura de áudio — sem precisar do log do PowerShell.

**Why this priority**: É o valor principal da issue #51 — sem sessionId visível, o operador não consegue confirmar alinhamento agent ↔ shell ↔ STT.

**Independent Test**: Com feed de transcript (ou fixture) contendo `sessionId = X`, o header exibe `X` completo; com status conectado e ainda sem eventos, o header não inventa id falso (estado vazio/aguardando legível).

**Acceptance Scenarios**:

1. **Given** o dashboard STT aberto e o feed recebe transcript(s) com `sessionId = X`, **When** a UI processa o evento, **Then** o header mostra o sessionId **completo** `X` (não truncado de forma que impeça copiar o valor integral).
2. **Given** o dashboard conectado ao feed mas ainda sem nenhum transcript/sessão observada, **When** o operador olha o header, **Then** o status de conexão permanece visível e o espaço de sessionId indica ausência de sessão observada (ex. «—» / «aguardando sessão»), **sem** inventar id.
3. **Given** sessionId longo (UUID ou string `session-YYYYMMDD-HHMMSS...`), **When** o header é renderizado, **Then** o layout do header **não quebra** (id permanece legível ou com wrap/scroll controlado; ação de copiar ainda entrega o valor **completo**).
4. **Given** sessionId visível no header, **When** o operador compara com o `--session` usado no agent e com a sessão ativa no shell (quando aplicável), **Then** consegue confirmar igualdade ou divergência **sem** abrir o log do terminal do agent.

---

### User Story 2 - Copiar sessionId do header (Priority: P1)

O operador precisa colar o sessionId em outro lugar (comando do agent, shell, documentação de suporte). Usa a ação **Copiar** no header e obtém o valor completo na área de transferência.

**Why this priority**: Aceite explícito da issue; reduz erro de digitação e elimina copiar do log.

**Independent Test**: Com sessionId `X` no header, acionar Copiar → valor copiado é exatamente `X`; feedback breve de sucesso (ou de falha se a cópia não for possível).

**Acceptance Scenarios**:

1. **Given** sessionId primário `X` exibido no header, **When** o operador aciona **Copiar**, **Then** a área de transferência contém exatamente `X` e o controle dá feedback textual breve de sucesso (FR-004, ex. «copiado»).
2. **Given** nenhum sessionId observado ainda, **When** o operador olha o header, **Then** a ação Copiar está ausente ou desabilitada — **não** copia string vazia como se fosse id válido.
3. **Given** falha da API de área de transferência do ambiente, **When** o operador aciona Copiar, **Then** o controle indica falha de forma legível (FR-004, sem crash) e o sessionId permanece visível/selecionável para cópia manual.

---

### User Story 3 - Nota de profile (padrão) e nome só se já presente (Priority: P2)

O operador vê no header uma **nota** de que o profile de áudio é definido no agent (`run --profile …`). Só se um nome lógico já estiver presente na página **sem** schema novo (FR-005 MAY — nesta fatia: nenhuma fonte), o header pode mostrar esse nome em vez da nota. Nunca inventa profile.

**Why this priority**: Aceite da issue inclui profile «se disponível»; caminho padrão = nota (analyze U2).

**Independent Test**: Página padrão → nota de agent/`--profile`; cards de canal sem session/profile de sessão.

**Acceptance Scenarios**:

1. **Given** a página STT padrão (sem profile injetado), **When** o operador olha o header, **Then** o elemento de profile mostra a **nota** de origem no agent (FR-006), sem inventar nome.
2. **Given** (MAY) um nome de profile já presente na página sem mudança de contrato, **When** o header o exibe, **Then** mostra esse nome legível e **não** uma string inventada.
3. **Given** sessionId e profile/nota no header, **When** o operador inspeciona os cards de canal, **Then** **não** há repetição de sessionId/profile em cada card.

---

### User Story 4 - URL base do STT e documentação mínima (Priority: P3)

O operador vê a **URL base** do STT em que a página está aberta (origem do documento) no header, sem poluir o layout. A documentação operacional (running e/ou min-flow) menciona que o header do Streaming Foundation exibe o sessionId em uso para alinhar agent e shell.

**Why this priority**: Confirmado no clarify (incluir URL); docs reforçam o fluxo operacional sem expandir produto.

**Independent Test**: Header mostra origem esperada; docs com menção ao header/sessionId do dashboard STT.

**Acceptance Scenarios**:

1. **Given** a página STT aberta em um host conhecido, **When** o operador olha o header, **Then** a URL base reflete a origem do documento (ex. host:porta do STT) sem tokens ou paths sensíveis.
2. **Given** documentação operacional atualizada, **When** o leitor procura alinhar agent e dashboard STT, **Then** encontra que o header do Streaming Foundation mostra o sessionId em uso e que copiar o id evita depender do log do PowerShell.

---

### Edge Cases

- **Múltiplos sessionIds no feed**: primário = mais recentemente observado; `#session-multi` mostra contagem (ex. «N sessões») e, se couber, ids secundários compactos; **Copiar** usa só o primário; **não** empurra session/profile para cada card de canal.
- **Troca de sessionId**: cada novo `sessionId` no feed torna-se o primário; ids anteriores permanecem no conjunto observado até **reload** da página (sem sessão «fantasma» inventada fora do feed).
- **Ids muito longos**: wrap, scroll horizontal controlado ou tipografia monoespaçada no header; copiar sempre o valor integral.
- **Reconexão do feed (WebSocket)**: `onclose`/`reconnect` **não** limpa o conjunto observado nem o primário em memória; novos eventos atualizam o primário. **Reload** da página zera o estado. Não inventar ids sem ter observado o feed nesta carga.
- **Conteúdo sensível**: sessionId e profile são identificadores operacionais; **não** exibir áudio bruto, tokens ou texto de transcript no header.
- **Ambiente sem clipboard**: fallback com seleção manual do texto + mensagem de falha na cópia automática.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O dashboard Streaming Foundation MUST exibir, de forma fixa no **header** (junto ao status de conexão), o **sessionId em uso** quando houver sessão observada no feed de transcript (ou estado equivalente já conhecido pela página).
- **FR-002**: O sessionId exibido MUST ser o **mesmo** identificador associado à captura/transcrição da sessão (equivalente ao `{sessionId}` do path de áudio do STT), completo e legível.
- **FR-003**: O header MUST oferecer ação **Copiar** que coloca o sessionId **primário** completo na área de transferência quando há id válido; MUST NOT copiar valor vazio como se fosse id.
- **FR-004**: A UI MUST dar feedback **textual breve no controle** de Copiar (~2s) para sucesso ou falha; em falha de clipboard o sessionId permanece selecionável/visível para cópia manual. (Unifica o antigo FR-015 — analyze D1.)
- **FR-005**: O header MAY exibir o **nome lógico do profile** de áudio **somente** se esse valor já estiver presente na página **sem** estender transcript-event.v2 e **sem** inventar a partir de query string ou heurística. Nesta fatia a fonte padrão é **nenhuma** → aplicar FR-006.
- **FR-006**: O header MUST exibir (quando não houver nome de profile por FR-005) uma **nota** de que o profile é definido no agent / comando de captura (`--profile`); MUST NOT inventar nome de profile.
- **FR-007**: SessionId e profile/nota MUST aparecer no header da **sessão**; MUST NOT ser repetidos em cada card de canal (cards: label/canal/dispositivo/métricas de canal apenas).
- **FR-008**: O layout do header MUST permanecer usável com sessionId longo (UUID ou string `session-…`, ≥64 caracteres); a ação Copiar MUST continuar entregando o valor completo.
- **FR-009**: Sem sessão observada, o header MUST mostrar estado vazio/aguardando legível e manter o status de conexão; MUST NOT fabricar sessionId.
- **FR-010**: Se mais de um sessionId for observado, o header MUST tornar isso visível: primário = mais recente + indicador multi com **contagem** (ex. «N sessões»); Copiar MUST usar o primário; MUST NOT misturar session/profile nos cards (alinha FR-007).
- **FR-011**: O header MUST exibir a **URL base** do STT em que a página está aberta (origem do documento, sem tokens nem paths sensíveis).
- **FR-012**: A documentação operacional (`docs/development/running.md` e/ou `docs/release/min-flow.md`) MUST mencionar, de forma curta e acionável, que o header do dashboard Streaming Foundation exibe o sessionId em uso e que Copiar evita depender do log do agent.
- **FR-013**: Esta fatia MUST NOT alterar o contrato transcript-event.v2, auto-alinhar agent ao shell, nem implementar live-answer / painel Assistente.
- **FR-014**: A observação de sessionId MUST basear-se no campo `sessionId` dos eventos do feed de transcript da página; MUST NOT fabricar id a partir da URL do browser ou de query string.
- **FR-015**: *(retirado — conteúdo unificado em FR-004; ID reservado para não renumerar tarefas legadas que citavam FR-015 como feedback de copiar.)*

### Key Entities

- **SessionId em uso (primário)**: identificador da sessão de captura/transcrição visto pelo dashboard STT via feed; igual ao id usado no path de áudio do STT (pipeline 001); completo e copiável.
- **Profile de áudio**: nome lógico do perfil do agent Windows (ex. `default-windows-devices`). Nesta fatia a UI **não** recebe profile do feed; exibe **nota** de origem no agent (FR-006), salvo valor já presente sem schema novo (FR-005 MAY).
- **Header do Streaming Foundation**: região fixa da página de transcript do STT com título, status de conexão, sessionId primário, indicador multi (se aplicável), profile/nota, **URL base** (MUST) e controle Copiar.
- **Card de canal**: painel por `channelId` (label, dispositivo, métricas, feed de texto); **não** é o lugar de sessionId/profile de sessão.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com agent em execução com `--session X` (e transcript fluindo para o dashboard), o operador identifica `X` no header em **menos de 5 segundos** após o primeiro evento visível no feed, sem abrir log do terminal. *(Validação manual / quickstart; pytest não cronometra.)*
- **SC-002**: Em **100%** dos casos com sessionId válido no header, a ação Copiar entrega o valor completo idêntico ao exibido (ou falha explícita se o ambiente bloquear clipboard). *(Estrutura + paths de feedback em pytest; clipboard real no quickstart se necessário.)*
- **SC-003**: Layout do header permanece legível e usável com ids de até pelo menos **64 caracteres** (UUID e strings `session-…` longas) sem sobrepor o status de conexão de forma irrecuperável.
- **SC-004**: Operador consegue confirmar se o sessionId do STT coincide com o da sessão ativa do shell **sem** ler o log do PowerShell do agent. *(Outcome operacional; docs + visibilidade no header; sem E2E shell obrigatório.)*
- **SC-005**: Cards de canal **não** ganham campos novos de sessionId/profile; revisão visual / assert de template confirma metadados de sessão só no header.
- **SC-006**: Docs running e/ou min-flow citam o header/sessionId do dashboard STT de forma encontrável em busca textual (`sessionId`, header, Streaming Foundation ou equivalente).

## Assumptions

- A superfície desta feature é o **dashboard STT** «Assistant Hub AI · Streaming Foundation» (UI estática servida com o serviço de transcrição), **não** o desktop-shell (que já trata sessão ativa / mismatch em 020 e 021).
- O `sessionId` já flui nos eventos de transcript consumidos pela página; a fatia **exibe** esse valor no header — não redefine identidade de sessão. Paridade com o path `/ws/audio/{sessionId}/...` é propriedade do pipeline 001 (mesmo id no evento), não revalidada por teste de path nesta fatia.
- **Profile**: nenhuma fonte nesta fatia → **sempre** FR-006 (nota). FR-005 MAY só se valor já existir sem schema; **fora** de escopo: ADR/campo novo no transcript v2.
- Fluxo operacional típico usa **um** sessionId por operador; multi-session: primário = mais recente + contagem (FR-010).
- URL base = origem do documento no browser (**MUST**, FR-011); não é seletor de host nem configuração de deploy.
- **Política canônica** de estado (observe/primary/multi/vazio): `header_session_state.py`; JS do `index.html` espelha (U1).
- Testes automatizados: estrutura do header + regras puras de estado; SC-001/SC-004 manuais no quickstart; clipboard real se fakes não bastarem. Sem GPU/WASAPI (P10).
- Privacidade (P9): header não exibe áudio bruto, tokens nem conteúdo de transcript.
- Alinhamento **automático** agent↔shell permanece fora de escopo (020/021); esta fatia só **torna visível** o id no STT para o operador comparar e copiar.

## Out of Scope

- Auto-alinhar ou reiniciar o agent com a sessão do shell
- Alteração de contrato transcript-event.v2 (salvo ADR futuro)
- Live-answer / painel Assistente / preferências do desktop-shell
- Seletor de sessão do shell e list-sessions (021)
- Persistência de sessionId escolhido pelo operador no dashboard STT
- Autenticação, multi-tenant ou redaction avançada de ids
- Mudança de comportamento do path `/ws/audio/{sessionId}/...` além do necessário para exibir o id já conhecido
