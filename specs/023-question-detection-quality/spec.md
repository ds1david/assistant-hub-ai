# Feature Specification: Qualidade de detecção de pergunta (entrevista, STT, prosódia)

**Feature Branch**: `feature/023-question-detection-quality` (sugerida)

**GitHub Issue**: [#52](https://github.com/ds1david/assistant-hub-ai/issues/52)

**Created**: 2026-07-25

**Status**: Draft — Ready for plan/tasks (defaults da conversa de produto 2026-07-25)

**Input**: Consolidação da sessão de operação/produto: operador em simulação de entrevista (conference cam + áudio remoto) vê transcript no STT mas **não** vê respostas do ChatGPT no shell; perguntas em imperativo (“Me conte…”, “David, me descreva…”) não disparam; discussão sobre entonação (prosódia), modelo Whisper maior que `small`, e checklist A/B.

**Referências**:
- Issue [#52](https://github.com/ds1david/assistant-hub-ai/issues/52)
- `specs/019-auto-answer-assistant` (live-answer, FR-004 original, painel Assistente)
- `specs/020-issue-47-sessionid-align` / `specs/021-issue-49-session-list-select` (sessionId único)
- `specs/022-issue-51-stt-ui-header` (sessionId no header STT — **não** substitui o Assistente)
- Contrato `contracts/transcript-event.v2.schema.json`
- Defaults STT: `WHISPER_MODEL=small`, `cuda`, `float16` (README / compose)
- Constituição P1 (spec antes de domínio), P5 (canal/origem), P9 (sem áudio bruto em log), P10 (testes sem GPU/WASAPI real quando possível)

## Problema (diagnóstico da sessão)

1. **Onde ver a resposta do modelo**: painel **Assistente (respostas automáticas)** do **desktop shell** — **não** o dashboard STT (`http://localhost:8001`).
2. **Por que quase nada disparava** com transcript longo de entrevista:
   - automático **off** por default (019);
   - origem default só **system** (áudio remoto = `loopback` → `sourceType: system`); microfone do candidato não dispara;
   - só trechos **Final** (partials não disparam);
   - heurística FR-004 original **não** aceitava imperativos de entrevista nem vocativo (`David, me conte…`);
   - sessionId shell ≠ agent ⇒ feed/Assistente da UI não reagem.
3. **Entonação**: Whisper **não** expõe prosódia; detectar pergunta pela voz exige features no agent (F0/energia) + campo aditivo no evento.
4. **Modelo Whisper**: `medium` / `large-v3` melhoram **WER/texto** e jargão; **não** resolvem entonação nem eco/session mismatch.

## Clarifications / Defaults (sessão 2026-07-25)

| Tema | Default adotado |
|------|-----------------|
| Superfície de resposta | Shell → painel Assistente; STT só transcript/header |
| Heurística lexical | Expandir FR-004 (imperativos, vocativo, início de sentença); limite de palavra (`qual` ≠ `qualidade`) |
| Score multimodal | Combinar texto + `?` + (futuro) `prosody.questionScore` com threshold configurável |
| Prosódia v1 | Score opcional no **Final** do canal; sem PCM em log; agent Windows extrai F0 no fim do utterance |
| Modo entrevista | Preferência por sessão: opcionalmente tratar **todo Final de origem system** como candidato (com min length), além da heurística |
| Whisper | Documentar + checklist A/B `small`→`medium` (e `large-v3` se VRAM); hotwords de entrevista |
| Fora desta feature | AEC acústico completo; mudar eco-suppression além do já existente; auto-alinhar agent sem ação do operador; resposta no dashboard STT |

### Já parcialmente implementado (baseline de código)

- Expansão lexical em `apps/desktop-shell/src/assistant-auto.ts` (`me conte`, `me descreva`, vocativo, sentença após `.!`, EN `tell me` / `describe`, word boundary).
- Testes em `apps/desktop-shell/tests/assistant-auto.test.ts`.
- **Ainda falta** nesta feature: alinhar **spec 019 FR-004** + contratos/docs; modo entrevista; prosódia + contrato; ops Whisper/hotwords; score combinado; quickstart A/B.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Imperativos e vocativos de entrevista disparam o Assistente (Priority: P1)

Operador em mock de entrevista (áudio remoto = entrevistador) liga o automático e a origem **sistema**. Frases finais como *«Me conte sobre um projeto relevante com Java Spring»* ou *«David, me descreva uma API REST…»* disparam turno no painel Assistente (P: / R: ou erro de provedor legível).

**Why this priority**: Caso real da sessão; FR-004 original falhava no padrão de entrevista.

**Independent Test**: Vitest com fixtures de texto (sem GPU); E2E manual com shell + session-core + provider.

**Acceptance Scenarios**:

1. **Given** automático on, origem system, **When** chega `Final` com texto *«Me conte sobre um projeto relevante com Java Spring»* e `sourceType=system`, **Then** o orquestrador cria candidato e inicia invoke `live-answer` (ou mostra conflito se busy).
2. **Given** texto *«David, me descreva uma API REST com Spring»*, **When** classificado, **Then** `looksLikeQuestion` = true.
3. **Given** texto *«Claro, sem problema. Me descreva uma API REST com Java»*, **When** classificado, **Then** true (pergunta após sentença).
4. **Given** *«Vamos seguir com o plano combinado»* ou *«qualidade do serviço ficou estável»*, **When** classificado, **Then** false.
5. **Given** partial com o mesmo texto interrogativo, **When** processado, **Then** **não** dispara.

---

### User Story 2 - Operador entende **onde** e **por que** não há resposta (Priority: P1)

Operador confuso entre STT e shell recebe orientação no produto/docs: respostas só no Assistente; empty states explicam automático off, sem origem, sem pergunta elegível, mismatch de sessão.

**Why this priority**: “Onde era pra eu ver o retorno do ChatGPT?” foi a primeira falha de usabilidade.

**Acceptance Scenarios**:

1. **Given** docs `running.md` / quickstart desta feature, **When** o operador segue o fluxo mínimo, **Then** encontra explicitamente: resposta = shell Assistente; STT ≠ chat.
2. **Given** automático off e finais no feed, **When** empty state, **Then** copy *Automático desligado…* (já 019; manter).
3. **Given** finais sem pergunta elegível e modo entrevista off, **When** empty state, **Then** *nenhum foi reconhecido como pergunta elegível…*.

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

Agent Windows, no fechamento do utterance de um canal, estima contorno de pitch/energia e anexa score opcional ao evento **final** de transcript. O shell usa o score no gate multimodal.

**Why this priority**: Ajuda yes/no sem `?`; não substitui lexical em imperativos.

**Acceptance Scenarios**:

1. **Given** prosódia habilitada no agent e utterance final com subida de F0, **When** emite `transcript.final.v2` (ou extensão aditiva), **Then** payload inclui `prosody.questionScore` ∈ [0,1] e opcionalmente `contour` / `f0EndSlopeSemitones` — **sem** áudio bruto.
2. **Given** falha do extrator de F0, **When** emite final, **Then** evento segue **sem** `prosody` (ou score null); transcript **não** falha.
3. **Given** shell com `useProsody` on e threshold 0.65, **When** texto **não** lexical-question mas `questionScore ≥ 0.65` e origem habilitada e Final, **Then** dispara.
4. **Given** `useProsody` off, **When** score alto no evento, **Then** score **não** sozinho dispara (só lexical / modo entrevista).
5. Testes do extrator usam **fixtures de áudio sintético** ou features mock — sem WASAPI real (P10).

---

### User Story 6 - Gate multimodal unificado (Priority: P2)

Uma função pura `isQuestionCandidate(entry, prefs)` combina:

- lexical FR-004 expandido;
- modo entrevista (system finals);
- prosódia (se prefs e campo presentes).

**Acceptance Scenarios**:

1. Tabela de verdade coberta por testes (ver `research.md` / tasks).
2. Preferências expõem: `interviewMode`, `useProsody`, `prosodyThreshold` (defaults: false, false, 0.65).
3. Empty state distingue “sem elegível lexical” vs “modo entrevista off / prosódia off” apenas se necessário; não poluir UI — preferir uma mensagem genérica de elegibilidade + docs.

---

## Requirements (Functional)

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

UI do painel Assistente MUST expor toggles/campos para `interviewMode` e `useProsody`; threshold MAY ser só config avançada ou constante documentada na v1 se a UI ficar densa (default fixo 0.65 ainda testável).

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

Estender o evento de transcript de forma **aditiva** (preferência: permitir objeto opcional `prosody` em v2 via revisão de schema compatível, ou `transcript-event.v2.1` se `additionalProperties: false` for intocável sem bump).

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

### FR-008 — Extração de prosódia no agent

- Onde: `agents/windows-audio-agent`, por canal isolado, no fechamento do utterance associado ao final
- Entrada: buffer PCM do utterance (memória do worker); MUST NOT logar amostras
- Saída: preencher `prosody` no payload enviado ao STT **ou** anexar no serviço de transcrição se o final for emitido só no STT — **decisão de plan**: preferir anexar no **STT** se o final nasce lá; se o agent só manda áudio, prosódia pode ser (a) no agent via metadado de chunk final, ou (b) no STT a partir do window final. **Default de implementação**: extrair no **STT** no window que vira `transcript.final.v2` (mesmo processo que já tem o áudio do window), para não alterar o path de áudio do agent; se inviável, plan documenta fallback agent-side.
- Falha do extrator: omitir `prosody`, nunca dropar o final
- Flag de settings: `PROSODY_ENABLED=false` default

### FR-009 — Ops Whisper

Documentar em `docs/development/running.md` (e quickstart desta feature):

1. Troca `WHISPER_MODEL=small|medium|large-v3`
2. Recriar container; sem rebuild de imagem obrigatório
3. VRAM/latência esperados (ordem de grandeza)
4. Hotwords: `config/whisper-hotwords.txt` — amostra de termos de entrevista técnica
5. Checklist A/B (3 frases fixas) small vs medium

Código de settings/compose já existe; esta FR é **docs + sample hotwords + health visibility** se ainda não mostrar modelo.

### FR-010 — Privacidade e logs

MUST NOT logar: tokens de provedor, PCM, conteúdo completo de transcript em nível DEBUG em produção defaults. Prosódia só scores agregados.

### FR-011 — Testes

- Shell: vitest FR-002, FR-004, FR-006, prefs
- STT/agent: testes unitários do extrator com fixture; schema contract test se schema mudar
- Sem GPU/WASAPI obrigatório na CI

### FR-012 — Alinhamento sessionId (não regredir)

Manter regras 020/021/022: mesmo sessionId; header STT ajuda o operador; Assistente só reage à sessão ativa.

## Non-Functional

- **NFR-001**: Expansão lexical e modo entrevista não aumentam latência de UI de forma perceptível (CPU trivial).
- **NFR-002**: Prosódia no path de final MUST ter budget documentado (ex. &lt; 20 ms CPU por final em fixture 1s @16kHz) ou desligar sob flag se exceder em medição.
- **NFR-003**: Compatibilidade aditiva de contrato; clientes antigos ignoram `prosody`.

## Success Criteria

| ID | Critério |
|----|----------|
| SC-001 | Frases de entrevista da sessão real (*Me conte…*, *David, me descreva…*, *Em que sistema…*) passam nos testes de heurística |
| SC-002 | Com auto on + system + medium (opcional) + provider OK, mock de entrevista gera ≥1 turno Assistente em &lt; 30s após pergunta final elegível (manual quickstart) |
| SC-003 | Modo entrevista on faz Final system sem prefixo disparar; mic não |
| SC-004 | Evento final sem prosódia continua válido; com prosódia o shell respeita threshold |
| SC-005 | Docs deixam inequívoco: resposta ≠ dashboard STT |
| SC-006 | CI shell verde sem GPU |

## Out of Scope

- Respostas renderizadas no `index.html` do STT
- AEC acústico / redesenho de eco-suppression (apenas não regredir)
- Classificador neural pesado de speech-act na v1
- Treino de modelo de prosódia com dataset grande
- Auto-start do agent com sessionId da UI sem ação do operador
- Mudar defaults globais para auto **on** (permanece off por privacidade/visão 019)
- Tradução simultânea / diarização multi-speaker

## Key Entities

- **QuestionCandidate**: eventId, text, channelId, sourceType, optional prosodyScore
- **AssistantSessionPreferences**: + interviewMode, useProsody, prosodyThreshold
- **ProsodyFeatures**: questionScore, contour, f0EndSlopeSemitones
- **Transcript Final**: kind Final + fields v2 + optional prosody

## Assumptions

- Áudio remoto do entrevistador chega como `sourceType=system` (loopback / kind loopback no profile).
- Conference cam profile labels (*Microfone da conference cam*, *Áudio remoto…*) não alteram sourceType.
- Provedor `live-answer` já configurado é pré-requisito de SC-002, não desta detecção.
