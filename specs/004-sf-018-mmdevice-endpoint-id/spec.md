# Feature Specification: Identidade persistente de dispositivos via MMDevice endpoint ID (SF-018)

**Feature Branch**: `feature/sf-018-sf-018-identidade-persistente-de-dispositivos-co`

**Created**: 2026-07-19

**Status**: Draft (formalização retrospectiva — implementação piloto já presente no código)

**Input**: User description: "004" (formalizar a feature existente em `specs/004-sf-018-mmdevice-endpoint-id`)

**Referências**: Issue #8 (ou equivalente) · Umbrella `specs/001-streaming-foundation/` · ADR `docs/adr/0011-mmdevice-endpoint-identity.md` · Evidência `docs/validation/sf-018-windows.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Canal preso ao dispositivo certo mesmo após reboot e hot-plug (Priority: P1)

Um operador configura um canal de áudio apontando para o identificador estável do endpoint Windows (`device.endpointId`) em vez do índice numérico. Após reiniciar a máquina, plugar/desplugar USB, conectar Bluetooth ou atualizar driver — eventos que reordenam os índices de enumeração — o canal continua capturando exatamente o dispositivo pretendido, porque a resolução para o índice atual acontece no início de cada captura.

**Why this priority**: É o problema central da feature. Índices de enumeração mudam sem aviso e perfis baseados em `index`/`nameRegex`/`default` podem capturar o dispositivo errado silenciosamente, corrompendo a transcrição da sessão inteira.

**Independent Test**: Configurar um perfil com `endpointId`, capturar, reordenar os dispositivos (reboot ou hot-plug de outro dispositivo) e capturar de novo: o mesmo endpoint físico deve ser aberto nas duas execuções. Em ambiente sem hardware, testável com fakes de provider e correlação.

**Acceptance Scenarios**:

1. **Given** um perfil com `device.endpointId` válido e ativo, **When** a captura inicia, **Then** o endpoint é resolvido para o índice de enumeração **atual** e o stream abre nesse dispositivo (o `endpointId` é usado para abrir o stream, não é metadado decorativo).
2. **Given** que a ordem de enumeração mudou desde a última execução (reboot, hot-plug, Bluetooth), **When** a captura inicia com o mesmo perfil, **Then** o mesmo endpoint físico é selecionado, ainda que seu índice numérico seja outro.
3. **Given** um canal de loopback configurado por `endpointId`, **When** a captura inicia, **Then** a seleção usa o endpoint de reprodução (render) original — o dispositivo `[Loopback]` correlaciona ao endpoint render correspondente.

---

### User Story 2 - Falha explícita e diagnóstico acionável quando o endpoint não resolve (Priority: P2)

Um operador cujo perfil referencia um endpoint que não existe mais, está desabilitado/inativo, tem fluxo incompatível com o tipo de captura, ou está ativo porém sem correlação com um dispositivo de captura, recebe um erro claro e distinto para cada situação — nunca uma degradação silenciosa para outro dispositivo. As mensagens indicam alternativas úteis (ex.: consultar a listagem de dispositivos em formato estruturado). A listagem de dispositivos exibe o `endpointId` correlacionado de cada dispositivo para que o operador copie o identificador correto para o perfil.

**Why this priority**: Sem falha explícita, o sistema volta ao problema original — capturar o dispositivo errado sem erro. O princípio P7 da constituição proíbe fallback silencioso quando `endpointId` foi solicitado e não resolve.

**Independent Test**: Com fakes de provider em CI, provocar cada modo de falha (inexistente, inativo, fluxo incompatível, ativo sem correlação) e verificar que cada um produz mensagem distinta e que nenhum abre stream em dispositivo alternativo.

**Acceptance Scenarios**:

1. **Given** um perfil com `endpointId` inexistente, **When** a captura inicia, **Then** a inicialização falha com mensagem específica de endpoint não encontrado e sugestão de como listar os dispositivos disponíveis.
2. **Given** um perfil com `endpointId` de endpoint desabilitado/inativo, **When** a captura inicia, **Then** a falha indica que o endpoint existe porém está inativo — mensagem distinta do caso "inexistente".
3. **Given** um `endpointId` ativo mas sem correlação com dispositivo de captura enumerável, **When** a captura inicia, **Then** a falha indica ausência de correlação — mensagem distinta dos casos anteriores.
4. **Given** qualquer um dos modos de falha acima, **When** a resolução falha, **Then** nenhum fallback para `index`/`nameRegex`/`default` ocorre.
5. **Given** o comando de listagem de dispositivos, **When** executado no Windows, **Then** cada dispositivo exibe seu `endpointId` correlacionado quando a correlação for possível.

---

### User Story 3 - Compatibilidade com perfis legados e consumidores downstream (Priority: P3)

Equipes com perfis existentes baseados em `index`, `nameRegex` ou `default` continuam operando sem nenhuma alteração. Um perfil pode declarar `endpointId` junto de `index` no mesmo YAML: agentes novos priorizam `endpointId`; agentes antigos ignoram a chave nova. Consumidores dos eventos de transcrição (dashboard, session-core) passam a receber o `endpointId` como campo aditivo opcional/anulável no evento v2 e na conexão de áudio, sem quebra de contrato.

**Why this priority**: Compatibilidade é pré-condição de adoção incremental, mas não entrega valor novo por si só — depende das histórias P1/P2 para ter razão de existir.

**Independent Test**: Rodar a suíte de perfis legados sem modificação (`agents/windows-audio-agent/tests/test_profiles.py`, casos sem `endpointId`, e os seletores `index`/`nameRegex`/`default` preexistentes de `devices.resolve_device`) e verificar resolução idêntica ao comportamento anterior; validar round-trip de perfil com as duas chaves; validar o evento v2 contra o schema com e sem o campo novo.

**Acceptance Scenarios**:

1. **Given** um perfil legado somente com `index`, `nameRegex` ou `default`, **When** a captura inicia, **Then** a resolução se comporta exatamente como antes da feature.
2. **Given** um perfil com `endpointId` e `index` simultâneos, **When** um agente novo resolve o dispositivo, **Then** `endpointId` tem prioridade sobre `index` e sobre `default`/`nameRegex`.
3. **Given** o mesmo perfil com as duas chaves, **When** um agente antigo o carrega, **Then** a chave `endpointId` é ignorada sem erro.
4. **Given** uma captura com endpoint conhecido, **When** eventos v2 são emitidos, **Then** `device.endpointId` está presente; **Given** endpoint desconhecido, **Then** o campo é omitido ou nulo e o evento permanece válido no schema v2.

---

### Edge Cases

- Dois dispositivos com o mesmo nome amigável (FriendlyName duplicado): a correlação nome+ordem é heurística — o sistema emite WARNING e desempata pela ordem de enumeração.
- Endpoint desaparece entre a enumeração e a abertura do stream (TOCTOU): falha explícita nesta feature; mitigação por listener de hot-plug fica para SF-019.
- `endpointId` muda após reinstalação de driver: tratado como endpoint inexistente, com mensagem acionável para o operador atualizar o perfil.
- Execução fora do Windows (Linux/CI): o provider de endpoints degrada para um provider nulo — nenhuma dependência específica de Windows é carregada e a listagem simplesmente não exibe `endpointId`.
- Canal de loopback: o dispositivo virtual `[Loopback]` deve correlacionar ao endpoint de render original, não a um endpoint de captura.
- Perfil com combinação inválida de seletores: a validação de perfil rejeita a combinação com mensagem clara antes de iniciar captura.
- Dois canais habilitados referenciam o mesmo `endpointId`: permitido — cada canal abre seu próprio processo isolado (ADR-0007) contra o mesmo endpoint; nenhuma deduplicação é feita entre canais.
- Falha de resolução de `endpointId` em um canal durante a execução do agente: o worker daquele canal encerra sem reentrar no laço de reconexão (FR-007), enquanto o supervisor (`run_agent`) mantém os demais canais em execução; o processo global só encerra com erro quando todos os canais tiverem falhado.
- `endpointId` vazio ou malformado na query do WebSocket de áudio (ex. agente legado ou plataforma sem correlação): o serviço de transcrição normaliza para `null`, nunca propaga uma string vazia distinta de nulo no evento v2.
- Endpoint que fica inativo **durante** uma captura já em andamento (diferente do TOCTOU entre resolução e abertura do stream, já listado acima): cai no laço de reconexão genérico do worker (backoff até 10s), sem detecção dedicada; notificação/recuperação de hot-plug fica para a SF-019.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A listagem de dispositivos MUST incluir o `endpointId` correlacionado de cada dispositivo quando a correlação for possível.
- **FR-002**: Um perfil com `device.endpointId` MUST resolver o índice de enumeração **atual** do dispositivo no início de cada captura, e esse índice MUST ser usado para abrir o stream. A resolução se repete a cada nova tentativa do laço de reconexão do worker e a cada novo processo worker — nunca reaproveita o índice resolvido em uma tentativa anterior.
- **FR-003**: Canais de loopback MUST selecionar pelo endpoint de reprodução (render) original — o dispositivo `[Loopback]` correlaciona ao render correspondente.
- **FR-004**: Perfis legados (`index`, `nameRegex`, `default`) MUST continuar válidos e com comportamento inalterado.
- **FR-005**: `endpointId` MUST poder coexistir com `index` no mesmo perfil YAML; agentes novos priorizam `endpointId` (`endpointId` > `index` > `default`/`nameRegex`, conforme P7/ADR-0011); agentes antigos ignoram a chave nova sem erro.
- **FR-006**: O evento de transcrição v2 e a query da conexão WebSocket de áudio MUST transportar `device.endpointId` quando conhecido, como campo aditivo opcional/anulável (sem breaking change do schema v2).
- **FR-007**: Quando `endpointId` foi solicitado e não resolve, o sistema MUST falhar de modo explícito com mensagens distintas para cada modo de falha — endpoint inexistente, endpoint inativo, fluxo incompatível e endpoint ativo sem correlação — e MUST NOT degradar silenciosamente para `index`/`nameRegex`/`default`. "Distinto" significa: mesma classe de exceção (erro de resolução), com um trecho de texto identificador exclusivo por modo, verificável por correspondência textual em teste — não há códigos de erro estruturados. "Falhar de modo explícito" significa que o processo worker do canal encerra (não entra no laço de reconexão genérico usado para erros transitórios de rede/stream); o supervisor detecta o encerramento e mantém os demais canais em execução (P6).
- **FR-008**: Mensagens de erro de resolução MUST indicar alternativas acionáveis (ex.: como obter a listagem estruturada de dispositivos) e MUST NOT conter segredos. No modo "endpoint ativo sem correlação", a alternativa sugerida também inclui `assistant-hub-audio probe` ou seleção manual por `index` como contorno.
- **FR-009**: A resolução por `endpointId` MUST estar disponível apenas no Windows; em outras plataformas o provider degrada para um provider nulo sem carregar dependências específicas de Windows. Um perfil com `endpointId` executado fora do Windows MUST falhar com a mesma mensagem de "endpoint inexistente" (o provider nulo nunca encontra correlação), sem tentativa de fallback.
- **FR-010**: Nomes amigáveis duplicados MUST gerar WARNING e desempate determinístico pela ordem de enumeração. O WARNING é emitido a cada resolução/captura (cada chamada de correlação), sem deduplicação entre tentativas.

### Key Entities

- **Endpoint de áudio (MMDevice)**: identidade estável de um dispositivo de áudio no Windows; atributos: `endpointId`, nome amigável, direção de fluxo (captura/render), estado (ativo/inativo).
- **Dispositivo enumerado (PortAudio)**: representação transitória do dispositivo na enumeração da biblioteca de captura; atributos: índice (volátil), nome, host API; correlacionado estruturalmente ao endpoint por fluxo, nome e ordem de enumeração.
- **Perfil de canal**: configuração YAML de um canal de captura; seletores de dispositivo: `endpointId`, `index`, `nameRegex`, `default`, com prioridade definida.
- **Evento de transcrição v2**: contrato versionado que carrega `channelId`, `sourceType` e metadados de dispositivo ponta a ponta; ganha o campo aditivo opcional/anulável `device.endpointId`.

### Fora de escopo

- Listener de hot-plug nativo (SF-019).
- Captura por processo/aplicativo (SF-020).
- Breaking change do schema (v3).
- Fallback silencioso de `endpointId` para `index`/`name` quando a resolução falha.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos cenários de validação Windows (reboot, hot-plug, Bluetooth, dispositivo desabilitado), o canal configurado por `endpointId` captura o dispositivo pretendido ou falha com mensagem explícita — nunca captura um dispositivo diferente do configurado.
- **SC-002**: Cada um dos quatro modos de falha de resolução (inexistente, inativo, fluxo incompatível, ativo sem correlação) produz mensagem distinta e identificável, verificado por teste automatizado.
- **SC-003**: 100% dos perfis legados existentes passam na suíte de testes sem modificação e sem mudança de comportamento.
- **SC-004**: A suíte de testes automatizada roda integralmente em CI Linux sem nenhum dispositivo de áudio físico e sem dependências específicas de Windows. Adicionalmente, um smoke Windows dedicado em CI (`windows-audio-agent-windows-smoke`) importa o provider MMDevice e executa o CLI sem hardware — não substitui a validação manual do SC-006.
- **SC-005**: Eventos v2 com e sem `device.endpointId` validam contra o schema v2 vigente (compatibilidade aditiva comprovada por teste de contrato).
- **SC-006**: A validação manual Windows está registrada em `docs/validation/sf-018-windows.md` com ambiente, commit, passos e resultado PASS (constituição P10). PASS exige que os valores observados (índice, endpointId, mensagem) correspondam aos registrados nas tabelas de Dispositivos/Perfil da mesma execução; qualquer divergência é FAIL.

## Assumptions

- Formalização retrospectiva: a implementação piloto já existe no código; esta spec descreve o comportamento acordado (ADR-0011) para fechar o gate G1 antes de Analyze/Validate.
- O identificador MMDevice é estável entre reboots e hot-plugs para o mesmo endpoint, exceto em reinstalação de driver — cenário tratado como endpoint inexistente, sem tentativa de recuperação automática.
- A correlação endpoint ↔ dispositivo enumerado é estrutural (fluxo, nome amigável, ordem de enumeração) e reconhecidamente heurística; não é apresentada como garantia absoluta.
- Testes automatizados usam fakes de provider (constituição P10 — sem dependência de hardware); cenários com hardware real são cobertos apenas pela validação manual documentada.
- A janela TOCTOU entre enumeração e abertura do stream é aceita nesta feature; mitigação chega com o listener de hot-plug (SF-019).
- O umbrella `specs/001-streaming-foundation/tasks.md` só é atualizado após o merge desta feature.
- Cobertura por camada: FR-001/002/004/005/006/007/008/010 e SC-002/003/004/005 são verificados por pytest com fakes (Linux/CI); FR-003/FR-009 e SC-001/SC-006 dependem da validação manual Windows documentada em `docs/validation/sf-018-windows.md`.
