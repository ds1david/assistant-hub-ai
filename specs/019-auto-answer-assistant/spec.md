# Feature Specification: Assistente de respostas automáticas no desktop (live-answer)

**Feature Branch**: `019-auto-answer-assistant`

**Created**: 2026-07-25

**Status**: Ready

**Input**: User description: "Não estou conseguindo visualizar a interação com o ChatGPT. Quero respostas de forma automática a partir da conversa; se houver mais de uma pergunta enquanto uma resposta estiver em execução, o app deve perguntar se desejo cancelar a resposta da pergunta anterior ou aguardar a pergunta em execução terminar. Seguir o fluxo Speckit já usado no repositório."

**Referências**: Visão do produto (`docs/vision.md` — sugestões sob controle do usuário; MVP não é resposta invisível em processo seletivo real) · Roadmap R2 (Conversation Intelligence / sugestões) · `specs/014-issue-35-desktop-tauri-shell-local` (shell desktop) · `specs/015-issue-37-ai-provider-hub` (hub de provedores, teste de conexão e invocação) · `specs/017-issue-40-invocation-sourcetype` (origem de canal no resultado de invoke) · Perfil de rotas de IA com capacidade de resposta ao vivo (rota de política já prevista no hub) · Constituição P1 (spec antes de código de domínio), P5 (origem/canal), P9 (privacidade).

## Clarifications

### Session 2026-07-25 (defaults documentados — sem bloqueio de clarificação)

Defaults adotados nesta spec a partir do pedido do usuário e do estado do produto; alteráveis em `/speckit-clarify` se o operador discordar.

- **Disparo automático**: trechos **finais** do transcript que o produto reconhece como **pergunta** (não parciais intermediários).
- **Onde ver a interação**: painel dedicado de **Assistente** no shell desktop (pergunta detectada + resposta gerada + estado), distinto do feed de transcript e do painel de configuração de provedores.
- **Rota de política**: usa a rota de resposta ao vivo já prevista no hub de provedores (nome de rota de produto alinhado ao perfil de provedores, ex. resposta em tempo de conversa), sem o operador escolher provedor manualmente a cada pergunta.
- **Conflito de perguntas**: no máximo **uma** resposta em geração por vez; nova pergunta enquanto há geração em andamento **sempre** exige escolha explícita: cancelar a anterior **ou** aguardar a atual terminar.
- **Cancelamento**: do ponto de vista do usuário, a resposta anterior deixa de ser a resposta “ativa” e a nova pergunta passa a ser a prioridade; o produto não deve apresentar a resposta cancelada como se fosse a resposta vigente.
- **Aguardar**: a nova pergunta fica em fila (a mais recente prevalece se várias chegarem enquanto se espera a decisão ou a conclusão); ao terminar a atual, a enfileirada inicia sem novo diálogo, salvo se outra pergunta chegar no meio e reabrir o conflito.
- **Ligar/desligar** e demais preferências do Assistente: **por sessão** (automático, origens, modo de entrada); default em sessão sem preferência: automático **desligado**, só **sistema**, **contexto recente**.
- **Sessão**: o operador **seleciona** a sessão ativa a partir de uma **lista** ou **cria** uma nova; a mesma identidade deve ser usada pela captura/transcrição para o automático reagir ao transcript.

### Session 2026-07-25 (clarify)

- Q: Quais origens de canal disparam o automático? → A: Operador escolhe na UI quais origens disparam; **default: sistema** (`system`).
- Q: O que entra no pedido ao modelo? → A: Operador escolhe na UI: **só pergunta** vs **pergunta + contexto recente** do transcript; **default: com contexto recente** (janela curta de trechos finais).
- Q: Automático ligado ou desligado ao abrir a sessão? → A: Preferência do automático é **por sessão** (refinado na Q seguinte); sessão **sem** preferência gravada inicia com automático **desligado**.
- Q: Como nasce a sessão ativa no shell? → A: Shell **lista sessões** disponíveis e o operador **escolhe** qual reabrir **ou** criar nova.
- Q: Preferências do Assistente além do automático (origens, modo de entrada)? → A: Persistir **tudo por sessão** (automático, origens de disparo, modo de entrada); **não** como preferência global do app. Sessão nova ou sem preferências → defaults da spec.

### Session 2026-07-25 (023 question-detection-quality)

- **019 FR-004** (heurística lexical canônica original desta spec) fica **superseded no shell** pela **FR-002** de `specs/023-issue-52-question-detection-quality/` (imperativos de entrevista, vocativo, word boundary, segmentos após `.!`). Orquestração de turns, conflito cancel/wait, rota `live-answer` e defaults de privacidade (auto off) **permanecem** definidos aqui.
- Preferências adicionais (`interviewMode`, `useProsody`, `prosodyThreshold`) e gate multimodal: ver 023.

### Session 2026-07-26 (028 interview context / style)

- No modo **pergunta + contexto recente**, o builder de input **pode** incluir finais `microphone` além de `system` quando a preferência **incluir minha voz no contexto** está ON (default ON) — ver `specs/028-issue-61-live-answer-interview-mode/`. **Disparo** continua filtrado só por `enabledSourceTypes`.
- Com `interviewMode` ON, o input do invoke recebe bloco de instrução de resposta em **1ª pessoa** (028).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver respostas automáticas no shell a partir do transcript (Priority: P1)

Um operador em treino ou validação do produto inicia uma sessão com captura e transcrição. Quando alguém na conversa faz uma **pergunta** que aparece como trecho final no transcript, o assistente **dispara sozinho** uma resposta (via política de provedores já configurada) e a **mostra no painel do Assistente** — pergunta, resposta (ou erro claro), e indicação de que está gerando.

**Why this priority**: Resolve a falha de produto relatada (“não consigo visualizar a interação com o ChatGPT”): hoje só há config/teste de provedor e transcript, sem superfície de pergunta/resposta.

**Independent Test**: Com sessão ativa, transcript recebendo um trecho final reconhecido como pergunta, e pelo menos um provedor habilitado na rota de resposta ao vivo, observar no painel do Assistente a pergunta, o estado “gerando” e depois a resposta (ou erro tipado legível), sem o operador clicar em “testar conexão” nem invocar API manualmente.

**Acceptance Scenarios**:

1. **Given** o automático ligado, sessão ativa alinhada à captura, e um trecho **final** de transcript reconhecido como pergunta, **When** o feed de transcript incorpora esse trecho, **Then** o painel do Assistente mostra a pergunta e inicia a geração de resposta sem ação manual adicional.
2. **Given** uma geração bem-sucedida, **When** o operador olha o painel do Assistente, **Then** vê a resposta textual associada àquela pergunta e consegue distinguir pergunta de resposta.
3. **Given** falha do provedor (ex.: autenticação, timeout, sem créditos, rota sem provedor habilitado), **When** a geração termina em erro, **Then** o painel mostra falha legível (tipo e/ou detalhe seguro) **sem** derrubar o shell nem interromper o feed de transcript.
4. **Given** o automático **desligado**, **When** novos trechos finais de pergunta chegam ao transcript, **Then** o Assistente **não** inicia novas gerações.
4b. **Given** uma sessão **nova** (ou sem preferências do Assistente gravadas), **When** ela se torna ativa, **Then** o modo automático inicia **desligado**, origens default (só sistema) e modo de entrada default (contexto recente).
4c. **Given** o operador configurou automático/origens/modo na sessão S e trocou para outra sessão T, **When** volta a selecionar S, **Then** as preferências de S são restauradas (não as de T nem um default global do app).
5. **Given** o automático ligado e apenas a origem **sistema** habilitada para disparo (default), **When** um trecho final de pergunta chega no canal de microfone, **Then** o Assistente **não** inicia geração.
6. **Given** o operador habilitou também a origem **microfone** no seletor de origens, **When** um trecho final de pergunta chega no microfone, **Then** o Assistente pode iniciar geração como faria para sistema.
7. **Given** o modo de contexto **com contexto recente** (default), **When** uma pergunta dispara geração, **Then** o pedido ao modelo inclui a pergunta e uma janela curta de trechos finais recentes da sessão (além da própria pergunta).
8. **Given** o operador escolheu **só pergunta**, **When** uma pergunta dispara geração, **Then** o pedido ao modelo contém o texto da pergunta candidata **sem** anexar histórico de transcript.

---

### User Story 2 - Conflito: cancelar resposta anterior ou aguardar (Priority: P1)

Enquanto uma resposta ainda está sendo gerada, chega **outra** pergunta no transcript. O produto **não** inicia a segunda resposta em silêncio nem descarta a primeira sem avisar. Em vez disso, apresenta um diálogo (ou equivalente inequívoco) com duas opções: **cancelar a resposta da pergunta anterior** e responder a nova, **ou aguardar** a resposta em execução terminar e só então tratar a nova pergunta.

**Why this priority**: Requisito explícito do usuário; evita corrida confusa de respostas e deixa o operador no controle (alinhado à visão de “sugestões sob controle”).

**Independent Test**: Simular (ou produzir) uma geração em andamento e, antes dela terminar, injetar uma segunda pergunta final; verificar que o diálogo de conflito aparece; testar os dois caminhos (cancelar e aguardar) e o histórico resultante no painel.

**Acceptance Scenarios**:

1. **Given** uma resposta em geração para a pergunta A, **When** a pergunta B (trecho final reconhecido como pergunta) chega ao transcript, **Then** o produto exibe um conflito claro mostrando, no mínimo, o sentido de “em execução” (A) e “nova” (B), com ações **Cancelar anterior** e **Aguardar**.
2. **Given** o diálogo de conflito aberto, **When** o operador escolhe **Cancelar a anterior**, **Then** a geração de A deixa de ser a resposta ativa (marcada como cancelada / não vigente), a pergunta B inicia (ou torna-se a geração em curso), e uma eventual resposta tardia de A **não** substitui a resposta de B no painel.
3. **Given** o diálogo de conflito aberto, **When** o operador escolhe **Aguardar**, **Then** a geração de A continua; B fica em fila/pendente de forma visível; ao concluir A com sucesso ou erro, B inicia automaticamente **sem** exigir novo clique no diálogo (salvo se outra pergunta C reabrir conflito).
4. **Given** o operador já escolheu **Aguardar** para B e A ainda roda, **When** chega a pergunta C, **Then** o produto reapresenta o conflito (atual vs. nova), em vez de enfileirar C em silêncio sem escolha.

---

### User Story 3 - Escolher ou criar a sessão ativa (Priority: P2)

O shell, com session-core acessível, **lista** as sessões conhecidas e permite ao operador **selecionar** uma para reabrir ou **criar** uma nova. A sessão escolhida torna-se a sessão ativa do feed de transcript e do Assistente. O identificador fica visível para alinhar a captura. Se o session-core estiver indisponível, o status deixa isso claro e o Assistente não finge sucesso.

**Why this priority**: Sem sessão compartilhada e escolhida de forma explícita, o automático nunca dispara de forma útil; listar/criar é o pré-requisito operacional da US1.

**Independent Test**: Com session-core no ar e ao menos zero ou mais sessões existentes: abrir o shell, ver a lista (ou estado vazio), criar uma sessão, ver id ativo; reabrir o shell e selecionar a mesma sessão; com session-core fora, ver erro/desconectado sem crash.

**Acceptance Scenarios**:

1. **Given** session-core acessível e nenhuma sessão ainda escolhida, **When** o operador abre o fluxo de sessão no shell, **Then** vê a **lista** de sessões disponíveis (possivelmente vazia) e ações para **criar nova** ou **selecionar** uma existente.
2. **Given** o operador cria uma nova sessão, **When** a criação conclui, **Then** essa sessão torna-se a **sessão ativa** do transcript e do Assistente, com identificador visível.
3. **Given** uma ou mais sessões já existentes, **When** o operador seleciona uma da lista, **Then** o feed e o Assistente passam a usar essa sessão (histórico de transcript daquela sessão; preferências do Assistente **daquela** sessão).
4. **Given** session-core inacessível, **When** o operador usa o shell, **Then** o status indica falha de conexão; lista/criação não reportam sucesso falso e o Assistente não finge respostas automáticas ativas.
5. **Given** captura enviando transcript para o **mesmo** identificador da sessão ativa na UI, **When** perguntas finais elegíveis chegam, **Then** o Assistente (com automático ligado e origens/modo conforme preferências **da sessão**) pode reagir a esses trechos.
6. **Given** preferências distintas gravadas para sessões S e T, **When** o operador alterna S → T → S, **Then** cada troca restaura apenas as preferências da sessão selecionada.

---

### User Story 4 - Histórico legível da interação na sessão corrente (Priority: P3)

O operador revisa na mesma tela a sequência de interações do Assistente na sessão corrente (perguntas, respostas, canceladas, erros, itens em fila), sem precisar de ferramentas externas.

**Why this priority**: Complementa a visualização “tipo ChatGPT” de forma mínima; não bloqueia o MVP se US1/US2 estiverem sólidas.

**Independent Test**: Produzir pelo menos duas interações (sucesso e cancelamento ou erro) e verificar ordem e estados no painel.

**Acceptance Scenarios**:

1. **Given** várias interações na sessão corrente, **When** o operador rola o painel do Assistente, **Then** consegue identificar cada pergunta e o desfecho (resposta, erro, cancelada, na fila, gerando).
2. **Given** conteúdo de transcript/resposta com caracteres especiais, **When** o painel renderiza o texto, **Then** o texto aparece de forma segura (sem quebrar a UI por injeção de marcação).

---

### Edge Cases

- **Trecho parcial** que parece pergunta: **não** dispara automático; só trechos **finais**.
- **Trecho final que não é pergunta** (afirmação, “ok”, ruído curto): **não** dispara.
- **Origem de canal não habilitada** no seletor do operador (ex.: microfone com default só sistema): trecho final mesmo em forma de pergunta **não** dispara.
- **Nenhuma origem habilitada** no seletor: automático ligado não dispara até o operador habilitar ao menos uma origem.
- **Contexto recente sem trechos anteriores**: pedido usa só a pergunta (equivalente funcional a “só pergunta” naquele instante); não inventa histórico.
- **Janela de contexto**: tamanho máximo fixo e documentado nos testes (trechos finais e/ou caracteres); trechos além do limite são omitidos (mais antigos saem primeiro).
- **Mesmo trecho reprocessado** no poll do feed: **não** gera segunda invocação (idempotência por identidade do trecho).
- **Automático desligado no meio de uma geração**: a geração em curso pode concluir e ser exibida; **novas** perguntas não disparam até religar (comportamento documentado).
- **Várias perguntas no mesmo ciclo de atualização do feed**: a primeira ocupa a geração; as demais entram na lógica de conflito/fila (última pendente prevalece se o operador ainda não decidiu).
- **Provedor / rota indisponível**: erro no painel; transcript e agent continuam.
- **Resposta cancelada que chega tarde**: **não** sobrescreve a interação vigente da pergunta mais nova.
- **Sem sessão selecionada**: Assistente e feed não processam automático; UI orienta a listar/criar/selecionar sessão.
- **Lista vazia**: operador ainda pode criar nova sessão.
- **Sem captura / feed vazio**: painel vazio com orientação de que perguntas finais no transcript disparam o automático.
- **Operador não responde ao diálogo de conflito**: a geração atual continua; a nova permanece pendente até decisão; não inicia a nova em silêncio.
- **Conteúdo sensível**: respostas e perguntas na UI local; logs de produto **não** devem registrar saída completa do modelo nem segredos (alinhado ao hub existente).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O shell desktop MUST exibir um **painel de Assistente** onde o operador visualiza interações pergunta/resposta (e estados intermediários) da sessão corrente.
- **FR-002**: Com o modo automático **ligado**, o sistema MUST iniciar uma geração de resposta quando um **trecho final** do transcript da sessão ativa for reconhecido como **pergunta** **e** a **origem do canal** (`sourceType`) estiver **habilitada** no seletor do operador, sem exigir clique manual por pergunta. MUST NOT disparar para trechos cuja origem esteja desabilitada no seletor (ou origem desconhecida/ausente), mesmo que o texto seja reconhecido como pergunta.
- **FR-003**: O sistema MUST NOT disparar automático a partir de trechos **parciais** do transcript.
- **FR-004**: O reconhecimento de “pergunta” MUST ser determinístico e testável. Um trecho `Final` MUST ser classificado como pergunta se, após `trim`: (1) o comprimento for **≥ 8** caracteres; **e** (2) contiver o caractere `?` **ou** começar (case-insensitive) com um prefixo interrogativo da lista canônica — **pt**: `o que`, `qual`, `quais`, `quem`, `quando`, `onde`, `por que`, `porque`, `como`, `será que`; **en**: `what`, `which`, `who`, `when`, `where`, `why`, `how`, `is `, `are `, `do `, `does `, `can `, `could `, `would `. MUST rejeitar em testes exemplos de não-pergunta (ex.: `"ok"`, `"sim"`, `"entendi"`, frases sem `?` e sem prefixo, textos com comprimento &lt; 8).
- **FR-020**: O operador MUST poder escolher na UI do Assistente quais **origens de canal** disparam o automático, usando o vocabulário canônico de transcript (`microphone`, `system`). O **default** MUST ser somente **sistema** habilitado; microfone desabilitado até o operador optar por habilitá-lo.
- **FR-021**: *(fundido em FR-002 — origem desabilitada ou desconhecida não dispara.)* O seletor de origens (FR-020) e o filtro de elegibilidade de FR-002 são a fonte única desta regra.
- **FR-022**: O operador MUST poder escolher na UI o **modo de entrada** da geração: **(a) só pergunta** ou **(b) pergunta + contexto recente** do transcript da sessão. O **default** MUST ser **(b)**.
- **FR-023**: No modo **contexto recente**, o sistema MUST montar o pedido com a pergunta candidata e uma **janela curta** de trechos **finais** recentes da sessão (limite máximo fixo de trechos e/ou caracteres, verificável em teste). MUST NOT enviar o transcript completo da sessão nem áudio bruto.
- **FR-024**: No modo **só pergunta**, o sistema MUST montar o pedido com o texto da pergunta candidata sem anexar outros trechos do transcript.
- **FR-005**: A geração MUST usar a **rota de política de resposta ao vivo** do hub de provedores já configurada (primário + fallbacks do perfil), não a escolha ad hoc de um único provedor na UI a cada pergunta.
- **FR-006**: Enquanto uma geração estiver em curso, o sistema MUST permitir **no máximo uma** geração ativa; uma nova pergunta MUST NOT iniciar outra geração sem a decisão do operador no fluxo de conflito (FR-007).
- **FR-007**: Ao detectar nova pergunta com geração em curso, o sistema MUST apresentar escolha explícita: **(a)** cancelar a resposta da pergunta anterior e priorizar a nova, **ou (b)** aguardar a resposta em execução terminar.
- **FR-008**: Na opção **cancelar**, o sistema MUST marcar a interação anterior como não vigente (cancelada) e MUST NOT aplicar resposta tardia da anterior como se fosse a resposta atual da nova pergunta.
- **FR-009**: Na opção **aguardar**, o sistema MUST manter a geração atual, manter a nova pergunta em estado de fila/pendente **visível**, e MUST iniciar a pendente ao término da atual (sucesso ou erro), salvo novo conflito.
- **FR-010**: Se, após **aguardar**, outra pergunta chegar ainda com geração em curso, o sistema MUST reabrir o fluxo de conflito (FR-007) em vez de enfileirar silenciosamente sem escolha.
- **FR-011**: O operador MUST poder **ligar e desligar** o modo automático na UI; desligado implica não iniciar novas gerações automáticas.
- **FR-025**: O sistema MUST **persistir por sessão** as preferências do Assistente: modo automático, origens de disparo e modo de entrada. Ao **criar** sessão ou ao ativar sessão **sem** preferências gravadas, MUST aplicar defaults: automático **desligado**, origem **system** apenas, modo **question-plus-recent-context**. Ao **selecionar** uma sessão com preferências gravadas, MUST restaurar as daquela sessão (MUST NOT aplicar preferências de outra sessão nem um único default global do app para todas as sessões).
- **FR-012**: O painel MUST mostrar estados distintos: gerando, concluído com resposta, erro, cancelado, na fila (conforme aplicável).
- **FR-013**: Em erro de geração, o painel MUST mostrar mensagem legível (tipo e/ou detalhe seguro), sem expor segredos, tokens ou chaves.
- **FR-014**: O shell MUST operar o Assistente sobre uma **sessão ativa** coerente com o feed de transcript; se não houver sessão selecionada ou o núcleo de sessão estiver indisponível, o status MUST ser claro e o automático não deve reportar sucesso falso.
- **FR-026**: Com session-core acessível, o shell MUST **listar** sessões disponíveis ao operador e MUST permitir **selecionar** uma sessão existente como ativa **ou criar** uma nova sessão ativa. MUST NOT fixar silenciosamente uma sessão ativa sem escolha do operador nesta fatia.
- **FR-027**: O identificador da sessão ativa MUST ser **visível** no shell para o operador alinhar a captura/agent ao mesmo id.
- **FR-015**: Cada trecho de transcript já consumido para disparo MUST ser tratado de forma **idempotente** (mesmo trecho não gera múltiplas interações).
- **FR-016**: O feed de transcript e o painel de configuração/teste de provedores MUST permanecer utilizáveis independentemente do Assistente (falha do Assistente não silencia transcript nem config).
- **FR-017**: Texto de pergunta e resposta exibido na UI MUST ser apresentado de forma segura (sem interpretação perigosa de marcação vinda do modelo ou do transcript).
- **FR-018**: A suíte de verificação automatizada do shell MUST cobrir, no mínimo: detecção de pergunta vs. não-pergunta (FR-004), disparo a partir de trecho final novo, ausência de disparo em parcial, filtro por origem habilitada (default sistema; microfone off; origem desconhecida inelegível), montagem do pedido nos modos **só pergunta** e **contexto recente**, preferências **por sessão** (isolamento S vs T), conflito com **cancelar**, conflito com **aguardar**, **reabertura de conflito quando chega pergunta C após aguardar** (FR-010), e descarte de resposta cancelada tardia.
- **FR-019**: Logs de produto relacionados a esta feature MUST NOT incluir segredos nem o texto completo da saída do modelo; proveniência de provedor/latência pode seguir o padrão já adotado no hub.
- **FR-028**: Ao **criar** sessão pela UI do shell, o sistema MUST usar defaults de produto: `title = "Sessão local"` e `profileId = "interview-technical"` (nesta fatia a criação pode ser só o botão criar com esses defaults; edição livre de title/profile fica fora de escopo).
- **FR-029**: A lista de interações (turns) do painel Assistente MUST ser exibida com a **interação mais recente primeiro** (topo = último turn criado).

### Key Entities

- **Sessão ativa**: conversa corrente no shell, **escolhida ou criada** pelo operador a partir da lista; compartilha identidade com captura/transcrição e com invocações do Assistente.
- **Lista de sessões**: conjunto de sessões conhecidas pelo núcleo de sessão que o shell apresenta para seleção.
- **Trecho de transcript**: unidade de fala com ciclo de vida parcial/final, canal e texto; só finais elegíveis disparam o automático.
- **Pergunta candidata**: trecho final classificado como pergunta ainda não consumido para disparo.
- **Interação do Assistente** (`AssistantTurn` no código): registro na UI de uma pergunta, seu estado (gerando / na fila / concluída / erro / cancelada → `running` \| `queued` \| `done` \| `error` \| `cancelled`) e resposta ou erro associado.
- **Conflito de perguntas**: estado em que há geração em curso e ao menos uma nova pergunta candidata aguardando decisão cancelar vs. aguardar.
- **Preferências do Assistente (por sessão)** (`AssistantSessionPreferences`): conjunto { modo automático / `autoEnabled`, origens de disparo / `enabledSourceTypes`, modo de entrada / `inputMode` } associado ao id da sessão; defaults quando ausente: automático off, só `system`, `question-plus-recent-context`.
- **Modo automático**: ligado/desligado para disparo sem clique por pergunta (parte das preferências por sessão).
- **Seletor de origens de disparo**: quais `sourceType` canônicos (`microphone`, `system`) podem gerar pergunta candidata (parte das preferências por sessão).
- **Modo de entrada**: na UI “só pergunta” \| “pergunta + contexto recente”; no código `question-only` \| `question-plus-recent-context` (parte das preferências por sessão).
- **Janela de contexto recente**: conjunto limitado de trechos finais da sessão incluídos no pedido quando o modo de entrada usa contexto (≤12 finais ou ≤4000 chars).
- **Rota de resposta ao vivo**: na UI/produto “resposta ao vivo”; no hub/código rota `live-answer` (primário e fallbacks) usada para gerar a sugestão/resposta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em um roteiro de validação documentado (sessão ativa escolhida/criada + transcript com pergunta final + provedor/rota ok + automático ligado), o operador vê a **primeira** resposta automática no painel do Assistente **sem** invocar API manualmente e **sem** usar apenas “testar conexão”.
- **SC-011**: Em menos de 2 minutos no roteiro guiado, o operador consegue **listar**, **criar** e **selecionar** sessão e identificar o id ativo na UI.
- **SC-002**: Em 100% dos casos de teste de conflito (segunda pergunta durante geração), o produto **bloqueia** início silencioso da segunda geração e **exige** escolha cancelar ou aguardar antes de priorizar a nova pergunta.
- **SC-003**: No caminho **cancelar**, em testes automatizados, resposta tardia da pergunta cancelada **nunca** aparece como resposta vigente da pergunta nova.
- **SC-004**: No caminho **aguardar**, a pergunta enfileirada inicia após o término da atual em todos os casos de teste (sucesso ou erro da primeira), sem segundo diálogo se nenhuma pergunta adicional chegou.
- **SC-005**: Com automático desligado, **zero** novas gerações automáticas são iniciadas perante novas perguntas finais no transcript (testes automatizados).
- **SC-010**: Em testes com armazenamento de preferência **por sessão** injetável/fake: sessão sem preferência inicia com automático desligado + defaults; após gravar preferências em S e alternar para T e de volta a S, **100%** das preferências de S são restauradas sem vazar as de T.
- **SC-006**: Um operador consegue explicar, em menos de 1 minuto de uso guiado, **onde** ver a resposta automática e **o que fazer** quando duas perguntas competem (dialogo cancelar/aguardar).
- **SC-007**: Falha de provedor na geração automática **não** impede o feed de transcript de continuar atualizando na mesma sessão (verificado no roteiro de validação).
- **SC-008**: Com default de origens (somente sistema), **100%** dos casos de teste com pergunta final só no microfone **não** disparam geração; após habilitar microfone no seletor, o mesmo trecho-tipo **dispara** (testes automatizados).
- **SC-009**: Com default de entrada (contexto recente), testes automatizados verificam que o pedido inclui a pergunta **e** trechos finais recentes dentro do limite; com modo **só pergunta**, o pedido **não** inclui outros trechos.
- **SC-012**: Em testes de painel com ≥2 turns, o **primeiro** item no DOM da lista de interações é o turn **mais recente** (FR-029).

## Assumptions

- O hub de provedores (registro, rota de resposta ao vivo, invoke, erros tipados) e o shell desktop (status de sessão, feed de transcript, painel de provedores) já existem como base; esta feature **adiciona** a superfície e a orquestração de respostas automáticas, não reimplementa o hub.
- Credenciais e créditos de provedores (OpenAI, xAI/Grok, etc.) são responsabilidade operacional do usuário; a feature deve **exibir** falhas, não criar billing.
- “Como ChatGPT” nesta fatia significa **ver pergunta e resposta na UI**, com disparo automático a partir do transcript — **não** um clone completo de chat multi-turno livre, **não** leitura automática em voz, **não** resposta invisível em entrevista real (conforme visão do produto).
- Heurística de pergunta é deliberadamente simples na primeira fatia (regras canônicas em FR-004); classificador de “fim de pergunta” / turn-taking sofisticado (roadmap R2 completo) fica fora ou como evolução.
- Preferência de canal, modo de entrada e automático: **resolvidos no clarify** — seletor na UI; defaults (só sistema; contexto recente; automático off); **persistência por sessão** (FR-025), não global do app.
- Cancelamento é **semântico na UI e na orquestração** (não vigente / não aplicar resultado tardio); aborto forçado da chamada de rede no provedor é desejável se trivial, mas não é requisito de aceite se o descarte lógico estiver correto.
- Pode existir código exploratório no workspace anterior a esta spec; a implementação oficial MUST seguir esta spec + plan/tasks, reconciliando ou substituindo protótipos sob G2/G3.

## Out of Scope

- Chat multi-turno estilo produto consumidor com histórico editável, ramificações e system prompts avançados por persona.
- Detecção acústica de fim de pergunta, diarização de falantes ou consolidação semântica completa de turnos (além da heurística de trecho final + forma de pergunta).
- Resposta automática falada (TTS) ou inserção da resposta em softphones/Meet.
- Marketplace de provedores, billing, cotas na UI além de refletir erro do provedor.
- Alterar contratos de transcript v2 ou schema de perfil de provedores, salvo necessidade aditiva documentada em plan/ADR.
- Persistência de longo prazo do histórico do Assistente além da sessão corrente na UI (Memory Hub / busca semântica ficam para fatias futuras).
- Substituição do dashboard de STT no browser como UI principal do Assistente.

## Dependencies

- Session-core com hub de provedores e rota de resposta ao vivo configurável.
- Capacidade de **listar** e **criar** sessões no núcleo de sessão (se a listagem ainda não existir na API, o plan deve incluir extensão **aditiva** mínima — fora do Out of Scope de “não alterar contratos de transcript”, pois é API de sessão).
- Ingestão de eventos de transcript na sessão (feed consumível pelo shell).
- Shell desktop local (Tauri) como hospedeiro da UI.
- Agent de captura / STT operacionais para o fluxo ponta a ponta manual; testes automatizados da orquestração e UI **não** dependem de GPU nem de WASAPI real (P10).
