# Validação — issue #52 Phase A (detecção de pergunta / Assistente)

**Feature**: `specs/023-issue-52-question-detection-quality/`  
**SC**: SC-001 (automatizado), SC-002 (manual E2E), SC-003/SC-005/SC-006  
**Data**: 2026-07-25  
**Commit base**: `9aaba4f` (workspace; revalidar após merge se o SHA mudar)  
**Ambiente**: WSL (testes automatizados); E2E manual requer stack STT + session-core + desktop shell + agent Windows + provedor `live-answer`

## O que foi validado automaticamente (sem GPU / WASAPI)

Comandos (WSL):

```bash
cd apps/desktop-shell
npm test -- --run tests/assistant-auto.test.ts tests/assistant-prefs.test.ts tests/assistant-panel.test.ts tests/session-alignment.test.ts

cd apps/desktop-shell/src-tauri && cargo test --lib

PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests/test_prosody.py

mvn -q -pl services/session-core -Dtest=TranscriptEventMapperTest test
```

**Resultado (implement 2026-07-25)**:

| Suite | Resultado |
|-------|-----------|
| Vitest assistant-auto / prefs / panel / session-alignment | verde (incl. FR-002 frases *Me conte…*, *David, me descreva…*, gate FR-006, interviewMode) |
| Rust lib (prefs + feed) | verde |
| pytest prosody + schema | verde |
| Maven TranscriptEventMapper (prosody payload) | verde |

### SC-001 (heurística)

Fixtures em `assistant-auto.test.ts` cobrem:

- *Me conte sobre um projeto relevante com Java Spring* → true  
- *David, me descreva uma API REST com Spring* → true  
- *Em que sistema…* → true  
- *qualidade do serviço…* / *Vamos seguir…* → false  
- partials → não candidatos  

### SC-003 (modo entrevista)

Gate tests: Final system sem prefixo + `interviewMode` → candidate; mesmo texto em microphone → não.

### SC-005 (superfície)

Docs: `docs/development/running.md` seção **Onde ver a resposta do modelo** + quickstart da feature.

### SC-006

CI/local shell suite sem GPU.

## SC-002 — checklist E2E manual (operador)

**Pré-requisitos**: hub up (`./scripts/wsl/start-assistant-hub.sh --no-build`), shell Tauri, agent com **mesmo sessionId** da sessão ativa, provedor `live-answer` OK, profile conference-cam (remoto = system).

| # | Passo | Esperado | Status |
|---|--------|----------|--------|
| 1 | Abrir shell → Assistente | Painel visível; **não** usar :8001 como chat | [ ] |
| 2 | Automático **on**, origem **sistema** | Prefs persistidas | [ ] |
| 3 | Falar no remoto (aguardar **Final**): *Me conte sobre um projeto relevante com Java e Spring.* | Turno P:/R: (ou erro de provedor legível) no Assistente em &lt; 30s | [ ] |
| 4 | Confirmar browser `http://localhost:8001` | Só transcript/header — **sem** resposta do modelo | [ ] |
| 5 | (Opcional) modo entrevista on + Final system sem prefixo | Dispara | [ ] |

**Resultado SC-002 nesta validação**: **não executado neste ambiente** (sem stack live + agent Windows na sessão de agent).  
**Bloqueio**: requer operador com GPU/agent/provedor. Preencher a tabela acima no próximo run manual e atualizar este arquivo com `Status: PASS` e timestamp.

## Prosódia / Compose (Convergence T049)

- `PROSODY_ENABLED` / `PROSODY_END_WINDOW_MS` injetados em `infra/compose/docker-compose.yml` (default false / 500).  
- `docker-compose.gpu.yml` só sobrescreve model/device/compute; herda o restante do base compose.

## Conclusão

| ID | Estado |
|----|--------|
| SC-001 | **PASS** (automatizado) |
| SC-002 | **PENDING** manual (checklist acima) |
| SC-003 | **PASS** (automatizado) |
| SC-004 | **PASS** unitário (schema + gate + health); E2E prosody opcional |
| SC-005 | **PASS** (docs) |
| SC-006 | **PASS** (suite shell) |

Phase A de produto está **pronta para merge** do ponto de vista de código e testes determinísticos; SC-002 permanece evidência humana obrigatória antes de declarar aceite de operação completa.
