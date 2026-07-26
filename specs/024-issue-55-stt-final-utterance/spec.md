# Feature Specification: STT — emitir `transcript.final.v2` ao fim de utterance (live-answer)

**Feature Branch**: `feature/issue-55-stt-emitir-transcript-final-v2-ao-fim-de-utteran`

**GitHub Issue**: [#55](https://github.com/ds1david/assistant-hub-ai/issues/55)

**Created**: 2026-07-25

**Status**: Clarified — ready for `/speckit-plan` / G2

**Input**: User description: "criar/atualizar specs/00x-issue-55-*/" — GitHub issue #55: [stt] Emitir `transcript.final.v2` ao fim de utterance (live-answer). session-core só recebe `transcript.partial.v2` (janelas ~3.2s); Assistente live-answer (019 FR-003) só dispara em **final** → perguntas claras com `sourceType=system` nunca geram resposta automática.

**Referências**:
- Issue [#55](https://github.com/ds1david/assistant-hub-ai/issues/55)
- `specs/019-auto-answer-assistant` (live-answer; **FR-003**: automático só em trechos **finais**; **FR-002**: origem habilitada)
- `specs/023-issue-52-question-detection-quality` (heurística de pergunta + prosódia opcional em Final; **não** muda política de partial vs final)
- `specs/020-issue-47-sessionid-align` / `specs/021-issue-49-session-list-select` / `specs/022-issue-51-stt-ui-header` (sessionId alinhado agent ↔ shell ↔ STT)
- Contrato `contracts/transcript-event.v2.schema.json` (`type`: `transcript.partial.v2` | `transcript.final.v2`)
- Streaming foundation `specs/001-streaming-foundation`
- Constituição P1 (spec antes de código), P4 (contratos versionados), P5 (`sessionId` / `channelId` / `sourceType` ponta a ponta), P9 (privacidade), P10 (testes sem GPU/hardware físico)

## Problema (diagnóstico)

1. **Sintoma**: com agent, STT e session-core no ar, `GET /api/sessions/{id}/events` lista apenas eventos cujo `type` é `transcript.partial.v2`. Não há `transcript.final.v2` durante a conversa.
2. **Causa de produto**: o pipeline de streaming trata cada janela de áudio processada como **parcial**; o único caminho que marca **final** hoje é o **flush residual no desligamento** do canal de áudio — não o **fim natural de um segmento de fala** (pausa / silêncio / fechamento de utterance).
3. **Efeito em cascata**: o Assistente live-answer (**019 FR-003**) **não** dispara em partials. Perguntas legíveis no feed (inclusive `sourceType=system`) permanecem “só partial” → estado de UI `awaiting_final` (“Aguardando trecho final…”) e **zero** geração automática, mesmo com automático ligado, origem habilitada e heurística de pergunta correta (023).
4. **O que já funciona** (fora do escopo de correção desta feature): UUID de sessão alinhado; `correlation` / `sourceType` system vs microphone; partials para dashboard STT e streaming; detecção de pergunta no shell.

## Clarifications

### Session 2026-07-25 (defaults a partir da issue #55 — sem bloqueio)

Defaults adotados nesta spec a partir do aceite da issue e do estado do produto.

| Tema | Default adotado |
|------|-----------------|
| Gatilho de final | **Fechamento de utterance** (segmento de fala contínuo), **não** só disconnect do canal |
| Política de finalização | Combinar **(1)** silêncio/pausa após fala e **(2)** estabilidade de texto entre janelas; **(3)** timeout máximo de utterance aberta como rede de segurança — valores numéricos no plan, documentados e testáveis |
| Cardinalidade | **Um** `transcript.final.v2` por utterance fechada; partials intermediários **ok** e esperados |
| Identidade | Final MUST reutilizar o mesmo `sessionId`, `channelId`, `sourceType`, `label` e metadados de dispositivo dos partials daquele canal |
| Texto do final | Texto consolidado/estável da utterance (não um partial “cru” incompleto se o consolidator já tiver texto melhor); vazio/só ruído **não** vira final útil (ver edge cases) |
| Partials | Continuam para UI de streaming (dashboard STT e feed); **não** remover partials |
| Live-answer | **Não** alterar regra “só final” (019 FR-003); **não** disparar em partial |
| Heurística de pergunta | Fora de escopo (permanece 023 / 019) |
| Schema | Reutilizar `transcript.final.v2` existente; **sem** novo tipo de evento; campos aditivos só se plan provar necessidade (preferir zero mudança de schema) |
| Testes | Preferir **automatizados determinísticos** (fake áudio/janelas, state machine de finalização) **sem GPU**; se engine real for inevitável, cobrir contrato + unidade da política e evidência manual em `docs/validation/` |
| Docs | Nota operacional para live-answer / quickstart / running: finais ao fim de utterance desbloqueiam o Assistente |

### Session 2026-07-25 (clarify — pipeline chained; defaults recomendados)

Pipeline `/speckit-clarify` → plan → checklist → tasks executado em cadeia; respostas abaixo são os **defaults recomendados** (operador pode reabrir clarify se discordar).

- Q: Qual sinal primário fecha a utterance? → A: **Sem resultado novo de transcrição após fala** — janela avaliada que não produz texto novo (silêncio, no-speech, ou texto idêntico ao último) **depois** de ao menos um partial com texto útil na utterance aberta. Equivale a pausa **e** estabilidade de texto no pipeline atual (janelas sem evento). **Não** exigir VAD/PCM energy separado no agent.
- Q: Quantas janelas “sem texto novo” fecham a utterance? → A: **`finalization_idle_windows = 1`** (default): a **primeira** janela sem texto novo após partials fecha e emite o final. Configurável; plan documenta env/setting.
- Q: Timeout máximo de utterance aberta? → A: **`finalization_max_open_seconds = 45`** (default): se a utterance ficar aberta sem fechar por idle, força um final com o último texto útil e reabre ciclo. Evita “awaiting_final” eterno em monólogo.
- Q: Qual texto vai no `transcript.final.v2`? → A: **Último texto útil da utterance** (último partial emitido / último texto não vazio aceito pela state machine naquele canal). MUST NOT inventar; MUST NOT emitir final se nunca houve texto útil.
- Q: Latência alvo do final após o fim da fala? → A: **Até ~1 janela de STT após a pausa** (ordem de grandeza da janela configurada, tipicamente ~3s com default 3.2s) — aceitável para live-answer; não exigir sub-segundo nesta fatia.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fechar utterance e ver final na sessão (Priority: P1)

Um operador corre uma sessão com captura e transcrição. Alguém fala uma frase (pergunta ou não) e faz uma **pausa**. Após o fechamento do segmento, a sessão no session-core (e o feed de transcript) passa a conter um evento **final** daquele canal — além dos partials que já vinham durante a fala.

**Why this priority**: Aceite principal da issue #55; sem final na sessão, nenhum consumidor (Assistente, consolidação, métricas de turn) consegue tratar “trecho fechado”.

**Independent Test**: Injetar (ou simular) janelas de áudio/texto de uma utterance seguida de silêncio/pausa conforme a política; consultar eventos da sessão e verificar presença de `type` final com o mesmo `sessionId`/`channelId`/`sourceType` dos partials; sem depender de desligar o agent.

**Acceptance Scenarios**:

1. **Given** um canal de áudio ativo enviando janelas de uma fala contínua, **When** a política de finalização detecta o **fim da utterance** (pausa/silêncio e/ou estabilidade + critérios da política), **Then** o sistema publica **um** evento `transcript.final.v2` para aquele canal com o texto da utterance e metadados de identidade coerentes com os partials.
2. **Given** a mesma sessão e o mesmo canal, **When** o operador (ou teste) lista os eventos da sessão após a pausa, **Then** existe ao menos um evento cujo tipo indica **final** (não apenas partials).
3. **Given** partials já emitidos durante a fala, **When** o final é publicado, **Then** partials **permanecem** no feed/histórico de streaming; o final **não** os apaga nem substitui o papel de UI streaming.
4. **Given** dois segmentos de fala separados por pausa suficiente (duas utterances), **When** ambos fecham, **Then** existem **dois** finais distintos (um por utterance), não um único final amalgamado sem política.

---

### User Story 2 - Live-answer pode disparar após final elegível (Priority: P1)

Com automático do Assistente **ligado**, origem **system** (ou outra habilitada) e texto reconhecido como pergunta, o operador fala (ou o remoto fala no loopback) e **pausa**. Após o final chegar à sessão ativa, o Assistente **pode** iniciar geração — o bloqueio “só partials / awaiting_final” deixa de ser o estado permanente da conversa.

**Why this priority**: Objetivo de produto da issue: desbloquear live-answer sem mudar a regra “não disparar em partial”.

**Independent Test**: Com automático on, origem habilitada e texto de pergunta, produzir utterance + fechamento; verificar que o feed da sessão ativa expõe trecho **Final** e que o orquestrador do Assistente **pode** iniciar geração (ou, em teste unitário do shell, que o trecho deixa de ser classificado só como partial). Não exige GPU se o final for injetado via fixture de eventos.

**Acceptance Scenarios**:

1. **Given** automático ligado, origem system habilitada, sessão ativa alinhada, e uma utterance de pergunta em canal system, **When** a utterance fecha e o final é incorporado ao feed da sessão, **Then** o Assistente **pode** iniciar geração (sujeito à heurística de pergunta e demais gates de 019/023 — esta feature só garante a **existência** do final).
2. **Given** o mesmo setup mas **somente** partials ainda em curso (utterance **não** fechada), **When** o operador observa o Assistente, **Then** **não** há novo disparo automático só por partial (019 FR-003 preservado).
3. **Given** final de **afirmação** (não pergunta) após pausa, **When** o feed incorpora o final, **Then** o Assistente **não** é obrigado a gerar resposta; a feature só exige que o final exista — a elegibilidade de pergunta permanece 019/023.

---

### User Story 3 - Um final por utterance (sem spam) (Priority: P2)

Durante uma fala longa com vários partials intermediários, o sistema **não** emite um final a cada janela. Só após o critério de fechamento. Após um final, uma **nova** fala no mesmo canal pode gerar um novo final ao fechar.

**Why this priority**: Aceite explícito “não spam”; evita flood de invoke no Assistente e ruído no histórico.

**Independent Test**: Sequência controlada de N partials da mesma utterance → exatamente **1** final ao fechar; reabrir fala → novo ciclo partials + 1 final.

**Acceptance Scenarios**:

1. **Given** N janelas processadas da **mesma** utterance aberta (N ≥ 2), **When** a utterance ainda não fechou, **Then** os eventos publicados são partials (0 finais daquela utterance).
2. **Given** a utterance fecha uma vez, **When** não há nova fala, **Then** **não** há segundo final repetido do mesmo segmento sem nova utterance.
3. **Given** um final já emitido e depois nova fala no mesmo canal, **When** a nova utterance fecha, **Then** um **novo** final é emitido (ciclo independente).

---

### User Story 4 - Documentação e verificação operacional (Priority: P3)

O operador ou desenvolvedor encontra na documentação de running/quickstart/live-answer que o STT emite **final ao fim de utterance**, que partials continuam para o dashboard, e que o Assistente depende desses finais — com um caminho de verificação (eventos da sessão / estado do Assistente) sem depender de “desligar o agent para ver final”.

**Why this priority**: Aceite de docs da issue; reduz regressão operacional e confusão com issue #52 (heurística) vs #55 (ausência de final).

**Independent Test**: Docs atualizados mencionam final-on-utterance e o vínculo com live-answer; checklist/quickstart descreve como confirmar um final na sessão após fala+pausa.

**Acceptance Scenarios**:

1. **Given** docs de operação/live-answer atualizados, **When** o leitor investiga “por que o Assistente não dispara”, **Then** encontra que (a) automático só reage a **finais**, e (b) o STT deve emitir final ao **fechar utterance**, não só no disconnect.
2. **Given** o quickstart/validação da feature, **When** o operador segue o passo “fala + pausa”, **Then** consegue confirmar um evento final na sessão **sem** encerrar o canal de áudio.

---

### Edge Cases

- **Silêncio contínuo sem fala prévia**: não emitir final vazio “fantasma”; partials de texto vazio/ruído já filtrados pelo pipeline atual continuam filtrados.
- **Texto vazio ou só whitespace após “fechamento”**: MUST NOT publicar final com texto inútil que dispare falso positivo no Assistente; preferir omitir o final ou equivaler ao comportamento atual de “sem resultado”.
- **Fala muito longa sem pausa**: timeout máximo de utterance aberta (`finalization_max_open_seconds`, default **45s**) MUST fechar a utterance, emitindo um final com o último texto útil; a fala seguinte inicia nova utterance.
- **Idle com `finalization_idle_windows = 1`**: a primeira avaliação de janela sem texto novo após partials fecha; aumentar o setting exige mais janelas idle antes do final (menos sensível a micro-pausas).
- **Janelas dropadas / atraso de filas**: atraso não deve gerar **múltiplos** finais da mesma utterance; política é por estado de utterance, não “um final por drop”.
- **Disconnect do canal no meio da fala**: o flush residual no desligamento continua válido como final da utterance aberta (compatível com comportamento atual); MUST NOT emitir dois finais idênticos (disconnect + política) para o mesmo residual.
- **Dois canais (system + microphone)**: cada canal fecha utterances **independentemente**; finais preservam `channelId` e `sourceType` (P5); eco suppression existente não é redesenhada nesta feature.
- **Eco / microfone**: se um partial de microfone é suprimido, não deve “reviver” como final ecoado; finais de microfone legítimos (fala local distinta) ainda podem fechar.
- **Reconexão / nova conexão de canal**: estado de utterance aberta é por conexão de canal; reconectar não reemite finais antigos.
- **Consumidores legados**: clientes que só escutam partials continuam funcionando; clientes que esperam final passam a recebê-lo em tempo de conversa.
- **Prosódia (023)**: se habilitada, permanece associada a Final quando aplicável; ausência de prosódia não bloqueia emissão do final.
- **Privacidade**: logs MUST NOT registrar texto completo de transcript nem áudio bruto (P9); contadores/tipo de evento ok.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O serviço de transcrição MUST publicar eventos `transcript.final.v2` (contrato v2 existente) quando uma **utterance** de um canal de áudio **fecha**, sem exigir o desligamento do canal ou do agent.
- **FR-002**: O sistema MUST manter a publicação de `transcript.partial.v2` durante a utterance para UI de streaming (dashboard STT e consumidores de partial).
- **FR-003**: A política de finalização MUST ser **documentada** (spec/plan/docs) e cobrir: **(a)** fechamento por **idle** — após utterance aberta ( ≥1 texto útil ), a **primeira** janela avaliada **sem texto novo** (default `finalization_idle_windows = 1`) emite o final; **(b)** **timeout máximo** de utterance aberta (default `finalization_max_open_seconds = 45`) força final com o último texto útil. Defaults numéricos e nomes de setting no plan; MUST ser configuráveis sem mudança de código de domínio.
- **FR-004**: Para cada utterance fechada, o sistema MUST emitir **no máximo um** `transcript.final.v2` daquela utterance (sem spam por janela).
- **FR-005**: Cada `transcript.final.v2` MUST carregar o mesmo `sessionId`, `channelId`, `label`, `sourceType` e metadados de `device` coerentes com os partials daquele canal naquela sessão (P5).
- **FR-006**: O texto do final MUST ser o **último texto útil** da utterance (último partial emitido / último texto não vazio aceito na state machine daquele canal). MUST NOT inventar texto; MUST NOT publicar final se a utterance nunca teve texto útil.
- **FR-007**: O session-core (ou caminho de ingestão já usado para partials) MUST persistir/expor o final nos eventos da sessão de forma que `GET` (ou equivalente de feed) da sessão mostre o tipo final após fala+pausa.
- **FR-008**: O Assistente live-answer MUST continuar a disparar **somente** em trechos finais (019 FR-003). Esta feature MUST NOT introduzir disparo automático em partial.
- **FR-009**: Esta feature MUST NOT alterar a heurística de detecção de pergunta do shell (023 / 019 lexical) nem o seletor de origens do Assistente.
- **FR-010**: Em desligamento de canal com residual de áudio/transcrição, o sistema MUST continuar a poder emitir um final do residual **sem** duplicar um final já emitido pela política de utterance para o mesmo conteúdo residual.
- **FR-011**: Testes automatizados MUST cobrir a state machine / política de finalização (abertura → partials → fechamento → um final; nova utterance → novo final; sem final em partial-only) de forma **determinística** e **sem GPU** quando possível (P10). Testes de contrato do schema v2 para final permanecem válidos.
- **FR-012**: Documentação operacional (running e/ou quickstart e/ou nota live-answer) MUST descrever que finais ocorrem ao fim de utterance e que o Assistente depende desses finais; MUST incluir verificação “fala + pausa → evento final na sessão” sem depender só de disconnect.
- **FR-013**: MUST NOT exigir novo tipo de evento além de `transcript.partial.v2` / `transcript.final.v2`. Mudança de schema v2 só se plan provar necessidade aditiva; preferência: zero alteração de schema.
- **FR-014**: Logs de produto MUST NOT incluir áudio bruto, tokens ou dump completo de transcript (P9).

### Key Entities

- **Utterance (segmento de fala)**: intervalo de fala contínua em um **canal** até critério de fechamento; contém zero ou mais partials e, ao fechar com texto útil, exatamente um final.
- **Transcript partial (v2)**: atualização intermediária de texto em streaming; não fecha turn de Assistente.
- **Transcript final (v2)**: trecho fechado de uma utterance; elegível para detecção de pergunta e live-answer.
- **Finalization policy**: regras documentadas (pausa/silêncio, estabilidade de texto, timeout) que decidem abertura/fechamento de utterance por canal.
- **Canal de áudio**: identidade `channelId` + `sourceType` + device dentro de um `sessionId`; estado de utterance é por canal.
- **Sessão**: agrega eventos de um ou mais canais; consumidores (session-core, shell, dashboard) leem partials e finais da sessão.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após uma fala seguida de pausa suficiente (idle de ≥1 janela sem texto novo, default), um operador ou teste verifica **pelo menos um** evento de tipo **final** na sessão **sem** desligar o agent/canal — em **100%** das corridas de verificação do quickstart da feature (N ≥ 3 tentativas manuais ou suite automatizada equivalente).
- **SC-002**: Em uma utterance com múltiplos partials, o número de finais daquela utterance é **exatamente 1** (0 antes do fechamento; 1 após).
- **SC-003**: Com automático on, origem habilitada e texto de pergunta, a existência do final na sessão remove o bloqueio permanente “só partials”: o Assistente **deixa de ficar preso** em “aguardando trecho final” quando há pergunta fechada elegível (verificável em UI ou teste de orquestração com fixture de final).
- **SC-004**: Partials continuam visíveis no dashboard STT durante a fala (regressão zero de streaming): operador ainda vê texto atualizar antes do final.
- **SC-005**: Suite automatizada da política de finalização passa em ambiente CI/WSL **sem GPU** e **sem** WASAPI real.
- **SC-006**: Documentação de running/quickstart/live-answer menciona final-on-utterance e o vínculo com o Assistente; um leitor consegue executar a verificação de SC-001 a partir dos docs.
- **SC-007**: Em condições normais (janela STT default), o final aparece **no máximo cerca de uma janela de áudio** após a pausa perceptível (ordem ~3s com janela 3.2s) — não se exige sub-segundo nesta fatia.

## Assumptions

- O contrato `transcript-event.v2` já define `transcript.final.v2`; consumidores (session-core, shell, testes) já tratam o tipo — o gap é **quando** o STT emite o final, não a existência do schema.
- Live-answer e detecção de pergunta (019/023) permanecem como estão; esta feature só **alimenta** finais em tempo de conversa.
- SessionId agent ↔ shell já pode ser alinhado (020/021/022); desalinhamento de sessão é problema separado e não é “corrigido” por emitir final.
- Defaults de idle/timeout: `finalization_idle_windows = 1`, `finalization_max_open_seconds = 45` (clarify); preferir atraso de ~1 janela a spam de finais; afinação fina de UX de latência do Assistente pode ser follow-up.
- Engine de STT pode continuar processando por janelas; a state machine de utterance é responsabilidade do serviço de transcrição (lado que hoje escolhe partial vs final), não do agent Windows nem do shell.
- No pipeline atual, janela sem texto novo já resulta em “sem evento” (`None`); a state machine MUST observar **avaliações de janela** (incluindo sem texto), não só eventos partial publicados.
- Não há mudança de política de eco (ADR-0008) além de não reintroduzir eco suprimido como final.
- Fora de escopo confirmado pela issue: mudar heurística de pergunta no desktop (#52); disparar live-answer em partial.

## Out of Scope

- Disparar live-answer (ou qualquer invoke) a partir de `transcript.partial.v2`.
- Alterar heurística lexical/prosódia de pergunta (issue #52 / spec 023).
- AEC acústico completo; redesenho de noise gate do agent.
- Auto-ligar o automático do Assistente; mudar defaults de origem (system only).
- Novo schema de evento ou breaking change do contrato v2 (salvo aditivo comprovado no plan).
- UI nova no dashboard STT para “marcar” finais (finais já entram no feed se o tipo for exibido; polish de UI é opcional e não bloqueia aceite).
- Otimização de WER / troca de modelo Whisper (permanece configuração existente).

## Dependencies

- Contrato v2 de transcript e ingestão session-core de eventos de feed já existentes.
- Shell live-answer (019) e detecção de pergunta (023) como **consumidores** do final — não reimplementados aqui.
- Alinhamento de sessionId (020–022) para o cenário ponta a ponta do Assistente; testes desta feature podem validar emissão STT/session-core com sessionId de teste independente do shell.
