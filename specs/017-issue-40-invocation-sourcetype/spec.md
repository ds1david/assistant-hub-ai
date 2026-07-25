# Feature Specification: Consistência de origem (`sourceType`) em resultados de invocação de IA

**Feature Branch**: `feature/issue-40-debt-invocationresult-sourcetype-consistency`

**Created**: 2026-07-25

**Status**: Draft

**Input**: User description: "40" (GitHub issue #40 — debt: InvocationResult sourceType consistency)

**Referências**: Issue [#40](https://github.com/ds1david/assistant-hub-ai/issues/40) · Débito rastreado na release 0.2.0 (`InvocationResult-sourceType`, issue #39 / `specs/016-issue-39-release-hardening`) · Constituição P5 (separação por canal e origem) · Spec `specs/015-issue-37-ai-provider-hub` (FR-004: contexto de sessão/transcript inclui `channelId` e `sourceType`) · Contrato de transcript (`sourceType`: origem do canal, ex. microfone vs. sistema)

## Clarifications

### Session 2026-07-25

- Q: When an invocation is bound to a session channel, where does the authoritative `sourceType` on the result come from? → A: Server resolves `sourceType` only from session/channel context; result includes it; caller never supplies origin.
- Q: When an invocation has no channel (or origin is not applicable), what should the result do? → A: No channel → origin absent/null on result (documented N/A); channel present → resolve or reject.
- Q: How should non-canonical sourceType values in session context be handled? → A: Reject the invocation with an explicit error if origin is not in the canonical set (fail-closed; no alias mapping, no unknown passthrough).
- Q: Should structured invocation logs include sourceType for observability? → A: Structured log includes sourceType when resolved for a channel-bound invoke; omitted/null when N/A (no channel); never log secrets or raw model output for this purpose.
- Q: When is a channel's origin considered resolvable on the server? → A: Resolvable from transcript/hub event(s) already recorded in the session for that channelId with canonical sourceType; if events for the same channel disagree on origin, reject. No separate channel-registry requirement for this debt slice.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Atribuir resposta de IA à origem correta do canal (Priority: P1)

Um operador ou integrador invoca um provedor de IA no contexto de uma sessão e de um canal conhecidos (por exemplo, canal de microfone ou canal de áudio de sistema). O resultado da invocação deve deixar explícita a **origem do canal** (`sourceType`) associada àquela chamada, de forma alinhada ao mesmo conceito usado nos eventos de transcrição e na memória de sessão — sem ambiguidade sobre se a assistência se refere a fala local, áudio remoto/sistema ou outro tipo de origem já suportado pelo produto.

**Why this priority**: Este é o débito central da issue #40. Sem origem consistente no resultado, consumidores (UI, auditoria, correlacionamento com transcript) não conseguem distinguir canais da mesma sessão e violam o princípio de preservar origem ponta a ponta.

**Independent Test**: Invocar o hub de provedores com uma sessão e um canal cuja origem é conhecida no contexto de sessão (ex.: microfone); o chamador **não** envia origem; inspecionar o resultado e confirmar que a origem retornada foi resolvida pelo servidor e coincide com o contexto de sessão/canal. Repetir com origem “sistema”. Não é necessário UI desktop para este teste.

**Acceptance Scenarios**:

1. **Given** uma sessão ativa com um canal de origem “microfone” no contexto de sessão, **When** uma invocação de IA é feita referenciando essa sessão e esse canal **sem** o chamador enviar origem, **Then** o resultado da invocação inclui a origem do canal como “microfone” (valor canônico dos eventos de transcrição), resolvida pelo servidor.
2. **Given** uma sessão ativa com um canal de origem “sistema” (áudio remoto/sistema) no contexto de sessão, **When** uma invocação de IA é feita referenciando essa sessão e esse canal **sem** o chamador enviar origem, **Then** o resultado da invocação inclui a origem “sistema”, coerente com os eventos de transcrição desse canal.
3. **Given** uma invocação bem-sucedida ou com falha tipada (timeout, provedor indisponível, etc.) no contexto de sessão/canal com origem conhecida, **When** o chamador observa o resultado, **Then** a origem do canal está presente no resultado em ambos os casos de sucesso e falha — a falha do provedor não apaga o contexto de origem da chamada.

---

### User Story 2 - Consumir o contrato de resultado sem surpresas (Priority: P1)

Um desenvolvedor ou revisor confia que o **modelo de resultado de invocação** documenta e expõe, de forma explícita, quais campos de contexto de sessão/origem são obrigatórios, opcionais ou “não aplicáveis”. O contrato escolhido é coberto por testes automatizados, de modo que regressões futuras (omitir origem, misturar canais, divergir dos valores de transcript) falhem na verificação do produto.

**Why this priority**: A issue #40 exige explicitamente que o modelo preserve **ou** documente o contexto, e que testes cubram o contrato. Sem documentação e testes, o débito reabre na próxima release.

**Independent Test**: Revisar a documentação do contrato de resultado de invocação (campos de sessão, canal e origem) e executar a suíte de testes que cobre sucesso/falha com canal, invocação sem canal (origem nula/ausente) e rejeição quando o canal não tem origem resolvível; todos os cenários do contrato passam.

**Acceptance Scenarios**:

1. **Given** o contrato de resultado de invocação publicado com o produto, **When** um revisor lê quais campos de contexto (sessão, canal, origem) são exigidos e em quais situações, **Then** a regra está escrita de forma inequívoca: o que é sempre presente, o que é opcional e o que é “não aplicável”.
2. **Given** a suíte de verificação do núcleo de sessão / hub de provedores, **When** os testes do contrato de origem no resultado são executados, **Then** eles cobrem pelo menos: (a) origem preservada em sucesso com canal, (b) origem preservada em falha com canal, (c) invocação sem canal com origem ausente/nula no resultado, (d) canal referenciado sem origem resolvível → rejeição explícita.
3. **Given** valores de origem usados nos eventos de transcrição do produto, **When** o resultado de invocação reporta origem, **Then** o conjunto de valores aceitos é o **mesmo conjunto canônico** (sem sinônimos paralelos ou casing divergente que obrigue o consumidor a mapear manualmente).

---

### User Story 3 - Não misturar origens entre canais da mesma sessão (Priority: P2)

Em uma sessão com **múltiplos canais** (ex.: microfone e sistema ao mesmo tempo), cada invocação amarrada a um canal deve devolver a origem **daquele** canal. Nenhuma resposta de um canal “herda” a origem de outro canal da mesma sessão por padrão ou por estado residual de chamada anterior.

**Why this priority**: Reforça P5 da constituição e o edge case já previsto no hub de provedores (isolamento entre sessões/canais). É secundário a US1/US2 porque depende do contrato básico já existir.

**Independent Test**: Na mesma sessão, invocar o hub duas vezes em sequência (ou em paralelo) com canais de origens diferentes e verificar que cada resultado carrega apenas a origem do canal da respectiva chamada.

**Acceptance Scenarios**:

1. **Given** uma sessão com canal A (origem microfone) e canal B (origem sistema), **When** o chamador invoca IA no canal A e em seguida no canal B, **Then** o resultado A reporta origem microfone e o resultado B reporta origem sistema, sem contaminação entre chamadas.
2. **Given** invocações concorrentes na mesma sessão em canais de origens distintas, **When** ambos os resultados retornam, **Then** cada resultado permanece atribuído à origem do seu próprio canal.

---

### Edge Cases

- **Invocação sem canal** (ex.: `channelId` ausente/nulo, ou caminho em que o canal não se aplica): o resultado **deixa a origem ausente/nula**; o contrato documenta isso como **não aplicável**. O servidor **não inventa** origem e **não** escolhe um canal/origem padrão da sessão.
- **Invocação sem sessão / teste de conexão de provedor**: permanece fora do requisito de origem no resultado de invoke de sessão; se houver resultado de teste de conexão separado, ele não precisa carregar `sourceType` de canal.
- **Canal desconhecido ou origem ausente no contexto de sessão**: quando a invocação **referencia um canal** e o servidor **não** encontra evento(s) de transcript/hub da sessão para aquele `channelId` com origem canônica, a invocação falha de forma **explícita** (erro claro ao chamador) em vez de preencher origem ambígua, omitir silenciosamente, usar default de outro canal ou pedir origem ao chamador.
- **Conflito de origem no mesmo canal**: se eventos já gravados na sessão para o mesmo `channelId` reportarem origens **diferentes**, a invocação é **rejeitada** (não “último evento ganha”).
- **Chamador tenta enviar origem**: o chamador **não** é fonte de `sourceType`; o servidor ignora qualquer tentativa de o chamador ditar origem (campo não faz parte do contrato de entrada) e resolve apenas a partir do contexto de sessão/canal.
- **Fallback de provedor**: quando a rota usa fallback, o resultado ainda reflete a **origem do canal da chamada** resolvida pelo servidor, não uma origem “do provedor”. Proveniência do provedor (quem respondeu) permanece distinta da origem do canal de áudio/sessão.
- **Valores legados ou desconhecidos no contexto de sessão**: se o contexto de sessão contiver um valor de origem **fora** do conjunto canônico (`microphone` / `system`), a invocação é **rejeitada com erro explícito** (fail-closed). Não há mapeamento de aliases, normalização para “desconhecido” nem repasse do valor bruto no resultado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST expor, no **resultado de cada invocação** de provedor de IA feita no contexto de um canal de sessão, o campo de **origem do canal** (`sourceType`) coerente com o contexto daquela chamada.
- **FR-002**: O sistema MUST usar o **mesmo vocabulário canônico de origem** já adotado nos eventos de transcrição (`microphone` e `system` apenas), sem introduzir sinônimos paralelos, aliases ou valores “desconhecido” no resultado de invocação.
- **FR-003**: O sistema MUST preservar a origem do canal no resultado tanto em invocações **bem-sucedidas** quanto em invocações com **falha tipada** (timeout, rate limit, provedor indisponível, erro de autenticação, etc.), desde que a chamada tenha sido aceita com contexto de canal válido.
- **FR-004**: O sistema MUST isolar origem por chamada: resultados de canais/sessões distintos MUST NOT compartilhar ou “vazar” origem entre si, inclusive sob concorrência e sob fallback de provedor.
- **FR-005**: Quando a invocação **não** estiver ligada a um canal (`channelId` ausente/nulo ou canal não aplicável), o sistema MUST devolver o resultado com origem **ausente/nula**, documentada como não aplicável, e MUST NOT inventar origem nem inferir a partir de outro canal da sessão.
- **FR-006**: Quando a invocação **referencia um canal** e o contexto de sessão/canal estiver **ausente, incompleto, sem origem resolvível, ou com origem fora do conjunto canônico**, o sistema MUST falhar de forma explícita ao chamador (contexto parcial/ambíguo ou não canônico não é enviado adiante e o chamador **não** pode completar a origem).
- **FR-011**: O sistema MUST **rejeitar** (fail-closed) qualquer invocação com canal cuja origem resolvida no servidor não seja exatamente um valor canônico de transcript (`microphone` ou `system`). MUST NOT mapear aliases, MUST NOT normalizar para genérico e MUST NOT ecoar valor bruto não canônico no resultado.
- **FR-013**: Para um `channelId` referenciado, o servidor MUST considerar a origem **resolvível** somente se existirem evento(s) de transcript/hub **já gravados na sessão** para esse canal com `sourceType` canônico. MUST NOT exigir um cadastro separado de canal só para este débito. Se eventos do mesmo canal divergirem quanto à origem, MUST rejeitar a invocação (não adotar “último evento ganha”).
- **FR-007**: O produto MUST documentar o contrato de resultado de invocação quanto a sessão, canal e origem (obrigatoriedade, valores permitidos, casos não aplicáveis), de forma legível por integradores e revisores de release.
- **FR-008**: A suíte de verificação automatizada MUST cobrir o contrato de origem no resultado: sucesso com canal (origem vinda de evento de sessão), falha com canal, multi-canal sem contaminação, invocação sem canal (origem nula/ausente), canal sem eventos/origem resolvível (rejeição), origem não canônica (rejeição), e conflito de origem entre eventos do mesmo canal (rejeição), de modo que regressões quebrem a build.
- **FR-009**: Após o fechamento desta fatia, o débito `InvocationResult-sourceType` da release 0.2.0 (issue #40) MUST ser tratável como **resolvido** no material de tracking de débitos (changelog/checklist da próxima release ou atualização do issue), sem reabrir o item como “só listado”.
- **FR-010**: Para invocações com canal de sessão, a origem no resultado MUST ser **resolvida exclusivamente pelo servidor** a partir do contexto de sessão/canal. O contrato de **entrada** da invocação MUST NOT exigir nem aceitar `sourceType` do chamador como fonte de verdade.
- **FR-012**: O log estruturado por invocação MUST incluir `sourceType` quando a origem tiver sido resolvida para um canal; quando a invocação for sem canal (origem N/A), o campo MUST estar omitido ou nulo no log. O log MUST NOT incluir segredos, áudio bruto nem o texto completo de saída do modelo só para fins desta fatia.

### Key Entities

- **Resultado de invocação**: Resposta tipada de uma chamada ao hub de provedores (sucesso ou falha), com proveniência do provedor (quem respondeu, modelo, latência) **e** contexto de sessão/canal/origem quando aplicável.
- **Contexto de chamada**: Identificadores que o chamador usa para amarrar a invocação a uma sessão e, quando houver, a um canal (`sessionId`, `channelId`). A origem (`sourceType`) **não** é enviada pelo chamador; o servidor a resolve a partir de eventos da sessão e devolve no resultado.
- **Origem do canal (`sourceType`)**: Classificação canônica da fonte do áudio/evento no produto (`microphone` ou `system`), presente nos eventos de transcript/hub da sessão e **ecoada** no resultado de invocação após resolução server-side.
- **Evidência de origem na sessão**: Um ou mais eventos de transcript/hub já gravados para o `channelId` na sessão, todos com a mesma origem canônica; ausência ou divergência impede a invocação com canal.
- **Canal de sessão**: Unidade de captura/transcrição dentro de uma sessão; possui identidade (`channelId`) e origem; canais da mesma sessão não se misturam antes da persistência nem no resultado de invocação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em **100%** das invocações de teste com canal de origem conhecida (microfone e sistema), o resultado reporta a origem correta na primeira verificação — zero casos de omissão ou valor trocado nos cenários cobertos.
- **SC-002**: Em uma sessão com **dois canais de origens distintas**, uma sequência de pelo menos uma invocação por canal produz **zero** contaminações de origem entre resultados (cada resultado casa com o seu canal).
- **SC-003**: A suíte automatizada do contrato de origem no resultado de invocação passa de forma **determinística** (sem GPU, sem hardware físico), cobrindo sucesso com canal, falha com canal, invocação sem canal (origem nula/ausente) e rejeição quando o canal não tem origem resolvível.
- **SC-004**: Um revisor consegue, em **menos de 10 minutos**, confirmar no material de produto (contrato documentado + testes) que o débito da issue #40 está fechado ou explicitamente resolvido — sem precisar inspecionar código de implementação para entender a regra de negócio.
- **SC-005**: Nenhum resultado de invocação em cenário de canal válido apresenta origem **conflitante** com o contexto de sessão/transcrição daquele canal nos testes de regressão desta fatia.
- **SC-006**: Em cenários de teste com canal e origem resolvida, o registro de observabilidade da invocação permite correlacionar **a mesma origem** que o resultado expõe (campo presente e igual); em invocação sem canal, o registro não inventa origem.

## Assumptions

- O vocabulário canônico de origem já existente nos eventos de transcrição é **exatamente** `microphone` e `system`; a **autoridade em runtime** para o valor no resultado de invocação é o **contexto de sessão/canal no servidor**, não o payload do chamador. Valores fora desse par geram rejeição, não mapeamento.
- A fatia é **débito de consistência de contrato**, não uma nova capacidade de domínio (não adiciona novos tipos de provedor, billing, nem UI desktop obrigatória).
- Preferência de compatibilidade: mudanças no modelo de **resultado** devem ser **aditivas** ou documentadas de forma que clientes existentes que só leem campos já estáveis continuem funcionando; o contrato de **entrada** não ganha campo obrigatório de origem (o chamador continua enviando sessão/canal quando aplicável).
- “Quando aplicável” na issue #40 significa: invocações que **referenciam um canal** de sessão/captura/transcript — nesses casos a origem é obrigatória no resultado após resolução server-side. Invocações **sem canal** devolvem origem nula/ausente (FR-005). Teste de conexão de provedor permanece fora do requisito de origem de canal.
- Proveniência do **provedor** (`providerId`, modelo, fallback) permanece conceito distinto de origem do **canal**; esta fatia não unifica os dois.
- Escopo de implementação concentrado no núcleo de sessão / hub de provedores e em testes/contrato associados; agentes de áudio Windows e serviço de transcrição não precisam mudar só para “fechar” o débito: a origem do canal é resolvida a partir de **eventos de transcript/hub já gravados na sessão** para o `channelId` (sem novo registro de canal obrigatório nesta fatia).
- Fora de escopo: redesign amplo do Memory Hub; novos valores de `sourceType` além do conjunto canônico atual; marketplace de provedores; correção do débito `frontend-vite-audit` (#41); novas features de domínio de IA; exigir que clientes externos passem `sourceType` na invocação.
- A branch de trabalho `feature/issue-40-debt-invocationresult-sourcetype-consistency` é independente do nome do diretório da spec; o diretório canônico desta feature é `specs/017-issue-40-invocation-sourcetype`.
