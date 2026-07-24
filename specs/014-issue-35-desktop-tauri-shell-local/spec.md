# Feature Specification: Desktop Tauri — shell local do Assistant Hub (R5)

**Feature Branch**: `feature/issue-35-r5-desktop-tauri-shell-local-do-assistant-hub`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Issue #35 — [R5] Desktop Tauri — shell local do Assistant Hub. App desktop Windows (Tauri) para operar agent, sessão e transcript sem depender só de CLI. Escopo: shell Tauri com status de canais/sessão; feed de transcript (session-core + Memory Hub); start/stop ou orientação clara do agent Windows; packaging básico documentado. Fora de escopo: AI Provider Hub completo; sync multi-device/cloud."

**Referências**: Issue #35 · Visão mais ampla em `specs/002-desktop-distribution/` (edições Developer/Desktop Lite/Desktop GPU, auto-update assinado, diagnóstico completo — fora do escopo desta fatia) · Consome `specs/007-sf-021-session-core-events/` (session-core ingere `transcript-event.v2`) e `specs/013-issue-29-memory-hub-persistence/` (sessões/eventos persistidos, API REST `/api/sessions`) · ADR-0003 (Windows host audio agent), ADR-0005 (WSL-first), ADR-0007 (workers de áudio isolados por endpoint WASAPI), ADR-0008 (supressão de eco no feed de transcrição, não AEC acústico) · AGENTS.md, seção "Distribuição desktop futura".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Acompanhar sessão e canais sem terminal (Priority: P1)

Um operador no Windows abre o shell desktop e, sem rodar nenhum comando de CLI ou consultar logs, vê o status atual da sessão (ativa, encerrada, sem sessão) e o status de cada canal de áudio conhecido (ex.: microfone, áudio de sistema), incluindo se o canal está recebendo eventos.

**Why this priority**: É o motivo de existir da issue #35 — hoje operar uma sessão exige CLI/terminal; sem essa visão mínima o shell não entrega valor de produto, e as demais histórias (feed de transcript, controle do agent) dependem de o operador já saber a que sessão/canal eles se referem.

**Independent Test**: Com o session-core rodando e uma sessão criada via API (`POST /api/sessions`), abrir o shell desktop e confirmar que a sessão aparece com seu status e que os canais que já receberam ao menos um evento aparecem identificados por `channelId`/`sourceType`/`label`, sem precisar consultar a API diretamente.

**Acceptance Scenarios**:

1. **Given** uma sessão ativa com eventos já registrados em 2 canais (`mic-1`/`microphone` e `sys-1`/`system_audio`), **When** o operador abre o shell, **Then** a sessão aparece como ativa e os dois canais aparecem listados com seus respectivos `channelId`, `sourceType` e `label`.
2. **Given** nenhuma sessão ativa no momento, **When** o operador abre o shell, **Then** a interface informa claramente a ausência de sessão ativa, sem erro nem tela em branco.
3. **Given** o session-core está indisponível (serviço parado ou inacessível), **When** o operador abre o shell, **Then** a interface informa que não conseguiu se conectar ao session-core, sem travar nem mostrar dado desatualizado como se fosse atual.

---

### User Story 2 - Ler o feed de transcript da sessão em tempo real (Priority: P1)

Enquanto a sessão está em andamento, o operador acompanha, dentro do próprio shell, o texto transcrito à medida que chega — sem precisar consultar API/CLI — identificando de qual canal cada trecho veio.

**Why this priority**: É o segundo valor central da issue (feed de transcript via session-core + Memory Hub) e é o que torna o shell útil durante uma conversa real, não só antes/depois dela; tem a mesma prioridade da User Story 1 porque ambas juntas formam o "modo de operação sem CLI" mínimo viável.

**Independent Test**: Com uma sessão ativa recebendo eventos `transcript-event.v2` sintéticos em mais de um canal, abrir o shell e verificar que os trechos de texto aparecem na tela, na ordem de chegada, cada um identificado com o canal de origem, sem misturar texto de canais diferentes em uma mesma linha.

**Acceptance Scenarios**:

1. **Given** uma sessão ativa exibida no shell, **When** um novo evento `transcript.final.v2` chega para o canal `mic-1`, **Then** o texto correspondente aparece no feed identificado como vindo de `mic-1`, sem exigir que o operador atualize a tela manualmente.
2. **Given** eventos chegando simultaneamente para dois canais diferentes, **When** o operador observa o feed, **Then** consegue distinguir visualmente qual trecho pertence a qual canal, preservando `channelId`, `sourceType` e `label`.
3. **Given** o operador fecha e reabre o shell durante a mesma sessão, **When** o shell reconecta, **Then** o feed é recarregado a partir do histórico já persistido da sessão (via Memory Hub), sem exigir que o operador perca o que já foi dito.

---

### User Story 3 - Controlar ou ser orientado sobre o agent de áudio Windows (Priority: P2)

O operador precisa saber se o agent de captura de áudio do Windows (`assistant-hub-audio`) está rodando para a sessão atual e, a partir do shell, ou inicia/encerra esse agent diretamente, ou recebe instruções claras e específicas de como fazê-lo quando o shell não pode controlar o processo diretamente.

**Why this priority**: É necessário para o shell ser autossuficiente no dia a dia, mas depende de a User Story 1 já existir (status de canal só faz sentido depois que a sessão é visível) — sem isso o operador ainda teria valor com US1+US2 sozinhas (ex.: agent já iniciado manualmente antes), então fica em P2.

**Independent Test**: Com o agent Windows parado, abrir o shell e confirmar que ele reporta "agent parado" com uma ação clara disponível (botão de start, quando suportado, ou instrução textual com o comando exato a rodar); repetir com o agent rodando e confirmar que o shell reflete "agent ativo".

**Acceptance Scenarios**:

1. **Given** o agent Windows não está em execução, **When** o operador abre o shell, **Then** a interface mostra o status "parado" e apresenta uma ação clara e específica para iniciá-lo (controle direto ou instrução textual reproduzível).
2. **Given** o agent Windows está em execução e vinculado à sessão atual, **When** o operador consulta o shell, **Then** a interface mostra o status "ativo" e, quando suportado, permite encerrá-lo a partir da própria interface.
3. **Given** o shell tentou iniciar o agent automaticamente e a tentativa falhou (ex.: binário ausente, dependência faltando), **When** a falha ocorre, **Then** o shell exibe uma mensagem específica do motivo da falha, nunca um erro genérico sem contexto acionável.

---

### User Story 4 - Instalar e rodar o shell de forma reproduzível (Priority: P3)

Um desenvolvedor ou um segundo operador, seguindo apenas a documentação do projeto, consegue empacotar (ou obter um pacote já empacotado) e rodar o shell desktop na máquina Windows de referência, sem depender de conhecimento tácito de quem construiu a feature.

**Why this priority**: É pré-condição para qualquer pessoa além do autor original usar o shell, mas só se torna relevante depois que o shell já existe e funciona (US1–US3); é o critério de aceite "build/reprodutível documentado" da issue.

**Independent Test**: Em uma máquina Windows de referência limpa (ou o mais próximo disso), seguir apenas os passos documentados para empacotar/instalar o shell e abri-lo, confirmando que o resultado é o mesmo shell funcional descrito nas demais histórias.

**Acceptance Scenarios**:

1. **Given** a documentação de packaging desta feature, **When** um desenvolvedor a segue do zero na máquina Windows de referência, **Then** obtém um shell executável funcional sem precisar de passos não documentados.
2. **Given** o shell empacotado, **When** é executado no modo Developer (WSL/Docker ainda presentes), **Then** o comportamento descrito em `AGENTS.md` ("o executável Windows será um shell, não um novo monólito de domínio") é preservado — o shell consome o session-core existente, não reimplementa suas responsabilidades.

---

### Edge Cases

- O que acontece se o session-core estiver rodando mas a sessão consultada não existir (ID inválido ou sessão de execução anterior sem registro persistido)? O shell mostra "sessão não encontrada", mesmo comportamento hoje já exposto pela API (`specs/013-issue-29-memory-hub-persistence/`).
- O que acontece se a conexão com o session-core cair no meio do feed de transcript (rede instável, serviço reiniciando)? O shell indica claramente que perdeu a conexão e tenta reconectar, sem descartar silenciosamente eventos nem exibir dado obsoleto como se fosse ao vivo.
- O que acontece se dois canais tiverem `label` igual mas `channelId`/`sourceType` diferentes? O shell distingue por `channelId`, nunca agrupa canais só pelo `label` (preserva a regra de não misturar canais antes da persistência, já estabelecida em `AGENTS.md`).
- O que acontece se o agent Windows já estiver rodando quando o shell é aberto pela primeira vez? O shell detecta o estado real (ativo) em vez de assumir "parado" por padrão.
- O que acontece se o operador fechar o shell enquanto o agent Windows e o session-core continuam rodando? Fechar o shell não deve necessariamente encerrar esses processos — este comportamento e sua justificativa MUST estar documentados, não implícitos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O shell desktop MUST exibir o status da sessão atual (ativa, encerrada ou ausente) sem exigir uso de CLI ou consulta manual à API pelo operador.
- **FR-002**: O shell desktop MUST listar os canais conhecidos da sessão atual com `channelId`, `sourceType` e `label`, refletindo os mesmos metadados preservados ponta a ponta pelo session-core (`specs/007-sf-021-session-core-events/`).
- **FR-003**: O shell desktop MUST exibir um feed de transcript da sessão atual, atualizado à medida que novos eventos `transcript-event.v2` chegam, sem exigir atualização manual da tela pelo operador.
- **FR-004**: O feed de transcript MUST identificar visualmente, para cada trecho de texto, o canal de origem (`channelId`/`sourceType`/`label`), sem misturar texto de canais diferentes em uma mesma entrada.
- **FR-005**: Ao reconectar ou reabrir durante uma sessão em andamento, o shell MUST recarregar o histórico do feed a partir do que já está persistido no Memory Hub (`specs/013-issue-29-memory-hub-persistence/`), preservando ordem cronológica.
- **FR-006**: O shell desktop MUST exibir o status atual do agent de áudio Windows (ativo/parado) para a sessão corrente.
- **FR-007**: O shell desktop MUST oferecer ao operador uma forma de agir sobre o agent Windows quando ele está parado — via controle direto de start/stop quando o shell detém o handle do processo (por tê-lo iniciado ele mesmo), ou via instrução textual específica e reproduzível quando o processo foi iniciado fora do shell ou seu handle não está disponível.
- **FR-008**: Quando uma tentativa de iniciar/parar o agent Windows a partir do shell falhar, o shell MUST exibir o motivo específico da falha, distinguindo ao menos: binário não encontrado, processo já em execução, permissão negada, e o processo encerrar imediatamente após iniciar — nunca uma mensagem genérica.
- **FR-009**: O shell desktop MUST informar claramente quando não consegue se conectar ao session-core, sem apresentar dados desatualizados como se fossem correntes.
- **FR-010**: O shell desktop MUST funcionar como consumidor das APIs já existentes do session-core (sessão e eventos) sem duplicar ou reimplementar a lógica de domínio de sessão/persistência já resolvida em `specs/007-sf-021-session-core-events/` e `specs/013-issue-29-memory-hub-persistence/`.
- **FR-011**: O projeto MUST documentar o processo de packaging/build do shell desktop de forma que seja reproduzível na máquina Windows de referência a partir apenas dessa documentação.
- **FR-012**: O shell desktop MUST continuar coexistindo com o modo Developer (WSL + Docker Compose) sem alterar ou quebrar esse fluxo existente, conforme `AGENTS.md`.
- **FR-013**: O shell desktop MUST NOT implementar ou expor configuração de provedores de IA (AI Provider Hub) — fora de escopo desta feature.
- **FR-014**: O shell desktop MUST NOT implementar sincronização multi-device ou dependência de nuvem — a operação é local, consistente com ADR-0005.

### Key Entities *(include if feature involves data)*

- **Shell desktop**: aplicação Windows (Tauri) que atua como cliente/visualização local; não é dona de dados de sessão, apenas consome e exibe o que o session-core/Memory Hub já expõem.
- **Status do agent Windows**: representação, no shell, de se o processo `assistant-hub-audio` está ativo ou parado para a sessão corrente; inclui a ação disponível (controle direto ou instrução) quando parado.
- **Feed de transcript**: sequência ordenada cronologicamente de trechos de texto exibidos no shell, cada um anotado com o canal de origem (`channelId`/`sourceType`/`label`), espelhando os eventos já persistidos/ingeridos pelo session-core.
- **Pacote de distribuição do shell**: artefato de build reproduzível do shell desktop para a máquina Windows de referência; o mecanismo concreto de empacotamento é decisão de arquitetura a ser definida em `/speckit-plan`, não desta especificação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um operador consegue verificar o status da sessão atual e de cada canal sem rodar nenhum comando de terminal, em menos de 10 segundos após abrir o shell.
- **SC-002**: 100% dos trechos de transcript exibidos no feed do shell preservam corretamente `channelId`, `sourceType` e `label` do evento de origem, verificado em teste automatizado.
- **SC-003**: Um operador consegue identificar se o agent Windows está ativo ou parado, e obter uma ação clara para agir sobre ele, sem consultar documentação externa ao shell.
- **SC-004**: Um desenvolvedor consegue, seguindo apenas a documentação de packaging desta feature, obter um shell funcional na máquina Windows de referência do zero.
- **SC-005**: O modo Developer (WSL/Docker) continua funcional e sem regressão após a introdução do shell desktop, verificado pela suíte de testes já existente do projeto.
- **SC-006**: 0% dos testes desta feature dependem de hardware de áudio físico ou GPU para validar status de sessão, feed de transcript ou status do agent (podem usar eventos sintéticos e um agent Windows simulado/mockado).

## Assumptions

- "MVP rodando no Windows de referência" (critério de aceite da issue) significa validação manual/documentada em uma máquina Windows real; testes automatizados desta feature rodam sem hardware de áudio físico (consistente com `specs/013-issue-29-memory-hub-persistence/`).
- O shell é um cliente do session-core já existente (`specs/007-sf-021-session-core-events/`, `specs/013-issue-29-memory-hub-persistence/`) — não introduz uma nova fonte de verdade para sessões/eventos, nem reimplementa a API `/api/sessions`.
- Controle direto de start/stop do agent Windows é desejável, mas quando não for tecnicamente viável no MVP, orientação textual clara e específica satisfaz o critério de aceite da issue ("start/stop ou orientação clara") — a escolha exata é decisão de arquitetura em `/speckit-plan`.
- Empacotamento básico nesta feature significa um artefato reproduzível e documentado; auto-update assinado, múltiplas edições (Developer/Desktop Lite/Desktop GPU) e instalador MSI/NSIS completos permanecem no escopo mais amplo de `specs/002-desktop-distribution/`, não desta fatia (R5).
- AI Provider Hub (`specs/003-ai-provider-hub/`) e sync multi-device/cloud não são afetados nem exercitados por esta feature, conforme delimitado explicitamente na issue #35.
- Fechar a janela do shell não implica, por padrão, encerrar o session-core ou o agent Windows; o comportamento exato de ciclo de vida entre shell e processos auxiliares é detalhado em `/speckit-plan`, mas o padrão de segurança é não matar processos que o operador não pediu para encerrar.
