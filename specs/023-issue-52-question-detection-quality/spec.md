# Feature Specification: Qualidade de detecção de pergunta (entrevista, STT, prosódia)

**Feature Branch**: `feature/issue-52-live-answer-qualidade-de-detec-o-de-pergunta-ent`

**GitHub Issue**: [#52](https://github.com/ds1david/assistant-hub-ai/issues/52)

**Created**: 2026-07-25

**Updated**: 2026-07-25 (analyze remediation I1–X1)

**Status**: Clarified — Analyze remediado; ready for implement

**Input**: User description: "criar/atualizar specs/00x-issue-52-*/" — GitHub issue #52: [live-answer] Qualidade de detecção de pergunta (entrevista, STT, prosódia). Operador em simulação de entrevista (conference cam + áudio remoto) vê transcript no STT mas **não** vê respostas do modelo no shell; perguntas em imperativo (“Me conte…”, “David, me descreva…”) não disparam; discussão sobre entonação (prosódia), modelo STT maior que o default, e checklist A/B.

**Referências**:
- Issue [#52](https://github.com/ds1david/assistant-hub-ai/issues/52)
- `specs/019-auto-answer-assistant` (live-answer, **019 FR-004** lexical original, painel Assistente)
- `specs/020-issue-47-sessionid-align` / `specs/021-issue-49-session-list-select` (sessionId único)
- `specs/022-issue-51-stt-ui-header` (sessionId no header STT — **não** substitui o Assistente)
- Contrato versionado de transcript final (v2) e constituição P1, P5, P9, P10

## Problema (diagnóstico da sessão)

1. **Onde ver a resposta do modelo**: painel **Assistente (respostas automáticas)** do **desktop shell** — **não** o dashboard STT (`http://localhost:8001`).
2. **Por que quase nada disparava** com transcript longo de entrevista:
   - automático **off** por default (019);
   - origem default só **system** (áudio remoto = `loopback` → `sourceType: system`); microfone do candidato não dispara;
   - só trechos **Final** (partials não disparam);
   - heurística **019 FR-004** original **não** aceitava imperativos de entrevista nem vocativo (`David, me conte…`);
   - sessionId shell ≠ agent ⇒ feed/Assistente da UI não reagem.
3. **Entonação**: o modelo STT **não** expõe prosódia; detectar pergunta pela voz exige score opcional no **Final** (F0/energia no **serviço de transcrição**) + campo aditivo no evento — **não** no agent de captura.
4. **Modelo STT**: opções maiores que o default (`medium` / `large-v3` via `WHISPER_MODEL`) melhoram **WER/texto** e jargão; **não** resolvem entonação nem eco/session mismatch.

## Clarifications

### Session 2026-07-25 (produto / specify)

| Tema | Default adotado |
|------|-----------------|
| Superfície de resposta | Shell → painel Assistente; STT só transcript/header |
| Heurística lexical | Expandir **019 FR-004** → esta feature **FR-002** (imperativos, vocativo, início de sentença); limite de palavra (`qual` ≠ `qualidade`) |
| Score multimodal | OR lógico: lexical ∨ modo entrevista ∨ prosódia (não média ponderada) — **FR-006** |
| Modo entrevista | Preferência por sessão; todo Final **system** ≥ 8 chars; default off — **FR-004** (desta feature; ≠ 019 FR-004) |
| Modelo STT | Default de produto permanece `small`; docs + A/B opt-in `medium`/`large-v3`; hotwords de entrevista |
| Fora desta feature | AEC acústico completo; redesenho de eco; auto-alinhar agent; resposta no dashboard STT; auto default on |

### Session 2026-07-25 (clarify — pipeline chained; defaults recomendados)

- Q: Onde calcular e anexar `prosody` no Final? → A: **No serviço de transcrição**, no window/utterance que produz o Final, sob flag off por default. Agent de captura **não** é a fonte na v1 (corrige nota antiga “agent Windows extrai F0”).
- Q: Schema v2 com `additionalProperties: false` — como estender? → A: **Atualizar o schema v2 in-place** com propriedade opcional `prosody` (objeto). Sem dual-read v2.1 nesta fatia, a menos que testes de contrato de consumidores legados exijam; plan documenta o fallback.
- Q: UI de `prosodyThreshold` na v1? → A: **Sem controle dedicado** no painel; limiar permanece **0.65** no store/normalização. UI MUST expor `interviewMode` e `useProsody` apenas.
- Q: Empty state quando há finais mas nenhum candidato? → A: **Uma mensagem genérica** de elegibilidade (manter copy 019); detalhes de modo entrevista/prosódia ficam na documentação, não em N empty states.
- Q: Fatiamento de entrega? → A: **Phase A mergeável sozinha** (lexical + modo entrevista + docs + gate sem dependência de prosódia). Phase B (ops STT) e Phase C (prosódia) podem seguir em PRs na mesma feature branch.

### Baseline de produto (parcialmente já no shell)

- Expansão lexical de imperativos/vocativos de entrevista (pt/en, limite de palavra) e testes unitários no shell já cobrem parte de FR-002.
- **Ainda falta** nesta feature: alinhar **spec 019 FR-004** (nota superseded) + contratos/docs; modo entrevista (FR-004 desta feature); prosódia + contrato; ops de modelo STT/hotwords; gate multimodal OR (FR-006); quickstart A/B.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Imperativos e vocativos de entrevista disparam o Assistente (Priority: P1)

Operador em mock de entrevista (áudio remoto = entrevistador) liga o automático e a origem **sistema**. Frases finais como *«Me conte sobre um projeto relevante com Java Spring»* ou *«David, me descreva uma API REST…»* disparam turno no painel Assistente (P: / R: ou erro de provedor legível).

**Why this priority**: Caso real da sessão; **019 FR-004** original falhava no padrão de entrevista.

**Independent Test**: Vitest com fixtures de texto (sem GPU); E2E manual com shell + session-core + provider.

**Acceptance Scenarios**:

1. **Given** automático on, origem system, **When** chega `Final` com texto *«Me conte sobre um projeto relevante com Java Spring»* e `sourceType=system`, **Then** o orquestrador cria candidato e inicia invoke `live-answer` (ou mostra conflito se busy).
2. **Given** texto *«David, me descreva uma API REST com Spring»*, **When** classificado, **Then** `looksLikeQuestion` = true.
3. **Given** texto *«Claro, sem problema. Me descreva uma API REST com Java»*, **When** classificado, **Then** true (pergunta após sentença).
4. **Given** *«Vamos seguir com o plano combinado»* ou *«qualidade do serviço ficou estável»*, **When** classificado, **Then** false.
5. **Given** partial com o mesmo texto interrogativo, **When** processado, **Then** **não** dispara.

---

### User Story 2 - Operador entende **onde** e **por que** não há resposta (Priority: P1)

Operador confuso entre STT e shell recebe orientação no **produto/docs**: respostas só no painel **Assistente**; o dashboard STT não é chat. Empty states da UI cobrem **automático off** e **nenhuma pergunta elegível** (mensagem genérica 019). Diagnóstico de origem desmarcada, sessionId desalinhado ou partial vs Final fica na **documentação** (não em N empty states distintos).

**Why this priority**: “Onde era pra eu ver o retorno do modelo?” foi a primeira falha de usabilidade.

**Acceptance Scenarios**:

1. **Given** docs `running.md` / quickstart desta feature, **When** o operador segue o fluxo mínimo, **Then** encontra explicitamente: resposta = shell Assistente; STT ≠ chat.
2. **Given** automático off e finais no feed, **When** empty state, **Then** copy *Automático desligado…* (já 019; manter).
3. **Given** finais sem pergunta elegível e modo entrevista off, **When** empty state, **Then** mensagem genérica de elegibilidade (*nenhum foi reconhecido como pergunta elegível…*); docs cobrem checklist de disparo (origem, sessionId, Final).

---

### User Story 3 - Modo entrevista (candidato amplo no áudio remoto) (Priority: P2)

Em treino, o operador habilita **modo entrevista**: qualquer `Final` da origem **system** com comprimento ≥ 8 (após trim) torna-se candidato a resposta automática, **mesmo sem** `?`/prefixo — além dos que já passam na heurística.

**Why this priority**: Imperativos e turns do entrevistador variam; lexical nunca cobrirá 100%.

**Acceptance Scenarios**:

1. **Given** modo entrevista on + auto on + origem system, **When** `Final` system *«Sobre o projeto na Claro, fale do seu papel.»* (sem `?`/prefixo canônico), **Then** dispara.
2. **Given** modo entrevista on, **When** `Final` **microphone** *«Eu implementei X»*, **Then** **não** dispara só por causa do modo (modo entrevista aplica-se só a `system`, salvo preferência futura explícita).
3. **Given** modo entrevista off, **When** o mesmo texto system sem prefixo, **Then** não dispara (salvo `?`/heurística).
4. Preferência **por sessão**, persistida com as demais prefs do Assistente; default **off**.

---

### User Story 4 - Qualidade de STT (modelo + hotwords) melhora o input (Priority: P2)

Operador com GPU configura `WHISPER_MODEL=medium` (ou `large-v3`) e hotwords de entrevista; transcript do remoto fica mais fiel (Java, Spring, REST, nomes), reduzindo lixo que quebra a heurística.

**Why this priority**: Transcript ruim (*reto!*, *peco-messe*) impede lexical e confunde o LLM.

**Acceptance Scenarios**:

1. **Given** `.env` com `WHISPER_MODEL=medium` e container recriado, **When** health/STT sobe, **Then** `/health` (ou equivalente) reporta o modelo carregado `medium`.
2. **Given** hotwords em `config/whisper-hotwords.txt` (Spring, REST, …), **When** fala jargão, **Then** taxa de erro lexical cai vs baseline (checklist A/B manual; não exige métrica WER automatizada nesta fatia).
3. Documentação lista trade-off latência/VRAM e passos de rollback para `small`.

---

### User Story 5 - Score de entonação (prosódia) no Final (Priority: P3)

O **serviço de transcrição**, no fechamento do window que gera o **Final** de um canal, estima contorno de pitch/energia e anexa score opcional ao evento final. O shell usa o score no gate multimodal. O agent de captura Windows **não** calcula prosódia nesta fatia.

**Why this priority**: Ajuda yes/no sem `?`; não substitui lexical em imperativos.

**Acceptance Scenarios**:

1. **Given** prosódia habilitada no STT (`PROSODY_ENABLED`) e window final com subida de F0, **When** emite `transcript.final.v2` (extensão aditiva), **Then** payload inclui `prosody.questionScore` ∈ [0,1] e opcionalmente `contour` / `f0EndSlopeSemitones` — **sem** áudio bruto.
2. **Given** falha do extrator de F0, **When** emite final, **Then** evento segue **sem** `prosody` (ou score null); transcript **não** falha.
3. **Given** shell com `useProsody` on e threshold 0.65, **When** texto **não** lexical-question mas `questionScore ≥ 0.65` e origem habilitada e Final, **Then** dispara.
4. **Given** `useProsody` off, **When** score alto no evento, **Then** score **não** sozinho dispara (só lexical / modo entrevista).
5. Testes do extrator usam **fixtures de áudio sintético** ou features mock no **transcription-service** — sem WASAPI real e sem testes no agent (P10).

---

### User Story 6 - Gate multimodal unificado (Priority: P2)

Uma função pura `isQuestionCandidate(entry, prefs)` combina:

- lexical **FR-002** (lista expandida; supersede de **019 FR-004** no shell);
- modo entrevista **FR-004** (system finals ≥ 8);
- prosódia (se prefs e campo presentes; **FR-007/008**).

**Acceptance Scenarios**:

1. Tabela de verdade coberta por testes (ver `research.md` / tasks).
2. Preferências expõem: `interviewMode`, `useProsody`, `prosodyThreshold` (defaults: false, false, 0.65).
3. Empty state: **uma** mensagem genérica de elegibilidade (como 019); detalhes de modo entrevista/prosódia em docs, não em múltiplos empty states.

---

### Edge Cases

- **Texto curto** (&lt; 8 chars após trim): nunca candidato lexical nem por modo entrevista.
- **Partial** com texto interrogativo completo: **não** dispara (só `Final`).
- **Prefixo embutido em palavra** (`qualidade`, `quandoquer`): **não** conta como lexical-question.
- **Modo entrevista on** + final de **microfone**: **não** vira candidato só por causa do modo.
- **Automático off** com finais elegíveis: sem invoke; empty state orienta ligar o automático.
- **sessionId do feed ≠ sessão ativa do shell**: Assistente não reage (regra 020/021; não regredir).
- **Prosódia ausente ou extrator falhou**: evento final permanece válido; gate ignora braço de prosódia.
- **`useProsody` off** com score alto no evento: score **não** dispara sozinho.
- **Orquestrador ocupado** (turno em andamento): conflito legível; não enfileirar em silêncio (comportamento 019).
- **Transcript ruidoso / jargão errado**: lexical pode falhar; ops de modelo STT + hotwords (US4) são o mitigator — não inventar match fuzzy de typos nesta fatia.
- **Múltiplas frases no mesmo Final**: candidatos de início incluem segmentos após `.` / `!` e vocativo (FR-002).

---

## Requirements *(mandatory)*

### Functional Requirements

### FR-001 — Superfície de resposta (norma)

O produto MUST documentar e manter: respostas do modelo da rota `live-answer` aparecem **somente** no painel Assistente do desktop shell. O dashboard STT MUST NOT ser descrito como superfície de chat/resposta.

### FR-002 — Heurística lexical expandida (substitui/estende 019 FR-004 no shell)

Um trecho `Final` MUST ser lexical-question se, após trim, length ≥ 8 **e** qualquer um:

1. contém `?`; **ou**
2. algum **candidato de início** começa com prefixo da lista canônica expandida (pt/en), com **limite de palavra** (próximo char vazio ou `[\s,?!:;.\-']`).

**Candidatos de início**: texto completo lowercased; texto após **vocativo** `Nome, `; segmentos após `.` ou `!`.

**Prefixos pt (mínimo; mais longos primeiro)**:  
`será que`, `me descreva`, `me conte`, `me conta`, `me fale`, `me fala`, `me diga`, `me explique`, `pode me`, `pode descrever`, `pode explicar`, `pode contar`, `conte sobre`, `conte-me`, `conte me`, `descreva`, `explique`, `por que`, `porque`, `para que`, `pra que`, `em que`, `o que`, `quais`, `qual`, `quem`, `quando`, `onde`, `como`.

**Prefixos en (mínimo)**:  
`tell me about`, `tell me`, `walk me through`, `describe`, `explain`, `what`, `which`, `who`, `when`, `where`, `why`, `how`, `is `, `are `, `do `, `does `, `can `, `could `, `would `.

MUST rejeitar: curtos &lt; 8; `qualidade…` sem `?`; afirmações de continuidade (*vamos seguir…*) sem prefixo.

A spec 019 FR-004 MUST ser referenciada como **superseded no shell** por esta FR-002 (documentar em research/plan; não reescrever todo 019).

### FR-003 — Filtro de origem e Final (herdado 019)

Disparo automático MUST exigir: `kind=Final`, origem canônica em `enabledSourceTypes`, `autoEnabled=true`, sessionId alinhado. Partials MUST NOT disparar.

### FR-004 — Modo entrevista

> **Numeração**: FR-004 **desta feature** = modo entrevista. A heurística lexical legada de `specs/019-auto-answer-assistant` continua referida como **019 FR-004** (superseded no shell por **FR-002**). Não confundir os dois IDs.

Preferência por sessão `interviewMode: boolean` default `false`.  
Se true: todo `Final` com `sourceType` canônico **system**, length ≥ 8, MUST ser candidato **além** de FR-002.  
MUST NOT aplicar o atalho a `microphone` nesta fatia.

### FR-005 — Preferências estendidas

Persistir por sessão (mesmo store 019), sem segredos:

| Campo | Tipo | Default |
|-------|------|---------|
| `autoEnabled` | bool | false (019) |
| `enabledSourceTypes` | system/microphone[] | [system] |
| `inputMode` | enum | question-plus-recent-context |
| `interviewMode` | bool | false |
| `useProsody` | bool | false |
| `prosodyThreshold` | number 0–1 | 0.65 |

UI do painel Assistente MUST expor toggles para `interviewMode` e `useProsody`.  
`prosodyThreshold` MUST permanecer no store com default **0.65** e normalização; **MUST NOT** exigir controle de UI na v1 (constante documentada; ainda testável via prefs/API de prefs).

### FR-006 — Gate multimodal

```
candidate =
  Final
  AND origin enabled
  AND (
    looksLikeQuestion(text)                          // FR-002
    OR (interviewMode AND origin == system AND len>=8)
    OR (useProsody AND prosody.questionScore >= threshold)
  )
```

MUST ser função pura testável.

### FR-007 — Contrato de prosódia (aditivo)

Estender o evento de transcript de forma **aditiva** atualizando `transcript-event.v2.schema.json` **in-place** com propriedade opcional `prosody` (o schema atual tem `additionalProperties: false`, portanto o campo MUST ser declarado explicitamente). Fallback v2.1 só se testes de contrato de consumidores legados o exigirem (ver plan/research).

Objeto opcional:

```json
"prosody": {
  "questionScore": 0.0,
  "contour": "rising|falling|flat|unknown",
  "f0EndSlopeSemitones": 0.0
}
```

- `questionScore`: number [0,1]
- campos adicionais MAY; consumidores MUST ignorar desconhecidos se o schema permitir
- MUST NOT incluir PCM, path de arquivo de áudio, ou texto além do já em `text`
- Ausência de `prosody` = comportamento atual

### FR-008 — Extração de prosódia (fonte do score)

- O score de prosódia MUST ser calculado no **serviço de transcrição**, no fechamento do window/utterance que gera o **Final**, por canal, sem misturar canais.
- Entrada: áudio do window em memória do STT; MUST NOT logar amostras nem paths de áudio bruto.
- O agent de captura Windows MUST NOT ser a fonte de `prosody` nesta fatia.
- Evento final consumido pelo shell MUST poder trazer `prosody` opcional.
- Falha do extrator: omitir `prosody`, **nunca** dropar o final.
- Prosódia MUST ser desligável por configuração (default **off**).

### FR-009 — Ops de qualidade de STT (modelo + hotwords)

Documentar no guia de operação e no quickstart desta feature:

1. Como trocar o modelo STT entre o default do produto e opções maiores (melhor texto / mais VRAM e latência)
2. Passos de recriar o serviço e de rollback ao default
3. Ordem de grandeza de custo de recursos (VRAM/latência)
4. Amostra de hotwords de entrevista técnica e onde configurá-los
5. Checklist A/B com 3 frases fixas (baseline vs modelo maior)

Esta FR é **documentação operacional + amostra de hotwords + visibilidade de modelo no health** se ainda não existir; não muda o default do produto.

### FR-010 — Privacidade e logs

MUST NOT logar: tokens de provedor, PCM, conteúdo completo de transcript em nível DEBUG em produção defaults. Prosódia só scores agregados.

### FR-011 — Testes

- Shell: testes automatizados de FR-002 (lexical), FR-004 (modo entrevista), FR-006 (gate) e preferências (sem GPU).
- **transcription-service** apenas: testes unitários do extrator de prosódia com fixture sintético; teste de contrato se o schema de evento mudar. MUST NOT exigir testes no agent de captura Windows para prosódia.
- CI MUST NOT exigir GPU nem WASAPI real.

### FR-012 — Alinhamento sessionId (não regredir)

Manter regras 020/021/022: mesmo sessionId; header STT ajuda o operador; Assistente só reage à sessão ativa.  
Trabalho **herdado** (não é feature net-new): MUST ter tarefa de regressão que reexecute testes de alinhamento existentes (ver tasks).

## Non-Functional

- **NFR-001**: Expansão lexical e modo entrevista MUST permanecer em CPU trivial no path de UI — meta de plan: **&lt; 1 ms por Final** classificado em fixture de teste (sem I/O de rede).
- **NFR-002**: Prosódia no path de final MUST ter budget **documentado** (ordem de dezenas de ms por final curto em fixture) **ou**, se não medido na fatia, nota explícita “unmeasured; default off permanece” em research/validation — e MUST permanecer desligável por flag.
- **NFR-003**: Compatibilidade aditiva de contrato; clientes antigos ignoram `prosody`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

| ID | Critério |
|----|----------|
| SC-001 | Frases de entrevista da sessão real (*Me conte…*, *David, me descreva…*, *Em que sistema…*) são reconhecidas como pergunta elegível nos testes de heurística |
| SC-002 | Com automático ligado, origem system habilitada e provedor OK, mock de entrevista gera ≥1 turno no painel Assistente em &lt; 30s após pergunta final elegível (quickstart manual) |
| SC-003 | Com modo entrevista ligado, um Final **system** sem prefixo interrogativo vira candidato; o mesmo texto em **microfone** não vira candidato só por causa do modo |
| SC-004 | Evento final **sem** prosódia continua válido para consumidores; com prosódia presente e preferência ligada, o shell respeita o limiar configurado |
| SC-005 | Documentação deixa inequívoco que a resposta do modelo **não** aparece no dashboard STT |
| SC-006 | Suite automatizada do shell que cobre detecção permanece verde sem GPU |

## Out of Scope

- Respostas do modelo renderizadas no dashboard STT
- AEC acústico / redesenho de eco-suppression (apenas não regredir)
- Classificador neural pesado de speech-act na v1
- Treino de modelo de prosódia com dataset grande
- Auto-start do agent com sessionId da UI sem ação do operador
- Mudar defaults globais para automático **on** (permanece off por privacidade/visão 019)
- Mudar o default de modelo STT do produto (permanece o default atual; upgrade é opt-in)
- Tradução simultânea / diarização multi-speaker

## Key Entities *(mandatory when data involved)*

- **QuestionCandidate**: trecho final elegível a resposta automática (texto, origem, canal, score de prosódia opcional)
- **AssistantSessionPreferences**: preferências por sessão do Assistente, incluindo `interviewMode`, `useProsody`, `prosodyThreshold`
- **ProsodyFeatures**: score de “soa como pergunta” e metadados de contorno (sem áudio bruto)
- **Transcript Final**: trecho final de transcrição com campos existentes + `prosody` opcional

## Assumptions

- Áudio remoto do entrevistador chega com origem canônica **system** (loopback / captura de saída no perfil).
- Labels de perfil (*Microfone da conference cam*, *Áudio remoto…*) **não** alteram o `sourceType` canônico.
- Provedor da rota de resposta automática já configurado é pré-requisito de SC-002, não da detecção em si.
- Heurística lexical expandida e modo entrevista entregam valor de Phase A sem prosódia (Phase C pode seguir em PR separada).
- Pasta canônica desta feature: `specs/023-issue-52-question-detection-quality/` (renomeada de `023-question-detection-quality` no specify).
