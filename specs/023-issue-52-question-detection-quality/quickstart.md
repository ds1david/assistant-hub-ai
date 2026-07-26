# Quickstart: Qualidade de detecção de pergunta (issue #52)

**Feature**: `specs/023-issue-52-question-detection-quality/`

## Pré-requisitos

- Stack: STT + session-core + agent + **desktop shell** (`docs/development/running.md`)
- Provedor na rota `live-answer` com credencial válida
- Profile conference cam (remoto = system):  
  `samples/audio-profiles/conference-cam-endpointid.yaml`
- **Mesmo sessionId** shell ↔ agent ↔ STT (header STT / sessão ativa no shell)

## Onde ver a resposta do modelo

| Superfície | O que é |
|------------|---------|
| Desktop shell → **Assistente (respostas automáticas)** | Pergunta + resposta (ou erro de provedor) |
| `http://localhost:8001` dashboard STT | Só transcript / sessionId / canais — **não** é o chat |

## Phase A — Disparo lexical / entrevista (sem trocar modelo STT)

1. Suba o hub e o shell; crie/selecione sessão; inicie agent com o **UUID** da sessão ativa.
2. No Assistente: ligue **automático**; origem **sistema** marcada.
3. (Opcional) ligue **modo entrevista** para qualquer final system ≥ 8 chars.
4. No áudio remoto, fale (e espere **final**):
   - *«Me conte sobre um projeto relevante com Java e Spring.»*
   - *«David, me descreva uma API REST que você implementou.»*
   - *«Qual era o seu papel no projeto?»*
5. **Esperado**: turnos P:/R: no Assistente (ou erro de provedor legível — ainda conta como disparo).

### Se não disparar

| Sintoma | Ação |
|---------|------|
| Empty “Automático desligado” | Ligue o toggle |
| “Nenhum … pergunta elegível” | Use prefixo/imperativo da lista ou modo entrevista; confira Final (não partial) |
| Mismatch de sessão | Reiniciar agent com sessão ativa / copiar id do header STT |
| Só transcript no browser :8001 | Abra o **shell** |

### Testes automatizados (WSL)

```bash
cd apps/desktop-shell && npm test -- --run tests/assistant-auto.test.ts tests/assistant-prefs.test.ts tests/assistant-panel.test.ts
```

## Phase B — A/B modelo STT small vs medium

1. Baseline: `WHISPER_MODEL=small` no `.env`; recrie o container de transcription.
2. Fale **3 frases fixas** no remoto (grave o texto exato no dashboard):
   1. *Me descreva uma API REST com Java e Spring Boot.*
   2. *Qual era o seu papel no projeto na Claro?*
   3. *Como você versionou contratos e testes de segurança?*
3. Anote erros óbvios (trocas de palavras técnicas).
4. Mude para `WHISPER_MODEL=medium`; recrie container; confira health `model=medium`.
5. Repita as 3 frases; compare.
6. Rollback: `small` se latência/VRAM inaceitável.

Hotwords: edite `config/whisper-hotwords.txt` (Spring, REST, session-core, …) e reinicie STT.

## Phase C — Prosódia (quando implementado)

1. `PROSODY_ENABLED=true` no **serviço de transcrição** (não no agent Windows); health `prosodyEnabled: true`.
2. No shell: `useProsody` on; threshold default 0.65 (sem UI de limiar na v1).
3. Fale yes/no **sem** `?` no texto se o ASR omitir: *«Você já usou Kafka em produção»* com entonação de pergunta.
4. Esperado: se score ≥ threshold e origem system, dispara; se extrator off/falha, comportamento lexical inalterado.
5. NFR-002: budget de CPU documentado em `research.md` **ou** nota “unmeasured; default off remains”.

## Critérios de aceite manual (resumo)

- [ ] SC-005: operador sabe que resposta é no shell
- [ ] SC-001/002: pelo menos uma pergunta de entrevista gera turno Assistente
- [ ] SC-003: modo entrevista (se build incluir) só amplia system
- [ ] Phase B opcional mas documentada
- [ ] Phase C opcional; default prosody off não quebra feed
