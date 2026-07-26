# Tasks: Qualidade de detecção de pergunta

**Spec**: `specs/023-question-detection-quality/spec.md`  
**Plan**: `plan.md`

## Phase A — Lexical, gate, modo entrevista, docs

- [ ] T001 Verificar e completar testes FR-002 (frases da sessão real + rejeições) em `apps/desktop-shell/tests/assistant-auto.test.ts`
- [ ] T002 Exportar e documentar no código a lista canônica alinhada à FR-002; nota “supersedes 019 FR-004” em `specs/019-auto-answer-assistant/spec.md` (bloco curto Clarifications) e em `data-model.md` 019 se necessário
- [ ] T003 Estender `AssistantSessionPreferences` com `interviewMode`, `useProsody`, `prosodyThreshold` + `normalizePrefs` defaults — `assistant-prefs.ts` + testes
- [ ] T004 Persistir novos campos no store Tauri/Rust (mesmos comandos get/set assistant prefs) se o tipo Rust for explícito
- [ ] T005 Implementar `isQuestionCandidate` (FR-006) e fazer `shouldAutoAnswerFromEntry` / `extractNewQuestions` usarem o gate — `assistant-auto.ts`
- [ ] T006 Toggle UI “modo entrevista” no painel Assistente — `assistant-panel.ts` + teste de render
- [ ] T007 Docs: onde ver ChatGPT; gates de disparo; sessionId — `docs/development/running.md` + trecho min-flow se couber
- [ ] T008 Quickstart Phase A em `specs/023-question-detection-quality/quickstart.md` (seção A)

## Phase B — STT quality ops

- [ ] T009 Sample/atualização `config/whisper-hotwords.txt` (ou sample em `samples/`) com termos de entrevista técnica PT/EN
- [ ] T010 Documentar WHISPER_MODEL medium/large-v3, VRAM, recriar container, rollback — running.md + `.env.example` comentários
- [ ] T011 Garantir health/status expõe `model` (já existe em parte) e documentar como verificar
- [ ] T012 Checklist A/B small vs medium no quickstart (3 frases fixas)

## Phase C — Prosódia

- [ ] T013 Atualizar schema transcript (`v2` aditivo ou `v2.1`) + contrato `contracts/question-detection.md` / schema file
- [ ] T014 Settings `PROSODY_ENABLED`, `PROSODY_END_WINDOW_MS` no transcription-service
- [ ] T015 Implementar extrator F0 → questionScore (falha omite prosody) + pytest com fixture sintética
- [ ] T016 Anexar `prosody` apenas em `transcript.final.v2` emitido
- [ ] T017 Tipar `prosody` no feed do shell (`api-client.ts` / transcript feed)
- [ ] T018 Ramo useProsody no gate + toggle UI (ou pref avançada) + testes
- [ ] T019 Health `prosodyEnabled` + quickstart Phase C
- [ ] T020 Análise de budget CPU (nota em research ou validation) — desligar default permanece false

## Dependencies

```
T001 → T005
T003 → T004 → T006
T005 → T006
T007 → T008
T009 → T010 → T012
T013 → T014 → T015 → T016 → T017 → T018 → T019
```

## Parallelism

- T007/T008 docs // T003 prefs
- T009 hotwords // T001 tests
- Phase C só após Phase A estável (gate já unificado facilita T018)

## Definition of done (feature)

- [ ] SC-001…SC-006 da spec
- [ ] Phase A mergeável sozinha se C adiar
- [ ] CI shell sem GPU verde
- [ ] Nenhuma regressão: auto default off; mic default off; partials não disparam
