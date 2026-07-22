# Quickstart: validar Memory Hub — persistência local de sessão e eventos (R3)

Guia de validação end-to-end, sem GPU e sem hardware de áudio (P10/FR-008). Todos os comandos rodam no WSL, no módulo `services/session-core`. Referências de schema: [data-model.md](./data-model.md); decisões de arquitetura: [research.md](./research.md).

## Pré-requisitos

- Ambiente WSL com Java 21 e Maven já configurados via SDKMAN (`sdk current`).
- Módulo `services/session-core` compilando na branch `013-issue-29-memory-hub-persistence`.
- Nenhuma dependência de rede, GPU ou dispositivo de áudio real.

## 1. Rodar a suíte de testes automatizados da feature

```bash
mvn -pl services/session-core -am test
```

**Esperado**: todos os testes de `ai.assistanthub.core.memory` passam, incluindo:

- `SessionPersistenceStoreTest` (US1) — grava sessão + eventos, "reabre" o mesmo arquivo SQLite (`@TempDir`) simulando restart gracioso, confirma que sessão e eventos voltam idênticos.
- `SessionPersistenceCrashSafetyTest` (US1, edge case) — interrompe a gravação de um evento antes do commit e confirma que os eventos já commitados anteriormente continuam intactos e consultáveis.
- `SessionPersistenceAppendOrderTest` (US2) — retoma uma sessão já persistida, envia novos eventos (canal existente + canal novo) e confirma ordem cronológica e separação por canal preservadas.
- `RetentionPolicyTest` (US3) — configura um limite de retenção baixo, grava sessões `ENDED` além do limite, confirma expurgo das mais antigas sem afetar sessões ativas nem falhar novas gravações.
- Suíte já existente de `specs/007-sf-021-session-core-events/` (`TranscriptContractTest`, `TranscriptFeedClient*Test`) continua verde, confirmando que o contrato `transcript-event.v2` e o comportamento de ingestão não regrediram (FR-007/FR-010).

## 2. Validação manual de restart gracioso (opcional, end-to-end)

```bash
# Sobe o serviço com um caminho de banco de teste isolado
SESSION_CORE_MEMORY_HUB_PATH=/tmp/memory-hub-quickstart.db \
  mvn -pl services/session-core spring-boot:run &

# Cria uma sessão e anexa um evento via API já existente do session-core (SessionController)
curl -s -X POST http://localhost:8080/api/sessions -H 'Content-Type: application/json' \
  -d '{"title":"quickstart","profileId":"demo","metadata":{}}'

# Anote o "id" da sessão retornada, então anexe um evento sintético
curl -s -X POST http://localhost:8080/api/sessions/<id-anotado>/events -H 'Content-Type: application/json' \
  -d '{"type":"transcript.final.v2","source":"quickstart","payload":{"text":"ola"}}'

# Encerra o processo (Ctrl+C ou kill) e sobe de novo com o MESMO caminho de banco
SESSION_CORE_MEMORY_HUB_PATH=/tmp/memory-hub-quickstart.db \
  mvn -pl services/session-core spring-boot:run &

curl -s http://localhost:8080/api/sessions/<id-anotado>
curl -s http://localhost:8080/api/sessions/<id-anotado>/events
```

**Esperado**: a sessão e o evento gravados antes do restart continuam retornando exatamente com os mesmos campos (`channelId`, `sourceType`, `label`, `device`, texto), confirmando SC-001.

## 3. Confirmar que nada sensível é versionado

```bash
git status --porcelain -- data/session-core 2>/dev/null
cat .gitignore | grep -i memory-hub
```

**Esperado**: nenhum arquivo `.db` aparece como rastreável pelo Git; a entrada de `.gitignore` para o caminho padrão do Memory Hub existe (P9).

## 4. Confirmar ausência de dependência de GPU/hardware

```bash
grep -ril "cuda\|gpu\|wasapi" services/session-core/src/test/java/ai/assistanthub/core/memory/ || echo "OK: nenhuma referência"
```

**Esperado**: `OK: nenhuma referência` — confirma SC-005/P10.

## Critérios de sucesso mapeados

| Critério | Como este quickstart valida |
|---|---|
| SC-001 (sessão/eventos idênticos após restart) | Passo 1 (`SessionPersistenceStoreTest`) e Passo 2 (manual) |
| SC-002 (política de retenção documentada e localizável) | `data-model.md` + `research.md` (Decisão 5) descrevem a política sem exigir leitura do código |
| SC-003 (zero perda em crash) | Passo 1 (`SessionPersistenceCrashSafetyTest`) |
| SC-004 (contrato v2 inalterado) | Passo 1 (suíte existente de `specs/007-sf-021-session-core-events/` continua verde) |
| SC-005 (sem GPU/hardware) | Passo 1 (suíte inteira) e Passo 4 |
