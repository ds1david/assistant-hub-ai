# Feature Specification: Live-answer — modo entrevista (contexto mic+system, 1ª pessoa, latência)

**Feature Branch**: `feature/issue-61-live-answer-modo-entrevista-contexto-mic-system`

**GitHub Issue**: [#61](https://github.com/ds1david/assistant-hub-ai/issues/61)

**Created**: 2026-07-26

**Status**: Implemented — ready for G3 validate / PR

**Input**: User description: "criar/atualizar specs/00x-issue-61-*/" — GitHub issue #61: [live-answer] Modo entrevista: contexto mic+system, resposta 1ª pessoa e latência. Pipeline live-answer já funciona ponta a ponta após finais (`transcript.final.v2`, issue #55); restam qualidade de **uso em entrevista**: resposta lenta, tom de “assistente”, e contexto que ignora o que o candidato já falou no microfone.

**Referências**:
- Issue [#61](https://github.com/ds1david/assistant-hub-ai/issues/61)
- `specs/019-auto-answer-assistant` (orquestração live-answer, painel Assistente, preferências por sessão, modos de entrada)
- `specs/023-issue-52-question-detection-quality` (detecção de pergunta; `interviewMode` como preferência de **disparo** lexical ampliado)
- `specs/024-issue-55-stt-final-utterance` (finais ao fim de utterance; knobs de finalização / idle)
- `docs/development/running.md` (modo entrevista / awaiting_final)
- Constituição P1 (spec antes de código), P5 (`sourceType` / canal ponta a ponta), P9 (privacidade), P10 (testes sem GPU)

## Problema (diagnóstico)

1. **Latência alta** até a resposta aparecer: soma de janela STT (~3s), idle de finalização, modelo de transcrição, timeout/modelo da rota de resposta ao vivo e eventual fallback.
2. **Tom inadequado** no modo entrevista: texto como orientação ao candidato (“Você poderia dizer…”, “Como candidato você deve…”), prefácios de assistente (“Claro!”), markdown e listas longas — **não** é fala pronta para o operador ler em voz alta.
3. **Contexto incompleto**: o pedido ao modelo tende a considerar sobretudo o locutor/entrevistador (origem **system**). Respostas anteriores do candidato (origem **microphone**) não entram de forma **confiável e rotulada** na janela de contexto, então o modelo não “ouve” o diálogo completo.

## Distinção obrigatória (produto)

| Papel | Origens | Comportamento |
|-------|---------|----------------|
| **Disparo** (o que gera uma nova interação automática) | Preferência do operador (`enabledSourceTypes`; default típico só **system**) | **Não** disparar a cada frase do candidato no mic |
| **Contexto** (o que vai no payload ao modelo no modo *pergunta + contexto recente*) | **system + microphone** (finais recentes da sessão), quando a preferência de incluir voz do operador estiver **ligada** | Incluir perguntas do entrevistador **e** respostas anteriores do candidato |

**Disparo ≠ contexto.** Esta feature **não** altera a regra de disparo por origem (019 / 023); ela corrige e expõe o **conteúdo de contexto** e o **estilo de resposta** no modo entrevista.

## Clarifications

### Session 2026-07-26 (defaults a partir da issue #61 — sem bloqueio)

Defaults adotados nesta spec a partir do aceite da issue e do estado do produto.

| Tema | Default adotado |
|------|-----------------|
| Contexto misto | No modo **pergunta + contexto recente**, incluir finais recentes com origem **system** e **microphone** (dentro dos limites de trechos/caracteres já existentes) |
| Preferência “Incluir minha voz no contexto” | Nova preferência **por sessão** (`includeMicrophoneInContext`); **default ON** quando ausente (opt-out explícito) — independente de modo entrevista (FR-004 / FR-006) |
| Rotulagem no contexto | Cada trecho de contexto MUST identificar o papel de origem de forma legível (entrevistador / system vs. candidato / microphone), sem exigir diarização de falantes |
| Modo `question-only` | **Inalterado**: só o texto da pergunta candidata |
| Disparo | Continua filtrado por `enabledSourceTypes` (default system); mic **não** dispara salvo habilitado no seletor de **disparo** |
| Estilo modo entrevista | 1ª pessoa (eu/meu); pt-BR natural; frases curtas; duração de leitura oral ~30–90s; sem meta-instrução, sem markdown pesado, sem inventar fatos fora do contexto; saída = **somente** o texto da fala |
| Quando aplicar o estilo | Quando **modo entrevista** da sessão estiver **ligado** (preferência já existente em 023); se desligado, estilo genérico de sugestão da 019 permanece (não é o foco desta fatia) |
| Latência | **P1**: documentar elos de atraso + defaults/ops recomendados para entrevista; latência por turn já existe no painel quando o hub devolve `latencyMs`; **sem** disparar em partial |
| Superfície de resposta | Painel **Assistente** no shell (não o dashboard STT :8001) |
| Fora | TTS automático; resposta invisível em processo seletivo real; reescrever STT/contrato v2 (salvo aditivo documentado); marketplace/billing |

### Session 2026-07-26 (clarify — pipeline chained; defaults recomendados)

Pipeline `/speckit-clarify` → plan → checklist → tasks executado em cadeia; respostas abaixo são os **defaults recomendados** (operador pode reabrir clarify se discordar).

- Q: Como injetar o estilo 1ª pessoa sem novo contrato de hub? → A: **Bloco de instrução fixo** prefixado no `input` do invoke `live-answer` quando `interviewMode=true`. Sem campo system-prompt separado no hub nesta fatia; sem mudança de schema de invoke.
- Q: Rótulos canônicos no bloco de contexto? → A: **`Entrevistador:`** para `system`; **`Candidato (eu):`** para `microphone`. Strings fixas no builder (testáveis).
- Q: Origem não canônica no buffer de contexto? → A: **Omitir** do bloco de contexto (não tratar como system nem microphone).
- Q: Enforcement de estilo na saída do modelo? → A: **Instrução forte + detector puro** (`hasMetaAssistantStyle` / equivalente) para testes e documentação. **Não** rejeitar/apagar a resposta do modelo em runtime na v1 (evita falso negativo); se no futuro houver sanitizer, MUST NOT marcar sucesso mentiroso.
- Q: Preferência de mic no contexto vs modo entrevista? → A: Campos **independentes**. Default `includeMicrophoneInContext=true` quando ausente; `interviewMode` só controla detecção (023) + estilo (esta feature).
- Q: Latência na UI (FR-017)? → A: **Já coberta** por `latencyMs` por turn no painel; esta fatia **documenta** e garante regressão visual se o campo sumir — sem segunda métrica global obrigatória.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Contexto inclui minhas respostas anteriores no mic (Priority: P1)

Em treino de entrevista, o operador (candidato) já respondeu em voz alta no microfone. Quando o entrevistador faz a **próxima** pergunta (áudio remoto → origem **system**, trecho **final**), o Assistente dispara (origem de disparo system) e o pedido ao modelo inclui, na janela de contexto recente, **tanto** as falas do entrevistador **quanto** as respostas finais recentes do **microfone** do operador — desde que a preferência “Incluir minha voz no contexto” esteja ligada.

**Why this priority**: Aceite P0 da issue #61; sem isso o modelo repete perguntas já respondidas ou ignora o fio da conversa do candidato.

**Independent Test**: Com feed de transcript contendo finais mistos (system + microphone) e modo de entrada “pergunta + contexto recente”, verificar que o payload/montagem do pedido contém texto dos finais de microfone (e rotulagem de papel); com preferência desligada, verificar que finais de microfone **não** entram no contexto (só system, além da pergunta candidata).

**Acceptance Scenarios**:

1. **Given** automático ligado, origem de **disparo** só system, modo de entrada **pergunta + contexto recente**, “Incluir minha voz no contexto” **ligado**, e a sessão tem finais recentes de `system` e `microphone`, **When** um Final `system` elegível como pergunta dispara geração, **Then** o pedido ao modelo inclui trechos finais recentes de **microphone** e de **system** (dentro do limite de janela), além da pergunta atual.
2. **Given** as mesmas preferências com “Incluir minha voz no contexto” **desligado**, **When** uma pergunta system dispara, **Then** o pedido **não** inclui trechos de origem `microphone` no bloco de contexto (só system e/ou a pergunta, conforme a janela).
3. **Given** modo de entrada **só pergunta**, **When** uma pergunta dispara, **Then** o pedido contém **somente** o texto da pergunta candidata (comportamento 019 inalterado); a preferência de voz no contexto **não** altera este modo.
4. **Given** automático ligado e origem de disparo **sem** microphone, **When** o operador fala um Final no microfone (mesmo que pareça pergunta), **Then** o Assistente **não** inicia geração só por isso.
5. **Given** trechos de contexto de origens distintas, **When** o pedido é montado, **Then** cada trecho identifica de forma legível se veio do lado do entrevistador/system ou do lado do candidato/microphone (rótulo estável e testável).

---

### User Story 2 - Resposta pronta para eu ler em voz alta (Priority: P1)

Com **modo entrevista** ligado, a resposta no painel Assistente é texto em **1ª pessoa**, oral, em português natural, sem prefácio de assistente e sem instruir o candidato na 2ª/3ª pessoa. O operador pode ler o texto em voz alta como se fosse a própria fala na entrevista.

**Why this priority**: Aceite P0 da issue #61; tom de “assistente” quebra o uso em treino de entrevista.

**Independent Test**: Gerar (ou simular o pós-processamento / instrução fixa) respostas sob modo entrevista e verificar ausência de padrões de meta-assistente acordados e presença de 1ª pessoa; spot-check manual no painel.

**Acceptance Scenarios**:

1. **Given** modo entrevista **ligado** e geração bem-sucedida, **When** o operador lê a resposta no painel Assistente, **Then** o texto está em 1ª pessoa (eu/meu/minha) e pode ser lido em voz alta sem reescrita óbvia.
2. **Given** modo entrevista **ligado**, **When** a resposta é produzida, **Then** o texto **não** contém padrões de meta-assistente da lista de regressão (FR-012): prefácios do tipo “Claro!”, “Como candidato você…”, “Você poderia dizer…”, instruções meta (“responda assim:”), nem markdown pesado de listas longas como corpo principal.
3. **Given** modo entrevista **ligado** e contexto insuficiente para inventar fatos (empresa, métricas, datas), **When** a geração conclui, **Then** a resposta permanece curta e honesta em vez de fabricar números ou nomes fora do contexto fornecido (verificável por fixture de prompt + inspeção de saída nos testes de estilo acordados; não exige LLM real em CI se houver fixture/contrato de instrução).
4. **Given** modo entrevista **desligado**, **When** uma geração ocorre, **Then** esta feature **não** exige o estilo 1ª pessoa de entrevista (comportamento de sugestão genérica da 019 permanece aceitável).

---

### User Story 3 - Preferência explícita “Incluir minha voz no contexto” (Priority: P2)

O operador vê e controla na UI do Assistente se os finais do **microfone** entram no contexto. A preferência é **por sessão**, persiste com as demais preferências do Assistente, e o default favorece o modo entrevista (ON).

**Why this priority**: Controlo e privacidade (opt-out) sem reintroduzir confusão disparo vs contexto; torna o comportamento auditável.

**Independent Test**: Alternar o controle na UI (ou via preferências injetáveis), gravar por sessão S, trocar para T e voltar a S; verificar restauração e efeito no builder de input.

**Acceptance Scenarios**:

1. **Given** o painel Assistente com sessão ativa, **When** o operador olha as preferências, **Then** existe um controle explícito com o sentido de **“Incluir minha voz no contexto”** (rótulo equivalente aceitável se legível).
2. **Given** sessão nova ou sem valor gravado para essa preferência, **When** a sessão fica ativa, **Then** o default é **ligado** (ON).
3. **Given** o operador desliga a preferência na sessão S, **When** troca para T e volta a S, **Then** a preferência permanece **desligada** em S (isolamento por sessão, alinhado a 019 FR-025).
4. **Given** o controle desabilitado por ausência de sessão / controles bloqueados, **When** o operador tenta alterar, **Then** o estado permanece coerente (não grava preferência fantasma).

---

### User Story 4 - Entender e reduzir latência percebida (Priority: P2)

O operador (e a documentação de desenvolvimento) compreendem **onde** o tempo se acumula até a resposta e quais defaults/ops usar em entrevista. Opcionalmente, o painel mostra indicação de geração e, se já houver dado, a latência do último invoke. O produto **não** regrede a política “só Final” nem spam de invoke em partial.

**Why this priority**: Issue relata “tá funcionando, mas muito lento”; documentação e defaults seguros são o corte P1 sem reescrever o STT.

**Independent Test**: Ler docs atualizados (elos de atraso + knobs); em teste automatizado, partial **não** dispara; com “gerando” + latência do último invoke (se implementado), o valor exibido corresponde ao último sucesso/erro medido.

**Acceptance Scenarios**:

1. **Given** a documentação de running / quickstart live-answer atualizada, **When** um desenvolvedor segue o modo entrevista, **Then** encontra: (a) disparo vs contexto; (b) estilo 1ª pessoa; (c) elos de atraso (janela STT, idle de finalização, modelo de transcrição, rota/modelo de resposta ao vivo, fallback); (d) defaults recomendados de ops para entrevista.
2. **Given** automático ligado, **When** chegam apenas trechos **parciais** de pergunta, **Then** **zero** novas gerações (sem regressão 019/024).
3. **Given** (opcional UI) um invoke concluído com latência conhecida, **When** o operador olha o painel, **Then** pode ver indicação de “gerando” durante o invoke e, após, a latência do último invoke se o produto já expõe esse dado.

---

### Edge Cases

- **Sem finais de microfone na sessão**: contexto usa só system (e a pergunta); não inventa fala do candidato.
- **Sem finais de system além da pergunta**: contexto ainda pode incluir mic recentes se a preferência estiver ON; pergunta candidata permanece o foco.
- **Janela cheia**: limites existentes de trechos e caracteres prevalecem; trechos mais antigos saem primeiro; não enviar transcript completo nem áudio bruto.
- **Mesmo eventId**: idempotência de tracking de finais e de disparo permanece (sem double-invoke).
- **Origem desconhecida/ausente**: **não** entra como disparo (019); para **contexto**, trechos sem origem canônica são **omitidos** (FR-007b).
- **Modo entrevista off + incluir voz on**: contexto misto ainda se aplica se modo de entrada for contexto recente; estilo 1ª pessoa **não** é obrigatório (US2 só com modo entrevista on).
- **Modo entrevista on + incluir voz off**: estilo 1ª pessoa aplica; contexto sem mic.
- **Resposta do modelo ainda com meta-assistente**: v1 **exibe** o texto retornado (FR-012b); testes garantem instrução + detector; sanitizer runtime fica fora.
- **Latência sem `latencyMs`**: UI omite o número (não inventa).
- **Conteúdo sensível**: logs **não** registram texto completo da saída do modelo nem áudio (P9).

## Requirements *(mandatory)*

### Functional Requirements

#### A — Contexto misto (P0)

- **FR-001**: No modo de entrada **pergunta + contexto recente**, o sistema MUST montar o pedido ao modelo com a pergunta candidata e uma janela curta de trechos **finais** recentes da sessão cuja origem canônica seja **`system` e/ou `microphone`**, respeitando a preferência FR-004 e os limites de trechos/caracteres já definidos na 019 (janela curta; MUST NOT enviar transcript completo nem áudio bruto).
- **FR-002**: O sistema MUST **rastrear** finais elegíveis para contexto a partir do feed da sessão ativa **independentemente** de o trecho ter disparado geração (finais de microfone que não disparam ainda assim entram no buffer de contexto quando a preferência permitir).
- **FR-003**: No modo de entrada **só pergunta**, o sistema MUST **não** anexar bloco de contexto de transcript. MUST incluir o texto da pergunta candidata. Com **modo entrevista** ligado, MUST prefixar o bloco de instrução (FR-009); com modo entrevista desligado, o pedido é só a pergunta (como 019 FR-024).
- **FR-004**: O operador MUST poder controlar, por sessão, se finais de origem **`microphone`** entram no contexto (“Incluir minha voz no contexto” ou rótulo equivalente). Default quando a preferência **não** está gravada: **ligado (ON)**.
- **FR-005**: Com a preferência FR-004 **desligada**, o bloco de contexto MUST **excluir** trechos de origem `microphone` (pode incluir `system` e a pergunta).
- **FR-006**: A preferência FR-004 MUST ser **persistida por sessão** junto com as demais preferências do Assistente (019 FR-025); isolamento entre sessões S e T MUST ser mantido.
- **FR-007**: No bloco de contexto, cada trecho incluído MUST usar rótulos canônicos: **`Entrevistador:`** para origem `system` e **`Candidato (eu):`** para origem `microphone`.
- **FR-007b**: Trechos com origem **ausente ou não canônica** MUST ser **omitidos** do bloco de contexto (MUST NOT ser rotulados como system nem microphone).
- **FR-008**: O **disparo** automático MUST continuar filtrado **apenas** por `enabledSourceTypes` (e regras de pergunta / modo entrevista de 019 e 023). MUST NOT passar a disparar em todo Final de microfone só porque o microfone entrou no contexto.

#### B — Estilo modo entrevista (P0)

- **FR-009**: Com **modo entrevista** da sessão **ligado**, o sistema MUST prefixar o `input` do invoke com um **bloco de instrução fixo** (constante de produto, versionável em testes) pedindo resposta em **1ª pessoa**, pt-BR natural, frases curtas adequadas a **~30–90 segundos** de leitura em voz alta. MUST NOT depender de novo campo de system-prompt no hub nesta fatia.
- **FR-010**: O bloco de instrução (FR-009) MUST exigir que a saída do modelo seja **somente** o texto da fala (sem prefácio de assistente, sem meta-instrução ao usuário, sem “como candidato você deve…”).
- **FR-011**: O bloco de instrução MUST proibir inventar empresas, números, datas ou fatos **fora** do contexto fornecido; se faltar contexto, pedir resposta curta e honesta.
- **FR-012**: A suíte automatizada MUST incluir: (1) assert de que o bloco de instrução de entrevista está presente no input montado quando `interviewMode=true` e **ausente** quando false; (2) detector puro de padrões proibidos em fixtures golden (sem GPU), falhando se a fixture “ruim” **não** for detectada ou se a fixture “boa” for marcada como ruim. Padrões mínimos:
  - prefácios: `Claro!`, `Claro,`, `Com certeza!` (início de resposta);
  - meta-candidato: `Como candidato`, `Você poderia dizer`, `Você deve responder`, `Na sua resposta`;
  - meta-instrução: `Responda assim`, `Aqui está uma sugestão de resposta`;
  - markdown pesado como corpo: linhas iniciando com `- ` ou `* ` em **≥ 4** itens consecutivos **ou** headings `#` / `##` no corpo principal.
- **FR-012b**: Em runtime v1, o sistema MUST NOT rejeitar nem apagar a resposta do modelo por falha do detector de estilo (exibir o texto retornado; sem sucesso mentiroso de sanitização). Detector serve a testes e eventual UX futura.
- **FR-013**: Com modo entrevista **desligado**, FR-009–012 **não** são obrigatórios (sugestão genérica 019 permanece válida).

#### C — Latência (P1)

- **FR-014**: A documentação operacional (running e/ou quickstart live-answer desta feature) MUST listar os **elos de atraso** relevantes: janela STT, idle de finalização de utterance, modelo de transcrição, timeout/modelo da rota de resposta ao vivo, fallback de provedor.
- **FR-015**: A mesma documentação MUST recomendar defaults/ops para perfil **entrevista** (ex.: modelo de transcrição de baixa latência aceitável, idle de finalização agressivo mas seguro, modelo de baixa latência na rota de resposta ao vivo), **sem** obrigar mudança de default global do produto se isso regredir outros modos.
- **FR-016**: O sistema MUST NOT disparar live-answer a partir de trechos **parciais** (sem regressão 019 FR-003 / 024).
- **FR-017**: O painel Assistente MUST continuar a exibir estado “gerando” durante invoke e, quando o hub devolver `latencyMs`, a latência **por turn** (já existente). MUST NOT inventar valores. Não exige métrica global adicional nesta fatia.

#### D — Docs e verificação

- **FR-018**: Docs MUST deixar explícito: (1) disparo ≠ contexto; (2) modo entrevista = 1ª pessoa + contexto mic+system quando a preferência de voz estiver ON; (3) a resposta aparece no **painel Assistente** do shell, não no dashboard STT.
- **FR-019**: A suíte de verificação do shell MUST cobrir, no mínimo: builder de contexto com transcript misto (mic+system); preferência OFF só system; modo só-pergunta inalterado; não-disparo por Final só no mic com default de origens; persistência por sessão da preferência de voz; regressão de padrões de estilo (FR-012); não-disparo em partial.
- **FR-020**: Logs de produto MUST NOT incluir texto completo da saída do modelo, áudio bruto ou segredos (P9).

### Key Entities

- **Preferência “Incluir minha voz no contexto”** (`includeMicrophoneInContext` no código, nome final no plan): booleano por sessão; default **true** quando ausente; controla se finais `microphone` entram no builder de contexto.
- **Buffer de finais recentes**: sequência de trechos finais da sessão com ao menos `{ identidade do trecho, texto, origem canônica }`, usada só para montagem de contexto (não redefine disparo).
- **Rótulo de papel no contexto**: marcação textual por trecho (entrevistador/system vs. candidato/microphone).
- **Modo entrevista** (já em 023): preferência por sessão que, nesta feature, também ativa o **estilo 1ª pessoa** (FR-009–012), além do comportamento de detecção já especificado em 023.
- **Modo de entrada**: `question-only` | `question-plus-recent-context` (019); só o segundo usa contexto misto.
- **Seletor de origens de disparo**: inalterado (019); independente da preferência de contexto de mic.
- **Interação do Assistente**: pergunta + resposta/estado no painel; resposta de entrevista deve ser legível como fala.
- **Elo de latência**: etapa documentada entre fala do remoto e texto no painel (STT, finalização, invoke, fallback).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos testes automatizados de contexto misto com preferência ON e ≥1 Final `microphone` + ≥1 Final `system` na janela, o pedido montado **contém** texto do microfone e do system (além da pergunta).
- **SC-002**: Em 100% dos testes com preferência OFF, o pedido montado **não** contém texto de origem `microphone` no bloco de contexto.
- **SC-003**: Com default de origens de disparo (só system), 100% dos testes com Final só no microfone **não** iniciam geração.
- **SC-004**: Com modo entrevista ON, 100% dos casos da suíte de regressão de estilo (FR-012): input montado **contém** o bloco de instrução; detector **marca** fixtures ruins e **não** marca fixtures boas em 1ª pessoa.
- **SC-005**: Em roteiro de validação documentado (automático on, disparo system, contexto recente, incluir voz on, modo entrevista on), após Final de pergunta do entrevistador o operador vê no painel Assistente uma resposta utilizável como fala em 1ª pessoa, e o pedido daquela interação incluiu contexto de mic quando havia finais de mic na sessão.
- **SC-006**: Zero gerações automáticas a partir de **parciais** nos testes de regressão (sem regressão Final-only).
- **SC-007**: Um desenvolvedor encontra em ≤ 5 minutos na documentação a distinção disparo vs contexto e a lista de knobs de latência para entrevista.
- **SC-008**: Preferência de voz no contexto: sessão sem valor inicia ON; após gravar OFF em S, alternar T→S restaura OFF em 100% dos testes de isolamento (alinhado a SC-010 da 019).
- **SC-009**: Suíte do shell (testes unitários/orquestração) permanece verde no CI sem GPU nem hardware de captura (P10).

## Assumptions

- Pipeline live-answer ponta a ponta (sessão alinhada, finais, disparo system, painel Assistente) já funciona após 019 + 023 + 024 / issue #55; esta feature é **refino de qualidade de uso em entrevista**, não bootstrap do Assistente.
- Finais de microfone e system chegam ao feed da sessão com `sourceType` canônico preservado (P5); se o feed omitir mic por falha operacional de captura, o produto não inventa contexto — apenas documenta o pré-requisito.
- Limites de janela de contexto (trechos/caracteres) da 019 permanecem válidos salvo o plan justificar ajuste aditivo documentado.
- “Modo entrevista” como preferência de sessão já existe para detecção (023); esta feature **reutiliza** o mesmo interruptor para estilo de resposta, evitando proliferar flags.
- Default ON para “incluir minha voz” equilibra utilidade em treino com opt-out de privacidade; não grava áudio — só texto final já presente no feed local.
- Redução de latência **estrutural** (STT mais rápido, modelo menor, idle=1) é majoritariamente **ops/docs** nesta fatia; mudanças de código de finalização só se forem seguras e cobertas por testes de não-regressão de Final.
- Cancelamento/conflito de perguntas, idempotência e rota de resposta ao vivo permanecem como na 019.
- Testes de estilo em CI validam **bloco de instrução + detector + fixtures**, sem chamar LLM real (P10); sem sanitizer runtime na v1 (FR-012b).
- `latencyMs` por turn já é populado pelo hub/shell (019/015); FR-017 é preservação + docs, não feature greenfield.

## Out of Scope

- Disparar live-answer em trechos **parciais** (spam de invoke).
- TTS / falar a resposta automaticamente.
- Resposta invisível em processo seletivo real (visão do produto: treino/validação sob controle do usuário).
- Reescrever o motor STT ou o contrato transcript v2 (salvo campo aditivo documentado no plan/ADR).
- Diarização multi-falante além de `sourceType` system vs microphone.
- Marketplace, billing ou cotas de provedores.
- Alterar defaults globais de disparo (automático continua off em sessão nova; origem default continua system).
- Chat multi-turno editável estilo consumidor ou personas avançadas além do bloco de estilo de entrevista.
- AEC acústico completo ou redesenho de supressão de eco.

## Dependencies

- Shell desktop com Assistente (019), preferências por sessão, modos de entrada e `interviewMode` (023).
- Finais de utterance no feed (`transcript.final.v2` / 024) para system e microphone.
- Hub de provedores com rota de resposta ao vivo configurável (015 / 019).
- Session-core e alinhamento de `sessionId` (020 / 021) para o feed correto.
- Documentação operacional existente (`docs/development/running.md`, quickstarts live-answer) como base de atualização.
