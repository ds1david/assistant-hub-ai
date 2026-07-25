# Feature Specification: AI Provider Hub — registro e invocação de provedores pluggable (R6)

**Feature Branch**: `feature/issue-37-r6-ai-provider-hub-provedores-pluggable-sobre-se`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "Issue #37 — [R6] AI Provider Hub — provedores pluggable sobre sessão/transcript. Registrar e invocar provedores de IA (local/remoto) sobre contexto de sessão/transcript, com contrato versionado. Escopo: registro de provider + profile (schema existente ai-provider-profile.v1), invocação isolada (timeout, falha sem derrubar session-core), 1 provider real + 1 fake para testes, integração mínima com sessão/eventos (Memory Hub / session-core). Fora de escopo: treino de modelos, billing cloud, marketplace."

**Referências**: Issue #37 · `specs/003-ai-provider-hub/spec.md` (visão ampla do AI Provider Hub, ainda "futura" — esta spec cobre o recorte concreto de registro + invocação do R6) · ADR-0010 (registro de provedores e segredos externos) · `contracts/ai-provider-profile.v1.schema.json` · `docs/security/provider-secrets.md` · Depende de `specs/013-issue-29-memory-hub-persistence/` (Memory Hub / session-core) como fonte de contexto de sessão/transcript · Depende de `specs/014-issue-35-desktop-tauri-shell-local/` (shell desktop) como host da UI de provedores.

## Clarifications

### Session 2026-07-24

- Q: O AI Provider Hub, neste R6, expõe um endpoint/API novo e/ou UI desktop nova para invocar provedores, ou é apenas uma biblioteca/serviço interno chamado pelo session-core, sem nova superfície externa? → A: Ambos — endpoint de API novo e UI desktop nova nesta fatia.
- Q: Mudanças no perfil de provedores (via configuração, UI desktop ou API) precisam de reinício do processo para valer, ou devem valer sem reiniciar (hot-reload)? → A: Hot-reload — alterações no perfil valem sem reiniciar o processo.
- Q: Um rate limit/quota (ex.: HTTP 429) retornado pelo provedor deve ser um tipo de erro distinto no resultado da invocação, ou pode ser tratado como parte do erro genérico? → A: Rate limit é um tipo de erro distinto e sempre aciona fallback quando a rota tiver um configurado.
- Q: Qual provedor real deve ser implementado nesta fatia como o "1 provider real" exigido pela issue #37? → A: Um provedor remoto (tipo `openai-compatible` ou `gemini` conforme o contrato v1); a escolha final entre Google Gemini e OpenAI GPT está em aberto e será resolvida até o `/speckit-plan`, mantendo Ollama local como alternativa viável caso a decisão remota não avance a tempo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar e invocar um provedor via configuração declarativa (Priority: P1)

Um operador cadastra um provedor de IA (local, como Ollama, ou um endpoint remoto compatível com OpenAI) em um perfil declarativo que segue o contrato `ai-provider-profile.v1`. Sem alterar código do core, o Assistant Hub AI consegue invocar esse provedor para uma capacidade (ex.: `chat`) usando o contexto de uma sessão/transcript ativa.

**Why this priority**: É o motivo central da issue #37 — sem registro e invocação funcionando por configuração, não existe "hub pluggable" e nenhuma das demais histórias tem o que testar.

**Independent Test**: Registrar um perfil com um provedor fake habilitado, invocá-lo para a capacidade `chat` dentro do contexto de uma sessão existente e verificar que a resposta é atribuída ao `providerId`/modelo corretos, sem qualquer alteração no código do core. Repetir com o provedor real definido para esta fatia (ver Assumptions), configurado apenas via perfil.

**Acceptance Scenarios**:

1. **Given** um perfil válido conforme `ai-provider-profile.v1` com um provedor fake habilitado, **When** o Hub o invoca para a capacidade `chat` no contexto de uma sessão ativa, **Then** a resposta retorna atribuída ao `providerId`/modelo corretos, sem qualquer edição de código do core.
2. **Given** um provedor real (ex.: Ollama local ou endpoint OpenAI-compatible) configurado via perfil, **When** ele é invocado com uma requisição real dentro do contexto de uma sessão, **Then** a resposta retorna com sucesso ou com um erro explícito, sem derrubar o session-core.

---

### User Story 2 - Invocar e testar um provedor via API dentro de uma sessão ativa (Priority: P2)

Um chamador externo ao processo (cliente interno do produto, script de integração ou teste automatizado) usa um endpoint de API do serviço já existente para (a) testar a conexão de um provedor configurado, distinguindo autenticação, modelo inexistente e timeout, e (b) invocar um provedor para uma capacidade dentro do contexto de uma sessão ativa, recebendo a resposta e metadados de proveniência (`providerId`, modelo, latência).

**Why this priority**: A issue exige "caminho fim a fim documentado (API e/ou desktop)" como critério de aceite; expor teste de conexão e invocação via API é o que torna o Hub alcançável fora de chamadas internas de código e é pré-requisito de transporte para a UI desktop (User Story 3).

**Independent Test**: Com o serviço rodando, chamar o endpoint de teste de conexão para um provedor fake e um provedor real, e o endpoint de invocação para a capacidade `chat` referenciando uma sessão existente, validando a resposta (sucesso ou erro tipado) e os metadados de proveniência — sem qualquer cliente desktop envolvido.

**Acceptance Scenarios**:

1. **Given** um provedor fake configurado e habilitado, **When** um cliente chama o endpoint de teste de conexão via API, **Then** a resposta indica sucesso/falha e, em caso de falha, distingue autenticação, modelo inexistente ou timeout.
2. **Given** uma sessão ativa e um provedor configurado com a capacidade `chat`, **When** um cliente chama o endpoint de invocação via API referenciando essa sessão, **Then** a resposta contém o texto gerado e os metadados de proveniência (`providerId`, modelo, latência), sem expor segredos.

---

### User Story 3 - Configurar e testar provedores pela UI do desktop (Priority: P2)

Um operador usa a aplicação desktop para cadastrar, editar, habilitar/desabilitar um provedor, disparar o teste de conexão e visualizar quais capacidades ele atende — sem editar arquivos de configuração manualmente nem reiniciar o processo por fora da própria aplicação.

**Why this priority**: É o segundo caminho fim a fim citado pela issue ("API e/ou desktop") e o ponto de contato mais comum para quem não edita a configuração diretamente; depende do endpoint de API (User Story 2) como camada de transporte.

**Independent Test**: Na aplicação desktop, adicionar um provedor fake pela tela de configuração, disparar o teste de conexão pela UI e confirmar visualmente sucesso ou erro tipado; repetir com o provedor real e confirmar que a chave aparece apenas mascarada (prefixo/sufixo).

**Acceptance Scenarios**:

1. **Given** a tela de configuração de provedores no desktop, **When** o operador cadastra um novo provedor preenchendo os campos exigidos pelo contrato, **Then** o provedor passa a aparecer na lista e pode ser testado imediatamente, sem editar arquivos manualmente e sem reiniciar o serviço.
2. **Given** um provedor cadastrado com autenticação por chave, **When** o operador visualiza os detalhes desse provedor na UI, **Then** a chave aparece apenas com prefixo/sufixo mascarado, nunca em texto completo.
3. **Given** um provedor com erro de configuração (ex.: URL inválida ou timeout), **When** o operador clica em "testar conexão" na UI, **Then** a UI exibe o tipo de erro distinto (autenticação, modelo, timeout) retornado pela API.

---

### User Story 4 - Falha de um provedor não derruba a sessão, e fallback obedece a política (Priority: P3)

Quando um provedor configurado falha, expira (timeout) ou está indisponível, a invocação é isolada: o session-core continua funcionando normalmente. Um fallback ordenado só é acionado quando a rota do perfil define provedores de fallback; caso contrário, a falha é reportada de forma explícita ao chamador.

**Why this priority**: É um critério de aceite explícito da issue ("invocação isolada — timeout, falha sem derrubar session-core" e "falha ou rate limit aciona fallback apenas quando a política permitir"). Só faz sentido depois que a invocação básica (US1) já existe.

**Independent Test**: Forçar o provedor fake a expirar ou retornar erro e verificar que (a) o session-core permanece operacional e segue atendendo outras sessões, (b) uma rota com fallback configurado é atendida pelo próximo provedor da lista, e (c) uma rota sem fallback retorna um erro tipado em vez de tentar silenciosamente outro provedor.

**Acceptance Scenarios**:

1. **Given** uma rota com provedor primário e um fallback configurado, **When** o provedor primário expira (timeout), **Then** o provedor de fallback atende a requisição e o session-core permanece no ar.
2. **Given** uma rota sem fallback configurado, **When** o provedor primário falha, **Then** a invocação retorna um erro tipado e distinto ao chamador, e o session-core continua atendendo outras requisições normalmente.
3. **Given** um provedor configurado com `timeoutMs`, **When** a resposta demora mais que esse limite, **Then** a invocação é abortada no timeout e o erro retornado identifica explicitamente que foi um timeout (não indistinguível de outras falhas).
4. **Given** um provedor com `enabled: false`, **When** uma rota referencia esse provedor, **Then** ele nunca é efetivamente invocado — a rota falha de forma explícita ou segue para o próximo fallback disponível.
5. **Given** uma rota com provedor primário e um fallback configurado, **When** o provedor primário retorna rate limit/quota excedida, **Then** o provedor de fallback atende a requisição, com o erro de rate limit distinguível de outros tipos de falha no registro da invocação.

---

### User Story 5 - Segredos de provedores nunca vazam (Priority: P4)

Chaves e credenciais de provedores são referenciadas por `secretRef` e resolvidas apenas no momento da invocação. Elas nunca aparecem em logs, métricas, exceções ou exportações de configuração — apenas um valor mascarado, quando aplicável, é exibido.

**Why this priority**: É requisito de segurança explícito em ADR-0010 e `docs/security/provider-secrets.md`, e critério de aceite da issue #37 e da spec 003 ("segredos nunca aparecem em logs, respostas da API ou arquivos exportados"). Depende de que a invocação, a API e a UI (User Stories 1-3) já existam para ter todas as superfícies auditáveis.

**Independent Test**: Configurar um provedor com autenticação `bearer`/`api-key` via `secretRef` (env ou armazenamento seguro do SO), invocá-lo, e inspecionar logs, métricas e exceções gerados, confirmando que o valor bruto do segredo nunca aparece. Gerar uma exportação da configuração e confirmar que qualquer `secretRef` local é substituído por um placeholder explícito.

**Acceptance Scenarios**:

1. **Given** um provedor com autenticação `bearer`/`api-key` cujo segredo é resolvido via `secretRef`, **When** uma invocação é executada e registrada em log/métricas, **Then** nenhum valor bruto do segredo aparece nesses registros.
2. **Given** uma exportação da configuração de provedores, **When** a exportação é gerada, **Then** qualquer `secretRef` apontando para um segredo local é substituído por um placeholder explícito, nunca pelo valor real.
3. **Given** uma invocação que falha por segredo inválido ou ausente, **When** o erro é reportado, **Then** ele indica um problema de autenticação sem vazar conteúdo de headers ou do segredo.

---

### Edge Cases

- O que acontece quando o perfil referencia um `type` de provedor sem adaptador disponível? O sistema deve rejeitar a invocação com um erro de validação claro antes de tentar chamar a rede.
- O que acontece quando dois provedores no mesmo perfil têm o mesmo `id`? A validação do perfil deve rejeitar o cadastro antes que qualquer invocação seja possível.
- O que acontece quando a capacidade solicitada (ex.: `embeddings`) não está na lista `capabilities` do provedor de destino? A invocação deve ser rejeitada com um erro de incompatibilidade de capacidade, sem encaminhar a requisição ao provedor.
- Como o sistema se comporta quando múltiplas sessões invocam o mesmo provedor fake/real concorrentemente? Cada invocação deve ser isolada, sem estado mutável compartilhado que cause vazamento de contexto entre sessões/canais.
- O que acontece quando o contexto de sessão/transcript necessário (ex.: `channelId`, `sourceType`) está ausente ou incompleto? A invocação deve falhar de forma explícita em vez de enviar contexto parcial/ambíguo ao provedor.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir registrar um ou mais provedores de IA por meio de um perfil declarativo conforme o contrato `ai-provider-profile.v1`, sem exigir alteração de código do core para adicionar um novo endpoint OpenAI-compatible.
- **FR-002**: O sistema DEVE validar um perfil de provedores contra o schema v1 (campos obrigatórios, `id` de provedor único, `type`/`capabilities` permitidos) antes de aceitá-lo, rejeitando perfis inválidos com um erro de validação específico.
- **FR-003**: O sistema DEVE invocar um provedor de forma isolada, respeitando o `timeoutMs` configurado no perfil, de modo que um provedor lento ou com falha não bloqueie nem derrube o processo do session-core.
- **FR-004**: O sistema DEVE fornecer à invocação do provedor o contexto de sessão/transcript relevante (`channelId`, `sourceType` e conteúdo de texto/mensagens) necessário para atender a capacidade solicitada.
- **FR-005**: O sistema DEVE rotear uma requisição de capacidade para um provedor de fallback conforme `routes.fallbacks` do perfil somente quando o provedor primário falhar, expirar (timeout) ou retornar rate limit/quota excedida, e nunca DEVE invocar um provedor com `enabled: false`.
- **FR-006**: O sistema DEVE distinguir, no resultado da invocação, entre falha de autenticação, modelo desconhecido/não suportado, timeout, rate limit/quota excedida e erro genérico do provedor.
- **FR-007**: O sistema DEVE resolver segredos de provedores exclusivamente via `secretRef` (env ou armazenamento seguro do SO) e NÃO DEVE gravar, logar ou exportar o valor resolvido do segredo.
- **FR-008**: O sistema DEVE registrar métricas/eventos por invocação (id do provedor, modelo, capacidade, latência, sucesso/falha) sem incluir material de segredo.
- **FR-009**: O sistema DEVE incluir, no mínimo, um adaptador de provedor real (ex.: Ollama local ou um endpoint genérico OpenAI-compatible) e um adaptador de provedor fake/teste utilizável em testes automatizados sem acesso à rede externa.
- **FR-010**: O sistema DEVE rejeitar uma invocação cuja capacidade solicitada não esteja declarada na lista `capabilities` do provedor de destino, retornando um erro de incompatibilidade de capacidade em vez de encaminhar a requisição.
- **FR-011**: O sistema DEVE expor um endpoint de API para testar a conexão de um provedor configurado, retornando um resultado que distingue autenticação, modelo inexistente e timeout, sem exigir um cliente desktop.
- **FR-012**: O sistema DEVE expor um endpoint de API para invocar um provedor para uma capacidade dentro do contexto de uma sessão ativa, retornando o resultado e metadados de proveniência (`providerId`, modelo, latência) sem expor segredos.
- **FR-013**: A aplicação desktop DEVE fornecer uma tela para cadastrar, editar e habilitar/desabilitar um provedor, e para disparar o teste de conexão definido em FR-011, sem exigir edição manual de arquivos de configuração.
- **FR-014**: A UI desktop DEVE exibir material de autenticação (chaves/segredos) apenas em forma mascarada (prefixo/sufixo), nunca em texto completo, reutilizando o endpoint de API (não acessando o segredo resolvido diretamente).
- **FR-015**: O sistema DEVE aplicar mudanças no perfil de provedores (adição, edição, habilitação/desabilitação de provedor, alteração de rotas) — feitas via configuração, UI desktop ou API — sem exigir reinício do processo do session-core.

### Key Entities

- **Provider**: representa um motor de IA configurado (`id`, `label`, `type`, `enabled`, `baseUrl`, `authentication`, `defaults`, `capabilities`), conforme `ai-provider-profile.v1`.
- **Provider Profile**: documento versionado (`version: 1`) contendo a lista de `providers` e o mapa de `routes`.
- **Route**: associa uma tarefa/capacidade a um provedor primário (`primary`) e uma lista ordenada de provedores de fallback (`fallbacks`).
- **Invocation**: uma chamada isolada e com timeout a um provedor, associada a uma sessão/canal e a uma capacidade solicitada, com resultado de sucesso ou erro tipado (autenticação, modelo, timeout, genérico); alcançável internamente pelo session-core e externamente pelo endpoint de API (FR-012).
- **Connection Test**: verificação isolada da configuração de um provedor (autenticação, modelo, timeout) sem executar uma invocação completa de capacidade; disparável via API (FR-011) e via UI desktop (FR-013).
- **Secret Reference (`secretRef`)**: identificador lógico (`env:VAR` ou `os:caminho`) resolvido em tempo de invocação, nunca persistido em texto puro no perfil nem exposto em logs/exports/UI.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um operador consegue registrar e invocar com sucesso um novo provedor OpenAI-compatible usando apenas configuração, com zero alterações no código-fonte da aplicação.
- **SC-002**: Em 100% dos cenários de falha de provedor exercitados em teste (timeout, erro, indisponibilidade), a sessão ativa continua operando sem interrupção não planejada do session-core.
- **SC-003**: 100% dos testes automatizados que cobrem invocação de provedor rodam contra o provedor fake, sem exigir acesso real à rede nem credenciais reais.
- **SC-004**: Em 100% dos caminhos auditados de invocação e exportação de configuração, nenhum valor bruto de segredo aparece em logs, métricas, respostas de API ou arquivos exportados.
- **SC-005**: Em todos os cenários de falha testados, é possível distinguir erro de autenticação, erro de modelo inexistente, timeout e rate limit/quota excedida a partir do resultado da invocação — nenhum desses quatro casos retorna apenas um erro genérico ambíguo.
- **SC-006**: Um operador consegue cadastrar, testar e invocar um provedor inteiramente pela UI do desktop, sem editar arquivos de configuração manualmente.
- **SC-007**: Um chamador externo ao processo consegue testar a conexão e invocar um provedor exclusivamente via API, sem depender da aplicação desktop.

## Assumptions

- O Memory Hub / session-core (`specs/013-issue-29-memory-hub-persistence/`) já expõe dados de sessão e `transcript-event` que o AI Provider Hub pode ler como contexto de invocação; esta feature não introduz novo armazenamento de sessão.
- "1 provider real" refere-se a um provedor remoto real (tipo `openai-compatible` ou `gemini` conforme o contrato v1) — a decisão final entre Google Gemini e OpenAI GPT segue em aberto e deve ser fechada até o `/speckit-plan`. Ollama local permanece como alternativa viável de fallback do próprio slice caso a integração remota escolhida não esteja pronta a tempo; testes automatizados não podem depender de créditos pagos para rodar (reutilizam o provedor fake para cobertura sem custo, conforme FR-009/SC-003).
- O endpoint de API (FR-011/FR-012) é adicionado ao serviço já existente que hospeda o session-core, reaproveitando sua infraestrutura de rede; não é um novo processo/serviço separado.
- A tela de provedores na UI desktop (FR-013/FR-014) é hospedada pelo shell desktop já existente (`specs/014-issue-35-desktop-tauri-shell-local/`) e consome exclusivamente o endpoint de API — nunca lê `secretRef` resolvido diretamente.
- Capacidades mais amplas descritas em `specs/003-ai-provider-hub/spec.md` (motor de políticas de custo/privacidade, descoberta automática de modelos, seleção por persona) permanecem fora de escopo desta fatia de registro + invocação do R6, conforme "fora de escopo" da issue #37.
- A integração com o armazenamento seguro do sistema operacional (`secretRef` no formato `os:...`) é tratada pelo contrato e pelas regras de segurança, mas a cobertura automatizada de testes neste recorte roda no ambiente WSL Developer usando `secretRef` baseado em variável de ambiente, conforme `docs/security/provider-secrets.md`.
