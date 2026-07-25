# Feature Specification: Alinhar sessionId UI↔agent e disparo só em transcript final (live-answer)

**Feature Branch**: `feature/issue-47-desktop-live-answer-alinhar-sessionid-ui-agent-e`

**Created**: 2026-07-25

**Status**: Clarified

**Input**: User description: "criar/atualizar specs/00x-issue-47-*/" — GitHub issue #47: Live-answer: alinhar sessionId UI↔agent e disparo só em transcript final

**Referências**: Issue [#47](https://github.com/ds1david/assistant-hub-ai/issues/47) · Spec base `specs/019-auto-answer-assistant` (FR-003 só finais; FR-014/FR-026/FR-027 sessão ativa) · Shell desktop `specs/014-issue-35-desktop-tauri-shell-local` · Constituição P1 (spec antes de código), P5 (`sessionId` ponta a ponta), P9 (privacidade), P10 (testes sem GPU/WASAPI real) · Docs operacionais `docs/development/running.md` e `docs/release/min-flow.md`

## Clarifications

### Session 2026-07-25 (defaults a partir da issue #47 — sem bloqueio)

- **Problema operacional**: selecionar sessão na lista do shell **não** altera o `--session` do agent de captura já em execução; feed de transcript e Assistente usam o UUID da UI, enquanto STT/agent usam outro id → painel vazio sem erro de console.
- **Problema de produto**: automático da 019 dispara **somente** em trechos **finais** (não parciais). Se o pipeline emite quase só partials, o Assistente permanece vazio mesmo com ids alinhados — a UI deve **explicar** esse estado.
- **Ação de start/restart**: reutilizar o controle de agent já existente no shell (iniciar/parar). “Iniciar/reiniciar com a sessão ativa” = parar (se em execução e **controlável pelo shell** / Direct) e iniciar passando o UUID da sessão ativa. Com mismatch em modo Direct, a UI MUST oferecer CTA explícito **Reiniciar agent com sessão ativa** (além do banner); selecionar na lista **não** reinicia sozinho. **MUST NOT** forçar encerramento de processo de agent iniciado fora do shell (Guided); recuperação = mismatch (se conhecido) + comando guiado com sessão ativa + parada manual pelo operador.
- **Sessão do agent detectável**: prioridade de resolução — (1) valor de `--session` na linha de comando do processo do agent em execução, se legível; (2) id do último start bem-sucedido gerenciado pelo shell; (3) “desconhecida”. Em modo guiado, a UI ainda mostra o comando com o UUID da sessão **ativa**.
- **Mismatch**: aviso visível no shell quando sessão ativa (UI) ≠ sessão do agent (quando esta for conhecida); não depende de ler o log do PowerShell.
- **Fora desta fatia**: multi-agent paralelo, auto-start de Docker/STT, classificador avançado de pergunta (R2), mudança de contrato transcript-event.v2 (salvo ADR).

### Session 2026-07-25

- Q: How should the shell determine the agent’s session id (for display and mismatch)? → A: Detect when possible: parse running process command line for `--session` if available; else last shell-managed start id; else “unknown”.
- Q: When the agent is already running outside shell control (Guided) and the operator wants the active UI session, what recovery path must the product offer? → A: No force-kill of external agent. Mismatch + guided command with active session; operator stops manually, then starts (UI Direct if free, or paste command).
- Q: When should the Assistente panel show “awaiting final transcript” vs other empty-state messages? → A: Distinct empty states: awaiting final (only partials + auto ready); waiting for transcript (empty feed); no eligible question (finals but none qualify); preference messages when auto/origin off; mismatch banner wins over partials hint.
- Q: When the operator selects a different active session while a Direct-controlled agent is already running (mismatch appears), what should the UI offer? → A: Mismatch banner + explicit “Restart agent with active session” (or equivalent) CTA; select still does not auto-restart.
- Q: Should restarting the agent with the active session require an extra confirmation step? → A: No confirmation dialog; CTA restarts immediately.

### Session 2026-07-25 (pós-analyze)

- Q: Quando o agent está parado e o shell não tem handle, o modo de controle deve permitir Iniciar? → A: Sim — status com agent **parado** reporta modo **direto** (Start disponível). Modo **guiado** só com agent **em execução** fora do controle do shell (analyze I1).
- Q: Feed vazio vs só partials nos estados vazios do Assistente? → A: Feed vazio = “aguardando transcript”; ≥1 partial sem final elegível = “aguardando trecho final” (analyze I4).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Iniciar ou reiniciar o agent com a sessão ativa (Priority: P1)

O operador escolhe (ou cria) a sessão ativa na lista do shell e, a partir do painel do agent, **inicia ou reinicia** a captura usando **exatamente** o identificador da sessão ativa. Não precisa copiar o UUID para o PowerShell quando o modo de controle direto está disponível.

**Why this priority**: É a causa raiz do sintoma “Assistente e transcript vazios com STT mostrando fala em outro cliente” — sem o mesmo `sessionId`, a 019 nunca reage.

**Independent Test**: Com sessão ativa `S` selecionada na UI e agent parado (ou em execução com outro id), acionar iniciar/reiniciar pelo shell; verificar que o agent passa a usar `S` e que o status do agent reflete esse id (modo direto). Testes com fakes cobrem que o start recebe o id da sessão ativa.

**Acceptance Scenarios**:

1. **Given** uma sessão ativa `S` selecionada na lista e o agent parado em modo de controle direto, **When** o operador aciona **Iniciar agent**, **Then** o agent é iniciado com o identificador `S` (não com um id gerado ou antigo).
2. **Given** o agent em execução (modo direto) com sessão `A` e a sessão ativa na UI é `B` (`A` ≠ `B`), **When** o operador aciona a CTA **Reiniciar agent com sessão ativa**, **Then** o agent deixa de usar `A` e passa a usar `B` (equivalente a parar o processo controlado e iniciar com `B`).
3. **Given** nenhuma sessão ativa selecionada, **When** o operador tenta iniciar o agent pela UI, **Then** a ação é bloqueada ou orienta a selecionar/criar sessão — **não** inicia captura com id ambíguo.
4. **Given** modo de controle **guiado** (comando manual), **When** há sessão ativa `S`, **Then** o comando orientado inclui `--session S` (UUID da sessão ativa), para o operador colar no PowerShell.
5. **Given** agent já em execução **fora** do controle do shell (Guided) e sessão ativa `S`, **When** o operador tenta iniciar pela UI ou vê o painel de recuperação, **Then** o shell **não** encerra o processo externo; orienta a parar o agent manualmente e mostra o comando (ou start Direct quando o processo já não estiver rodando) com `--session S`.

---

### User Story 2 - Ver mismatch de sessão e corrigir (Priority: P1)

O operador vê, no shell, a **sessão ativa (UI)** e a **sessão do agent** quando esta for detectável. Se divergirem, um **banner/aviso** deixa o desalinhamento inequívoco — sem depender do log do terminal do agent.

**Why this priority**: Mesmo com botão de start correto, o operador pode ter deixado um agent antigo no ar; o produto deve tornar o erro operacional **visível**.

**Independent Test**: Com fakes de status: (a) ids iguais → sem banner de mismatch; (b) ids diferentes → banner presente; (c) sessão do agent desconhecida → estado neutro/orientação, sem falso “tudo ok”.

**Acceptance Scenarios**:

1. **Given** sessão ativa `S` e agent reportando sessão `S`, **When** o shell atualiza o status, **Then** mostra ambos os ids (ou equivalência clara) e **não** exibe aviso de mismatch.
2. **Given** sessão ativa `S` e agent reportando sessão `T` (`S` ≠ `T`), **When** o shell atualiza o status, **Then** exibe um aviso/banner de desalinhamento visível no shell (próximo ao agent e/ou ao Assistente).
3. **Given** agent parado, **When** o operador olha o painel, **Then** não há banner de mismatch por ids divergentes (o estado é “agent parado”, não “ids diferentes”).
4. **Given** agent em execução cuja sessão **não** é resolvível (sem `--session` legível na linha de comando e sem id de start gerenciado), **When** o shell atualiza o status, **Then** a UI deixa claro que a sessão do agent é desconhecida e reforça a regra de usar o mesmo id da sessão ativa (sem afirmar alinhamento nem mismatch definitivo).
5. **Given** mismatch visível e modo direto, **When** o operador usa a CTA **Reiniciar agent com sessão ativa**, **Then** o reinício inicia **sem** diálogo de confirmação e o aviso de mismatch desaparece após o agent passar a reportar o id da sessão ativa.
6. **Given** agent iniciado fora do shell (ex. PowerShell) com `--session T` legível na linha de comando e sessão ativa `S` (`S` ≠ `T`), **When** o shell atualiza o status, **Then** a sessão do agent é `T` e o aviso de mismatch aparece (sem depender de o shell ter iniciado o processo).
7. **Given** agent Direct em execução com sessão `A` e o operador **seleciona** sessão `B` na lista (`A` ≠ `B`), **When** a UI atualiza, **Then** o feed/Assistente usam `B`, o mismatch aparece **e** a CTA de reinício com sessão ativa fica disponível — **sem** reiniciar o agent só pela seleção.

---

### User Story 3 - Entender por que o Assistente não dispara (só partials / aguardando final) (Priority: P2)

Com sessionIds alinhados, automático ligado e origem habilitada, o operador ainda pode ver o feed de transcript com trechos **parciais** e o painel do Assistente vazio. O produto explica que o automático **aguarda trecho final** (e, quando aplicável, pergunta elegível), em vez de parecer “quebrado”.

**Why this priority**: Segunda causa raiz da issue #47; não muda a regra da 019 (só finais), mas fecha o buraco de UX.

**Independent Test**: Fixture com apenas partials no feed → hint “aguardando trecho final” (ou equivalente) no painel Assistente; fixture com final sintético elegível (pergunta + origem system) → orquestração dispara conforme 019.

**Acceptance Scenarios**:

1. **Given** ids alinhados (sem mismatch), automático ligado, ao menos uma origem elegível, feed com **apenas** trechos parciais (sem finais novos elegíveis) e **zero** interações, **When** o operador olha o painel Assistente, **Then** vê o estado **aguardando trecho final** (não o genérico “nenhuma interação” sem contexto).
2. **Given** as mesmas condições e um trecho **final** sintético reconhecido como pergunta com origem `system`, **When** o feed o incorpora, **Then** o Assistente inicia interação (gerando/resposta/erro de provedor) conforme `specs/019-auto-answer-assistant` — **não** permanece vazio por “sessão errada”.
3. **Given** automático desligado ou nenhuma origem habilitada, **When** o feed tem partials ou finais e zero interações, **Then** a UI prioriza a orientação de **preferências** (automático off / origem off) e **não** mostra “aguardando trecho final” como se o pipeline fosse o problema.
4. **Given** ids **desalinhados** (mismatch conhecido), **When** o painel Assistente está vazio, **Then** o aviso de mismatch (US2) tem prioridade de diagnóstico sobre qualquer hint de partials / aguardando final.
5. **Given** automático apto, feed **vazio** (sem partials nem finais) e zero interações, **When** o operador olha o Assistente, **Then** vê estado de **aguardando transcript** (não “aguardando trecho final”).
6. **Given** automático apto, feed com um ou mais **finais** que **não** são perguntas elegíveis (e sem partials “em aberto” que justifiquem aguardar final), **When** zero interações, **Then** vê estado de **nenhuma pergunta elegível ainda** (não “aguardando trecho final”).

---

### User Story 4 - Documentação da regra do sessionId único (Priority: P2)

O operador ou desenvolvedor lê a documentação de fluxo mínimo / running e entende: (1) shell, agent e STT devem usar o **mesmo** `sessionId`; (2) **selecionar na lista não reconfigura** um agent já em execução; (3) exemplo de comando PowerShell com o UUID da sessão ativa da UI; (4) preferir iniciar/reiniciar agent pela UI quando o modo direto estiver disponível.

**Why this priority**: Fecha o workaround operacional da issue e evita regressão de processo.

**Independent Test**: Revisar `docs/development/running.md` e/ou `docs/release/min-flow.md` e verificar que as quatro regras acima estão explícitas e acionáveis.

**Acceptance Scenarios**:

1. **Given** a documentação operacional atualizada, **When** o leitor procura “sessionId” / sessão ativa, **Then** encontra a regra do **mesmo** identificador entre UI, agent e STT.
2. **Given** a mesma documentação, **When** o leitor segue o fluxo do agent, **Then** vê aviso de que **selecionar sessão na lista não altera** o agent já em execução e o passo de reiniciar com o UUID correto (UI ou PowerShell de exemplo).

---

### Edge Cases

- **Troca de sessão na lista com agent rodando**: UI atualiza feed/Assistente para a nova sessão; agent continua no id antigo até reinício → **mismatch** + CTA (Direct); reinício da CTA é imediato (sem confirm).
- **Start falha** (binário ausente, perfil inválido, permissão): erro legível no painel do agent; não marca alinhamento falso.
- **Stop falha / agent zumbi**: status e lastError refletem falha; operador pode usar modo guiado; não inventar sessionId.
- **Modo guiado + agent externo**: shell **MUST NOT** forçar kill do processo externo; mostra comando com sessão ativa; se a linha de comando expuser `--session`, usa esse valor para mismatch; se não for legível, estado “desconhecida” + orientação de parada manual e reinício com o id correto.
- **Start com agent externo já rodando**: falha/orientação clara (já em execução); não inicia segunda instância nem encerra a externa em silêncio.
- **Linha de comando sem `--session` ou ilegível** (permissões, formato inesperado): sessão do agent cai no fallback (id do último start gerenciado, senão desconhecida); MUST NOT inventar id.
- **Sessão ativa muda durante start em andamento**: o start em curso deve ter sido disparado com o id no momento do clique; se a UI mudou depois, mismatch pode surgir até novo restart — aceitável e visível.
- **Partials contínuos sem final**: estado “aguardando trecho final” permanece (se pré-condições de FR-010); não dispara live-answer (FR-003 da 019).
- **Final que não é pergunta**: sem disparo; estado “nenhuma pergunta elegível” (não prometer resposta).
- **Feed vazio**: estado “aguardando transcript”, distinto de “aguardando trecho final”.
- **Precedência de diagnóstico (vazio)**: mismatch conhecido → preferências (auto/origem off) → aguardando transcript (feed vazio) → aguardando trecho final (só partials) → nenhuma pergunta elegível (finais sem pergunta).
- **Provedor/rota indisponível com ids alinhados e final elegível**: interação com **erro legível** no Assistente (não feed vazio por sessão errada).
- **Múltiplos agents**: fora de escopo; um agent por shell nesta fatia.
- **Privacidade**: avisos e status mostram ids de sessão (UUIDs operacionais); MUST NOT logar áudio bruto, tokens ou texto completo do modelo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Com sessão ativa selecionada e modo de controle **direto**, o shell MUST permitir **iniciar** o agent de captura passando o **identificador da sessão ativa** como `session` da captura. Quando o agent **não** está em execução, o status exposto à UI MUST permitir esse start (modo direto ou equivalente) — MUST NOT classificar como “só guiado” apenas por ausência de handle de processo parado (analyze I1).
- **FR-002**: Com agent em execução em modo **direto** (processo controlado pelo shell) e sessão ativa definida, o shell MUST permitir **reiniciar** o agent (parar o processo **controlado** e iniciar de novo) com o identificador da sessão ativa atual.
- **FR-016**: Quando houver **mismatch conhecido** e o agent estiver em modo **direto**, o shell MUST exibir uma CTA explícita de **reiniciar o agent com a sessão ativa** (rótulo inequívoco). A CTA MUST executar o reinício de FR-002 **imediatamente**, sem diálogo de confirmação adicional. MUST NOT reiniciar o agent apenas porque o operador selecionou outra sessão na lista (FR-009).
- **FR-015**: Quando o agent estiver em execução **fora** do controle do shell (modo guiado / processo externo detectado), o shell MUST NOT forçar o encerramento desse processo para “alinhar” a sessão. MUST exibir orientação de **parada manual** e o comando (ou caminho Direct após parada) com a sessão ativa. MUST NOT iniciar uma segunda instância concorrente sem diagnóstico claro.
- **FR-003**: O shell MUST NOT iniciar o agent pela UI sem sessão ativa; MUST orientar o operador a selecionar ou criar uma sessão.
- **FR-004**: Em modo de controle **guiado**, o comando de orientação exibido MUST incluir o identificador da **sessão ativa** atual (quando houver sessão ativa).
- **FR-005**: O status do agent exposto à UI MUST incluir a **sessão do agent resolvida** quando conhecida. A resolução MUST seguir esta prioridade: **(1)** valor de `--session` (ou equivalente documentado) obtido da linha de comando do processo do agent em execução, se legível e não vazio; **(2)** identificador do último start bem-sucedido gerenciado pelo shell; **(3)** desconhecida. MUST NOT inventar id. Comparação com a sessão ativa para mismatch (FR-007) MUST usar igualdade exata de string do identificador resolvido.
- **FR-006**: O shell MUST exibir de forma legível a **sessão ativa (UI)** e a **sessão do agent** (ou “desconhecida” / “parado”).
- **FR-007**: Quando sessão ativa e sessão do agent forem ambas conhecidas e **diferentes**, o shell MUST exibir um **aviso de desalinhamento** visível sem depender de logs externos.
- **FR-008**: Quando as sessões forem iguais e conhecidas, o shell MUST NOT exibir o aviso de mismatch de FR-007.
- **FR-009**: Selecionar uma sessão na lista MUST atualizar feed de transcript e Assistente para essa sessão e MUST NOT, por si só, alterar o `session` de um agent já em execução. Com agent Direct e ids divergentes após a seleção, MUST aplicar FR-007 + FR-016 (banner + CTA), não reinício silencioso.
- **FR-010**: O painel Assistente MUST usar **estados vazios distintos** (sem interações), com esta precedência de diagnóstico:
  1. **Mismatch conhecido** (FR-007) — prioridade sobre hints de transcript;
  2. **Automático desligado** ou **nenhuma origem habilitada** — orientação de preferências;
  3. **Feed vazio** — “aguardando transcript” (ou equivalente);
  4. **Somente partials** (sem final elegível novo), automático ligado e origem elegível, sem mismatch — “aguardando trecho final”;
  5. **Há finais** mas nenhum classificado como pergunta elegível (019 FR-004 + origem) — “nenhuma pergunta elegível ainda”.
  MUST NOT usar um único genérico “Nenhuma interação ainda” como única mensagem quando um dos estados acima se aplica. Disparo continua só em finais (019 FR-003).
- **FR-011**: A suíte de verificação automatizada do shell MUST cobrir, no mínimo: (a) start do agent usa id da sessão ativa; (b) mismatch exibe aviso e match não exibe (incluindo caso em que a sessão do agent veio da linha de comando, não só de start gerenciado); (c) agent parado sem falso mismatch; (d) sessão do agent desconhecida quando cmdline e start gerenciado não resolvem; (e) agent externo (Guided) **não** é encerrado pelo shell e recebe orientação de parada manual + comando com sessão ativa; (f) seleção de outra sessão com agent Direct **não** reinicia sozinha e expõe banner + CTA de reinício; (g) CTA de reinício realinha o id; (h) estados vazios de FR-010 (partials / feed vazio / finais sem pergunta / auto off / mismatch prioritário); (i) fixture de trecho **final** elegível (pergunta + origem system) dispara a orquestração do Assistente conforme 019.
- **FR-012**: A documentação operacional (`docs/development/running.md` e/ou `docs/release/min-flow.md`) MUST registrar: regra do **mesmo sessionId** entre UI, agent e STT; que **selecionar na lista não reconfigura** agent em execução; exemplo PowerShell com UUID da sessão ativa; preferência por iniciar/reiniciar via UI quando modo direto estiver disponível.
- **FR-013**: Esta feature MUST NOT alterar o contrato `transcript-event.v2` nem a regra de que **somente trechos finais** disparam live-answer (019 FR-003), salvo ADR e ciclo de contrato separado.
- **FR-014**: Logs e painéis desta feature MUST NOT incluir segredos, áudio bruto ou saída completa do modelo; ids de sessão operacionais podem aparecer na UI e em logs de diagnóstico de nível apropriado.

### Key Entities

- **Sessão ativa (UI)**: identificador da sessão selecionada/criada no shell; escopo do feed de transcript e do Assistente.
- **Sessão do agent**: identificador com o qual a captura/STT está associada, resolvido por prioridade: linha de comando do processo (`--session`) → último start gerenciado pelo shell → desconhecida.
- **Estado de alinhamento de sessão**: enumeração lógica { alinhado, desalinhado, agent parado, sessão do agent desconhecida, sem sessão ativa }.
- **Aviso de mismatch**: superfície de UI que comunica desalinhamento entre sessão ativa e sessão do agent.
- **CTA reiniciar com sessão ativa**: ação explícita (modo Direct + mismatch ou equivalente de realinhamento) que para o processo controlado e inicia com o id da sessão ativa, **sem** passo de confirmação.
- **Estados vazios do Assistente**: conjunto de orientações sem interações — mismatch, preferências off, aguardando transcript, aguardando trecho final, nenhuma pergunta elegível (precedência em FR-010).
- **Controle do agent**: painel existente de iniciar/parar/orientação; estendido para restart com sessão ativa e exposição de sessionId.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em roteiro guiado com sessão ativa na UI, o operador inicia (ou reinicia) o agent **pela UI** (modo direto) e a captura usa o **mesmo** id da sessão ativa — verificado em teste automatizado com fake de start e em checklist manual quando houver host Windows.
- **SC-002**: Em **100%** dos casos de teste com sessão ativa ≠ sessão do agent (ambas conhecidas), o aviso de mismatch está presente; em **100%** dos casos com ids iguais, o aviso de mismatch está ausente.
- **SC-003**: Em testes automatizados de estado vazio: (a) só partials + auto apto → **aguardar trecho final**; (b) feed vazio + auto apto → **aguardando transcript**; (c) finais sem pergunta elegível → **nenhuma pergunta elegível**; (d) auto off → mensagem de preferência, não “aguardando final”; (e) mismatch conhecido tem prioridade sobre (a).
- **SC-004**: Em teste com final sintético elegível (pergunta + `system`) e ids coerentes, o Assistente **cria** interação (running/done/error) — não permanece vazio por desalinhamento.
- **SC-005**: Documentação operacional atualizada permite a um revisor localizar em **menos de 2 minutos** a regra do sessionId único e o aviso de que selecionar na lista não reconfigura o agent.
- **SC-006**: Com ids alinhados + final elegível + automático on + origem on + rota live-answer ok **ou** falha de provedor, o operador **não** interpreta “feed/Assistente vazios por sessão errada”; ou há interação no Assistente, ou erro de provedor legível, ou hint de aguardar final se só houver partials.

## Assumptions

- A feature **019-auto-answer-assistant** já define o painel Assistente, preferências por sessão, disparo só em finais e filtro por origem; esta fatia **não** reespecifica a orquestração completa — apenas o alinhamento operacional de sessão e a UX de diagnóstico (mismatch + aguardando final).
- O shell já possui (ou terá na 014/019) painel de agent com start/stop e modos Direct/Guided; esta feature estende esse controle e o status, não inventa um segundo agent manager.
- “Sessão do agent conhecida” = resolvida por FR-005 (cmdline `--session` se legível, senão último start gerenciado). Parsing de linha de comando é requisito desta fatia quando o SO expõe a cmdline do processo do agent.
- Agent iniciado **fora** do shell: se `--session` for legível na cmdline, mismatch funciona; se não for, “desconhecida”. Recuperação **sem** force-kill: parada manual + comando guiado / start Direct quando o processo já não estiver rodando.
- Confirmar se o pipeline STT→session-core emite finais no fluxo real é **validação/documentação** (P1 da issue), não mudança de contrato; se houver limitação, documentar em running/min-flow ou validation, sem expandir escopo para redesenhar o STT.
- Testes automatizados usam fakes/fixtures (P10); validação WASAPI real permanece manual em host Windows.

## Out of Scope

- Alterar contrato `transcript-event.v2` (parcial/final) sem ADR.
- Classificador avançado de pergunta / turn-taking (roadmap R2 além da heurística da 019).
- Auto-start de Docker, STT ou session-core a partir do shell.
- Multi-agent / multi-sessão de captura em paralelo no mesmo shell.
- AEC acústico ou mudança de supressão de eco.
- Redesign completo do painel de agent além do necessário para sessionId, mismatch e restart.
- Marketplace de provedores, billing ou mudanças na rota `live-answer` em si.

## Dependencies

- `specs/019-auto-answer-assistant` — regras de disparo, painel Assistente, preferências.
- Shell desktop com session picker e controle de agent (014 / implementação corrente).
- Session-core com listagem/criação de sessão e feed de transcript por `sessionId`.
- Agent Windows aceitando `--session <id>` (já existente).
- Docs `docs/development/running.md` e `docs/release/min-flow.md` como alvos de atualização documental.
