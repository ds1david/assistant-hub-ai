# Feature Specification: STT — finalização no disconnect e métricas de eco confiáveis

**Feature Branch**: `fix/stt-echo-metrics-disconnect-final`

**Created**: 2026-07-27

**Status**: Implemented — verified (suite + stress); ready for G3 / PR

**Input**: User description: formalizar o trabalho da branch `fix/stt-echo-metrics-disconnect-final` — garantir que, ao desconectar um canal de áudio, a finalização residual da utterance e o registro de métricas por sessão completem de forma confiável; eco suprimido no microfone não conta como evento entregue; canais system+mic aninhados mantêm contagens corretas (partial + final de disconnect).

**Referências**:
- ADR-0008 (supressão de eco na camada de transcrição — não AEC acústico)
- `specs/024-issue-55-stt-final-utterance` (final ao fim de utterance **e** residual no disconnect)
- `specs/001-streaming-foundation` (canais, feed de transcript, métricas de sessão)
- Constituição P5 (`sessionId` / `channelId` / `sourceType` ponta a ponta), P9 (sem áudio bruto/tokens em logs), P10 (testes determinísticos sem GPU/hardware)
- PR relacionada: [#73](https://github.com/ds1david/assistant-hub-ai/pull/73) (race de finalização no disconnect vs. `sampleCount` de eco)

## Clarifications

### Session 2026-07-27 (pipeline chained; defaults recomendados)

Pipeline `/speckit-clarify` → `/speckit-plan` → `/speckit-checklist` → `/speckit-tasks` executado em cadeia; respostas abaixo são os **defaults recomendados** (operador pode reabrir clarify se discordar).

| Tema | Default adotado |
|------|-----------------|
| Definição de “evento entregue” para métrica | Amostra contada **uma vez** no ponto de publicação do evento de transcript (partial ou final) **depois** de passar eco/dedupe e de a política decidir emitir. Fan-out para N assinantes **não** multiplica. Eco **suprimido** nunca gera amostra. |
| Ordem métrica vs. envio no disconnect | Registrar amostra de métrica **antes** de awaits de envio ao socket de áudio e ao feed; falha/timeout de envio **não** reverte a amostra. |
| Final de disconnect e cliente de áudio | Final de reason `disconnect` **não** precisa ser entregue de volta no socket de áudio que está fechando; **deve** ser contado e **deve** tentar fan-out no feed de transcript (com limite de tempo). Finais idle/max-open continuam enviáveis no socket vivo. |
| Modelo de concorrência no canal | Emissão **sequencial** na tarefa da conexão de áudio (backpressure natural). **Sem** fila de worker separada que possa dropar o tick de disconnect. |
| Proteção contra cancelamento no teardown | Finalização residual de disconnect MUST completar mesmo sob cancelamento agressivo do runtime de teste/cliente (ex. cancel após `websocket.disconnect`); se a finalização assíncrona for interrompida antes de agendar, há caminho síncrono best-effort de contagem quando utterance ainda aberta com texto útil. |
| Fan-out lento | Timeout por envio a assinante do feed (**1,0 s**) e teto no publish agregado do produtor (**0,5 s**); assinante travado é descartado/ignorado; métrica do produtor não depende do sucesso de todos os assinantes. |
| Leitura precoce de métricas (SC-002) | Observador **MAY** reconsultar por até **2,0 s** (poll) até contagens finais; perda permanente é falha. Helper de teste `wait_metrics` é o padrão de aceite em CI. |
| Stress de eco (SC-005) | **≥ 60** repetições do cenário `suppressed_echo` + multi-canal sem falha de `sampleCount` atribuível a race de disconnect. |
| Schema / API | **Sem** mudança de `transcript-event.v2` nem de shape do `GET /v1/sessions/{sessionId}/metrics`; só comportamento e estabilidade. |
| Docs | Comentários de teste + quickstart desta feature bastam; README já descreve o endpoint — opcional nota de “partial + disconnect final” se faltar. |

- Q: O que conta como “entregue” em `sampleCount`/`totalEvents`? → A: **Uma amostra por evento emitido** (partial/final) no ponto de publicação; eco suprimido **zero**; fan-out **não** multiplica.
- Q: Final de disconnect deve ir no WS de áudio? → A: **Não obrigatório** (socket fechando); **sim** contar métrica e tentar feed; idle/max-open mantêm envio no socket vivo.
- Q: Como evitar race de fila no disconnect? → A: **Emit sequencial** na conexão; sem worker queue que dropa disconnect tick.
- Q: Timeout de fan-out / poll de métricas? → A: **1,0 s** por assinante, **0,5 s** publish agregado, poll **2,0 s** para SC-002.
- Q: Quantas repetições definem “stress estável”? → A: **≥ 60** no cenário de eco multi-canal.

## Problema (diagnóstico)

1. **Sintoma**: em testes e sob carga de teardown, a métrica de sessão de um canal (ex. microfone com eco suprimido) às vezes mostra `sampleCount = 1` quando o esperado é **2** (um partial entregue + um final de disconnect/residual).
2. **Causa de produto**: o caminho de **finalização no desligamento do canal** (flush residual + fechar utterance aberta) pode **não completar** ou **não registrar métrica** antes de o observador ler o endpoint de métricas — em especial com **dois canais aninhados** (system + mic) e com **eventos suprimidos por eco** no meio do fluxo.
3. **Efeito**: operadores e CI não confiam em “eventos entregues por canal”; regressões de supressão de eco ficam **intermitentes** (flake); contagens confusas dificultam validar ADR-0008 (eco não deve inflar o feed entregue).
4. **O que já funciona** (fora do escopo de redesign): emissão de partials; supressão de eco por similaridade de texto (ADR-0008); endpoint de métricas por sessão; final por idle/max-open de utterance (024); live-answer e schema de transcript.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Métricas corretas após desligar um canal (Priority: P1)

Um operador (ou um teste automatizado) envia áudio em um canal de uma sessão, recebe ao menos um trecho parcial no feed, e em seguida o canal **desconecta** (fim da captura ou encerramento da conexão). Ao consultar as métricas da sessão, o canal reflete **cada evento de transcript realmente entregue** na contagem — incluindo o **final residual de disconnect** quando havia utterance aberta ou residual a fechar — **uma vez por evento**, sem depender de “sorte” no momento da leitura.

**Why this priority**: Aceite principal da branch e da correção de flake; sem contagem estável pós-disconnect, métricas de sessão e testes de eco são não confiáveis.

**Independent Test**: Simular um canal com uma janela de fala sintética, desconectar, ler métricas da sessão; esperar contagem coerente com partial entregue + final de disconnect (quando aplicável), sem GPU e sem hardware real.

**Acceptance Scenarios**:

1. **Given** um canal de áudio ativo que já entregou um evento de transcript parcial, **When** o canal desconecta e a finalização residual termina, **Then** as métricas da sessão para esse canal incluem **pelo menos** o partial e o final de disconnect (quando a política de finalização emite final no disconnect), com `sampleCount` / total de eventos **iguais** ao número de eventos entregues — não um a menos por corrida de teardown.
2. **Given** o mesmo cenário, **When** o operador consulta as métricas logo após o teardown do canal, **Then** consegue obter a contagem final completa dentro de um intervalo curto de observação (ver SC-002) — a leitura “cedo demais” pode ser resolvida por reconsulta, mas o sistema **não** deve perder o registro de forma permanente.
3. **Given** um evento de transcript entregue, **When** há assinantes no feed de transcript (fan-out), **Then** a contagem de amostras do canal **não** multiplica pelo número de assinantes (um evento = uma amostra, independentemente de quantos clientes de feed o receberam).

---

### User Story 2 - Eco suprimido não infla métricas do microfone (Priority: P1)

Em sessão com canal **system** (loopback) e canal **microphone**, o microfone captura eco da fala remota. O sistema **suprime** o trecho de microfone semelhante ao system recente (ADR-0008). A fala local **diferente** no microfone continua entregue. Nas métricas, o microfone **não** conta o eco suprimido como evento entregue; conta apenas o que de fato saiu no feed (partial local + final de disconnect, conforme política).

**Why this priority**: Valida o contrato de produto da supressão de eco e é o cenário que falhava de forma intermitente (`sampleCount` 1 vs 2 no mic).

**Independent Test**: Scriptar textos system + mic eco + mic local distinto; desconectar ambos os canais; assertar contagens por canal e que o texto local foi o entregue no mic — sem hardware WASAPI.

**Acceptance Scenarios**:

1. **Given** system já entregou um trecho de texto T e o microfone envia janela cujo texto é **eco de T** (suprimido), **When** as métricas do microfone são consultadas após o fluxo, **Then** esse eco **não** incrementa a contagem de eventos entregues do microfone.
2. **Given** em seguida o microfone envia fala **local distinta** (não eco), **When** o evento é entregue, **Then** esse partial **é** contado e o texto no feed do microfone é o da fala local.
3. **Given** system e mic na mesma sessão com teardown aninhado (system ainda “aberto” enquanto mic fecha, ou ambos fecham em sequência), **When** a finalização de disconnect de **ambos** termina, **Then** cada canal tem contagem estável coerente com partials entregues + final de disconnect (ex. mic: 1 partial local + 1 final; system: 1 partial + 1 final), **sem** contagem fantasma do eco.

---

### User Story 3 - Isolamento de sessão e de canal (Priority: P2)

Métricas de uma sessão não vazam para outra; canais da mesma sessão aparecem separados com identidade (`channelId`, `sourceType`, label quando houver) e contagens independentes.

**Why this priority**: Garante que correções de disconnect/eco não misturem contadores entre sessões ou canais.

**Independent Test**: Duas sessões e/ou dois canais com textos distintos; desconectar; comparar payloads de métricas.

**Acceptance Scenarios**:

1. **Given** duas sessões distintas com áudio, **When** se consulta métricas de cada `sessionId`, **Then** cada payload lista apenas os canais daquela sessão, com contagens independentes.
2. **Given** uma sessão com dois canais (ex. system e mic), **When** se consulta métricas, **Then** ambos aparecem com identidade distinta e contagens que não se somam indevidamente num único bucket.

---

### User Story 4 - Operador e CI confiam no endpoint de métricas (Priority: P3)

Desenvolvedores e operadores usam o endpoint de métricas da sessão (e testes automatizados associados) para validar entrega de eventos, latência agregada e ausência de eco contado. A documentação de validação/teste deixa claro que, após disconnect, a contagem deve incluir o final residual quando emitido, e que eco suprimido não entra na contagem entregue.

**Why this priority**: Reduz regressão e flake de CI; alinha expectativa com 024 (final no disconnect como rede de segurança além do idle).

**Independent Test**: Suite de métricas de sessão passa de forma estável (incluindo cenário de eco); nota operacional ou comentário de teste descreve partial + disconnect final e eco não contado.

**Acceptance Scenarios**:

1. **Given** a suíte de testes de métricas de sessão (incluindo eco + multi-canal), **When** executada de forma repetida em ambiente de CI sem GPU, **Then** não há falha intermitente por contagem de disconnect incompleta (critério: zero falhas atribuíveis a race de finalização no teardown em stress razoável do cenário de eco).
2. **Given** um leitor da spec/docs de validação, **When** investiga “por que sampleCount é 2 e não 1”, **Then** encontra a regra: partial entregue + final de disconnect (quando a utterance/residual finaliza no desligamento), e eco suprimido fora da contagem entregue.

---

### Edge Cases

- **Disconnect sem nenhum partial útil**: canal abre e fecha sem texto entregue — métricas não inventam amostra; final vazio/só ruído não conta como evento útil entregue (alinhado a 024).
- **Disconnect com utterance já fechada por idle**: não deve **duplicar** final nem inflar contagem com segundo final idêntico sem nova fala.
- **Vários assinantes lentos no feed**: fan-out de transcript não bloqueia de forma indefinida a finalização/métricas do canal produtor; um assinante preso não apaga permanentemente o registro de métricas do produtor.
- **Cliente de áudio já fechado no momento do final de disconnect**: o final residual ainda deve ser **contado** e, se possível, publicado no feed de transcript para observadores; falha de envio direto ao socket de áudio que está fechando **não** cancela o registro de métrica.
- **Cancel residual extreme (analyze I1)**: se o runtime cancelar a tarefa **depois** de `websocket.disconnect` e o shield da finalização assíncrona **não** completar o caminho de publicação, o caminho síncrono best-effort MAY registrar **apenas** a amostra de métrica (e fechar o finalizer) **sem** fan-out do evento no feed. Fan-out e evento completo permanecem **best-effort** sob cancel; **perda permanente de contagem** continua proibida quando a utterance tinha texto útil.
- **Supressão de eco + residual no flush**: texto residual no desligamento que seria eco ou duplicata da política de dedupe **não** deve inflar contagem entregue além do esperado pela política.
- **Retenção de amostras de métricas**: `totalEvents` é a contagem cumulativa de eventos entregues; `sampleCount` é o tamanho do ring de latência (≤ `maxSamplesPerChannel`). Em cenários curtos de aceite (1 partial + 1 final) ambos valem **2**; sob retenção, `sampleCount` pode ser **menor** que `totalEvents` — asserts de produto usam **`totalEvents`** como fonte da verdade do “quantos eventos”, e `sampleCount` quando o foco é o buffer de percentis.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST, ao desconectar um canal de áudio de uma sessão, executar a finalização residual da utterance daquele canal (flush/residual conforme política de 024) de forma que a contagem de eventos **não se perca de forma permanente** só porque o cliente de áudio encerrou — inclusive sob cancelamento de tarefa no teardown (clarify 2026-07-27). Leitura temporariamente atrasada é aceitável se recuperável via reconsulta (ver **SC-002**). Caminho metrics-only sob cancel extremo: ver Edge Cases.
- **FR-002**: O sistema MUST incrementar **`totalEvents`** (e a amostra de latência do ring) **exatamente uma vez** por evento de transcript entregue naquele canal (partial ou final), independentemente do número de assinantes do feed de transcript. Em cenários curtos sem pressão de retenção, `sampleCount` coincide com `totalEvents`.
- **FR-003**: O sistema MUST registrar a amostra de métrica do evento **antes de qualquer await** no caminho de publicação — incluindo prosódia (se habilitada), envio ao socket de áudio e fan-out do feed; falha ou timeout de I/O MUST NOT reverter a amostra já registrada.
- **FR-004**: O sistema MUST emitir (quando a política de finalização o exigir) o final de disconnect com a mesma identidade de canal/sessão/`sourceType`/label dos partials daquele canal (P5). Final de disconnect MAY omitir envio direto ao socket de áudio que está fechando; MUST tentar fan-out no feed com limite de tempo no caminho normal (shield completo). Sob cancel residual extremo, fan-out é best-effort (Edge Cases).
- **FR-005**: O sistema MUST NOT contar como evento entregue um trecho de microfone **suprimido por eco** (ADR-0008) — a contagem do microfone reflete apenas o que efetivamente saiu no pipeline de publicação daquele canal.
- **FR-006**: O sistema MUST manter contagens e listagens de métricas **isoladas por `sessionId`** e **por `channelId`** dentro da sessão.
- **FR-007**: O sistema MUST expor as métricas de sessão via o endpoint de métricas já existente da Streaming Foundation (`GET /v1/sessions/{sessionId}/metrics`), com campos de contagem e latência agregada por canal utilizáveis por operadores e testes (sem exigir GPU); **sem** mudança de shape nesta feature.
- **FR-008**: O sistema MUST permitir que, após disconnect multi-canal (incluindo system + mic aninhados), as contagens de **todos** os canais envolvidos atinjam o valor final completo sem perda permanente do final de disconnect por corrida de teardown.
- **FR-009**: Testes automatizados da feature MUST ser determinísticos e independentes de GPU e de hardware WASAPI (P10); cenários de eco e multi-canal MUST cobrir contagem pós-disconnect; stress do cenário de eco MUST repetir **≥ 60** vezes sem flake de contagem por race (ver **SC-005**).
- **FR-010**: No **caminho de finalização/disconnect e no registro de métricas desta feature**, o sistema MUST NOT registrar PCM, tokens ou dumps de áudio; logs de disconnect MUST limitar-se a ids de sessão/canal e contadores (P9). Redação de logs INFO de **supressão de eco** (texto/matched) **não** é obrigatória nesta fatia — ver Out of Scope.
- **FR-011**: O processamento de janelas de áudio de um canal MUST ser **sequencial** na conexão (sem fila de worker que possa descartar o tick de disconnect sob pressão).
- **FR-012**: Envios do fan-out do feed MUST ter timeout por assinante (default **1,0 s**) e o publish do produtor MUST ter teto (default **0,5 s**) para não bloquear finalização de disconnect de forma indefinida.

### Key Entities

- **Sessão de transcrição**: identificada por `sessionId`; agrega um ou mais canais de áudio e um snapshot de métricas consultável.
- **Canal de áudio**: identificado por `channelId` na sessão; possui `sourceType` (ex. system, microphone), label opcional e contadores de eventos/latência.
- **Evento de transcript entregue**: partial ou final que saiu no pipeline de entrega (feed e/ou contagem); eco suprimido **não** é evento entregue.
- **Final de disconnect**: finalização residual ao encerrar o canal; fecha utterance aberta ou residual de flush quando a política aplica; conta como no máximo um evento entregue adicional por ciclo de desligamento quando emitido.
- **Métricas por canal**: contagem de amostras/eventos entregues, janelas descartadas (se aplicável), percentis de latência, carimbo do último evento — sem multiplicar por fan-out de feed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos cenários de teste determinísticos de um canal com um partial entregue + disconnect com final residual, **`totalEvents == 2`** (não 1) após a finalização completar; com retenção default e só 2 eventos, **`sampleCount == 2`** também.
- **SC-002**: Após o teardown de canais em cenário multi-canal (system + mic com eco), um observador que consulta métricas da sessão obtém contagens finais completas de **todos** os canais em até **2 segundos** de reconsulta (poll), em ambiente de teste local — sem perda permanente de **`totalEvents`**.
- **SC-003**: No cenário de eco (system texto T, mic eco de T suprimido, mic fala local distinta), **`totalEvents` do microfone == 2** (1 partial local + 1 final de disconnect) e **do system == 2**; eco suprimido **não** eleva o mic para `totalEvents ≥ 3`. Com retenção folgada, `sampleCount` coincide.
- **SC-004**: Com N assinantes no feed de transcript (N ≥ 1), **`totalEvents`** (e `sampleCount` sob a mesma retenção) do canal produtor permanece **igual** à contagem com 0 ou 1 assinante para o mesmo número de eventos de transcript (sem multiplicação por N).
- **SC-005**: A suíte de testes de métricas de sessão, incluindo o cenário de eco, passa de forma estável em CI sem GPU; stress do cenário de eco (**≥ 60** repetições) não reproduz falha intermitente de **`totalEvents`/`sampleCount`** por race de disconnect (cenário curto: ambos == 2).
- **SC-006**: Operador ou desenvolvedor consegue explicar “partial + disconnect final”, “eco não conta” e a diferença **`totalEvents` (cumulativo) vs `sampleCount` (ring)** sem inspecionar código — via spec/docs e o endpoint de métricas.

## Assumptions

- A política de **quando** emitir final (idle, max-open, disconnect residual) permanece a de `specs/024-issue-55-stt-final-utterance`; esta feature **não** redesenha gatilhos de idle/max-open, só garante que o caminho de **disconnect** complete e seja contado de forma confiável.
- Supressão de eco permanece na camada de transcript (ADR-0008); **não** é AEC acústico completo e **não** altera WAV bruto.
- O endpoint e o modelo de métricas de sessão da Streaming Foundation já existem; esta feature endurece **completude e correção** pós-disconnect e com eco, sem exigir novo produto de dashboard além do endpoint atual.
- Testes usam motor de transcrição falso e áudio sintético; validação em hardware real Windows/WASAPI fica opcional em `docs/validation/` se necessária, não como gate de CI.
- Assinantes lentos no feed: timeout **1,0 s** por envio e teto **0,5 s** no publish do produtor (clarify); o requisito de produto é não perder **métrica do produtor**, não garantir entrega eterna a todo assinante.
- Implementação de referência já existe na branch `fix/stt-echo-metrics-disconnect-final`; esta pasta formaliza aceite e residual de verificação/docs.
- Não há mudança de schema de `transcript-event.v2` nesta feature (reutilizar partial/final existentes).
- Branch de implementação de referência: `fix/stt-echo-metrics-disconnect-final` (e predecessor `fix/stt-echo-metrics-disconnect-race` / PR #73).

## Out of Scope

- Redesign da heurística de similaridade de eco (thresholds, janela temporal) — apenas garantir que **suprimido não conta**.
- **Redação/remoção de logs INFO de supressão de eco** que ainda incluem trecho de texto (`text` / `matched`) — preexistente; não é gate desta feature (FR-010 limita-se ao caminho disconnect/métricas).
- AEC nativo no agente Windows.
- Novos painéis de UI de métricas no desktop-shell (além do endpoint STT já existente).
- Alterar política “live-answer só em final” (019) ou gatilhos de utterance idle (024) além do caminho de disconnect.
- Métricas de negócio externas (Prometheus/Grafana remotos); foco é métricas de sessão do serviço de transcrição.
- Mudança de contratos versionados de transcript ou de identidade de canal.

## Analyze remediação (2026-07-27)

| ID | Tema | Ação |
|----|------|------|
| I1 | Cancel residual metrics-only | Edge Cases + FR-001/004 + contract C7 |
| I2 | `totalEvents` vs `sampleCount` | FR-002, SC-001–005, Edge Cases retenção |
| C1 | P9 / logs de eco | FR-010 narrowed + Out of Scope |
| U1 | Prosody await | FR-003 + plan + research R3 + T005 |
