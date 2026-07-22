# Quickstart: validar eventos transcript v2 no session-core (SF-021)

## Pré-requisitos

- WSL: Java 21 e Maven via SDKMAN já ativos (`sdk current`).
- Nenhum hardware de áudio, GPU ou modelo STT real é necessário — a validação automatizada usa eventos sintéticos e um servidor WebSocket fake em memória (ver `research.md` #5-#6 e `data-model.md`).

## 1. Validação automatizada (WSL, sem hardware/GPU)

```bash
sdk current
mvn -pl services/session-core -am test
```

**Resultado esperado**: todos os testes do módulo passam, cobrindo (ver `spec.md` FR-001..FR-008 e `data-model.md`):

- `TranscriptContractTest`: fixtures de evento v2 (com e sem `device.endpointId`) validam contra `contracts/transcript-event.v2.schema.json`; uma fixture com campo obrigatório ausente é rejeitada (FR-004, SC-004).
- `TranscriptEventMapperTest`: um evento v2 mapeado para `HubEvent` preserva `channelId`/`sourceType`/`label`/`device` bit a bit em `correlation` (US1, SC-001); dois eventos de `channelId` diferentes na mesma sessão nunca se sobrescrevem (US2, SC-002).
- `TranscriptFeedClientIntegrationTest`: contra um servidor WebSocket fake que reproduz o formato de `/ws/transcripts`, um evento malformado ou de `sessionId` desconhecido/encerrado é descartado sem interromper a ingestão de outros eventos subsequentes (US3, SC-003); nenhuma chamada de controle é emitida de volta ao servidor fake (FR-005).

## 2. Verificação de consulta ponta a ponta

```bash
mvn -pl services/session-core -am spring-boot:run &
# criar sessão, publicar evento sintético via cliente WebSocket de teste apontando
# para o servidor fake local, então:
curl -s http://localhost:8080/api/sessions/<id>/events | jq '.[].correlation'
```

**Resultado esperado**: a resposta de `GET /api/sessions/{id}/events` (endpoint já existente, ver `contracts/README.md`) mostra `correlation.channelId`, `correlation.sourceType`, `correlation.label` e `correlation.device.*` idênticos aos do evento publicado.

## 3. Validação manual opcional com o `transcription-service` real (sem GPU)

Só necessária se quiser confirmar a integração fim a fim contra o serviço Python real (não é obrigatória para fechar a issue, que exige apenas testes automatizados — FR-007/SC-004).

1. Subir o `transcription-service` localmente com `WHISPER_DEVICE=cpu` e um modelo pequeno (`WHISPER_MODEL=tiny`), reaproveitando o padrão de `infra/compose/docker-compose.yml`.
2. Subir o `session-core` (`mvn -pl services/session-core -am spring-boot:run`) com a propriedade `session-core.transcript-ingestion.feed-url=ws://localhost:8001/ws/transcripts` (`TranscriptIngestionProperties`, ver `plan.md`).
3. Criar uma sessão via `POST /api/sessions` e anotar o `id` retornado.
4. Abrir um canal de áudio sintético no `transcription-service` usando o mesmo padrão de `services/transcription-service/tests/test_ws_audio_contract.py` (PCM senoidal, `sourceType=microphone`), usando o `id` da sessão como `session_id` no path (`/ws/audio/{session_id}/{channel_id}`).
5. Consultar `GET /api/sessions/{id}/events` no `session-core` e confirmar que o evento aparece com `correlation` preenchido.
6. Registrar o resultado em `docs/validation/` apenas se a validação revelar algo que os testes automatizados não cobriam (constituição P10).

## Referências

- Requisitos completos: `spec.md` (FR-001..FR-008, SC-001..SC-005).
- Entidades e mapeamento: `data-model.md`.
- Decisões técnicas e alternativas rejeitadas: `research.md`.
- Interface consumida e delta de contrato: `contracts/README.md`.
