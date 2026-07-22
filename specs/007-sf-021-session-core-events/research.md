# Phase 0 Research: Publicar eventos transcript v2 no session-core (SF-021)

Nenhum item de Technical Context ficou como `NEEDS CLARIFICATION` — todas as decisões abaixo foram resolvidas por inspeção direta do código já existente (`services/transcription-service`, `services/session-core`, `packages/plugin-sdk-java`) e dos contratos versionados (`contracts/transcript-event.v2.schema.json`).

## 1. Transporte de consumo do evento v2

- **Decision**: cliente WebSocket dentro do `session-core` (via `spring-boot-starter-websocket`, `StandardWebSocketClient`) conectando ao feed já existente `/ws/transcripts` do `transcription-service`.
- **Rationale**: o endpoint já existe (`services/transcription-service/app/main.py:81`) e já emite todo evento v2 publicado (`TranscriptBroadcaster.publish`, `services/transcription-service/app/broadcast.py`); nenhuma mudança é necessária do lado Python, o que respeita a fronteira da issue ("transcription publica / session-core consome") e o princípio P4 (contrato inalterado).
- **Alternatives considered**:
  - Novo endpoint WebSocket dedicado por sessão no `transcription-service` — rejeitado: exigiria mudança em um serviço fora do escopo desta issue, e o feed global já carrega tudo que é necessário (todo evento já inclui `sessionId`/`channelId`).
  - Polling de um endpoint REST — rejeitado: não existe hoje, e adicionaria latência e um estado de "última posição lida" desnecessário quando o evento já é empurrado.
  - Broker de mensagens (Kafka/RabbitMQ) — rejeitado por desproporcional: dois serviços na mesma rede, sem essa infraestrutura hoje no repositório.

## 2. Demultiplexação por sessão em um feed global

- **Decision**: o consumidor do `session-core` lê todo evento do feed compartilhado e resolve a sessão pelo `sessionId` do próprio evento; eventos de sessão desconhecida/encerrada são descartados (FR-004).
- **Rationale**: `TranscriptBroadcaster.publish` faz fan-out para **todos** os clientes conectados — não há escopo por sessão no lado do publisher. A demultiplexação só pode acontecer no consumidor.
- **Alternatives considered**: pedir ao `transcription-service` para filtrar por sessão via query param na conexão — rejeitado: mudaria o protocolo do `/ws/transcripts` publicado, fora da fronteira desta issue (que não pede mudança no lado que publica).

## 3. Correlação entre `sessionId` (string, transcription-service) e `ConversationSession.id` (UUID, session-core)

- **Decision**: tratar ambos como strings opacas para fins de correspondência — comparar `event.sessionId` com `ConversationSession.id().toString()`, sem impor um formato além de igualdade de string.
- **Rationale**: em `services/transcription-service/app/main.py`, `session_id` é um parâmetro de path livre (`/ws/audio/{session_id}/{channel_id}`); em `session-core`, `ConversationSession.id` é um `UUID`. Quem inicia a captura (o agente de áudio) é responsável por usar o mesmo valor (o UUID da sessão do session-core) como `session_id` ao abrir o canal no transcription-service — isso é uma questão operacional de como a sessão é iniciada ponta a ponta, não uma mudança de formato de dado que esta feature precise resolver.
- **Alternatives considered**: tabela de mapeamento entre um `session_id` arbitrário e o UUID do session-core — rejeitado por complexidade desnecessária; nada no código hoje sugere que os dois precisem ser valores diferentes, e uma tabela de mapeamento introduziria uma persistência fora do escopo (ver spec Assumptions).

## 4. Como representar `channelId`/`sourceType`/`label`/`device` dentro do `HubEvent` já existente

- **Decision**: mapear os campos do evento v2 para `HubEvent` (`packages/plugin-sdk-java/src/main/java/ai/assistanthub/sdk/HubEvent.java`) assim:
  - `type` = `type` do evento (`transcript.partial.v2` / `transcript.final.v2`)
  - `source` = `"transcription-service"`
  - `occurredAt` = `occurredAt` do evento
  - `payload` = `{text, language, languageProbability, latencyMs, audioSeconds, droppedWindows}`
  - `correlation` = `{channelId, sourceType, label, "device.index", "device.name", "device.endpointId"}` (valores convertidos para string; `null` vira ausência de chave ou string vazia — decisão de implementação, não de contrato)
- **Rationale**: `HubEvent` já tem um campo `correlation: Map<String,String>` que parece desenhado exatamente para esse tipo de marcação de canal/dispositivo. Reaproveitá-lo evita ampliar um contrato de SDK compartilhado por outros plugins (P4), e mantém `payload` só para o conteúdo da transcrição.
- **Alternatives considered**: estender `HubEvent` com campos próprios (`channelId`, `device`) — rejeitado para esta feature: seria uma mudança ampla em um record compartilhado por outros consumidores do SDK; reaproveitar `correlation`/`payload` já satisfaz FR-002/FR-003 sem tocar no contrato compartilhado. Pode ser revisitado se uma feature futura precisar de campos tipados/consultáveis por canal.

## 5. Validação de contrato nos testes Java

- **Decision**: adicionar `networknt:json-schema-validator` (Apache-2.0) ao escopo de teste do `session-core`, validando fixtures sintéticas contra o mesmo arquivo `contracts/transcript-event.v2.schema.json` já validado no lado Python (`services/transcription-service/tests/test_ws_audio_contract.py`, que usa `jsonschema`/`Draft202012Validator`).
- **Rationale**: mantém o contrato com fonte única (P4); usa validação real de schema em vez de asserts campo a campo que podem divergir do arquivo com o tempo.
- **Alternatives considered**: asserts manuais campo a campo — rejeitado por não detectar automaticamente mudanças futuras no schema.

## 6. Comportamento de rejeição/log para evento malformado ou de sessão desconhecida (FR-004)

- **Decision**: eventos inválidos contra o schema e eventos de sessão desconhecida/encerrada são logados em nível WARN com `type`/`channelId`/`sessionId` (sem necessidade do texto completo transcrito no log de rejeição) e descartados; nenhuma exceção pode propagar e interromper o loop de leitura do WebSocket.
- **Rationale**: um loop de leitura quebrado derrubaria a ingestão de **todas** as sessões por causa de um único evento problemático — exatamente o que a issue quer evitar ao dizer que o `session-core` não pode virar (nem depender de) um orquestrador frágil.
- **Alternatives considered**: desconectar/reconectar a cada evento inválido — rejeitado: causaria lacunas de ingestão para todas as sessões por causa de um problema isolado em outra sessão.

## 7. Reconexão do cliente WebSocket

- **Decision**: ao desconectar, o cliente tenta novamente com backoff limitado, sem falhar a inicialização do `session-core`.
- **Rationale**: o `transcription-service` pode reiniciar de forma independente; uma dependência rígida na inicialização violaria a fronteira "apenas consumidor" e reduziria a disponibilidade do `session-core` para suas outras funções (API de sessão).
- **Alternatives considered**: falhar rápido na perda de conexão — rejeitado: derrubaria funcionalidades de sessão sem relação alguma só porque o serviço de transcrição está momentaneamente indisponível.
