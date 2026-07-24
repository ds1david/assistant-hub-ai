# Quickstart: validar Desktop Tauri — shell local do Assistant Hub (R5)

Guia de validação end-to-end. Passos 1–2 rodam com um `session-core` real (WSL, sem GPU/hardware de áudio, P10) e um agent Windows **fake** — não é necessário microfone/áudio de sistema real para validar o shell. O passo 3 é a única validação que exige de fato a máquina Windows de referência com o shell empacotado (SC-004). Referências: [data-model.md](./data-model.md) (formato das views), [research.md](./research.md) (decisões de transporte/detecção).

## Pré-requisitos

- WSL com Java 21/Maven via SDKMAN (`sdk current`) para rodar o `session-core`.
- Máquina/VM Windows 10/11 de referência com WebView2, Rust e Node instalados, para build/execução do shell (`apps/desktop-shell/`) — ver "Onde roda o build" em `research.md`.
- Nenhuma dependência de GPU ou hardware de áudio físico para os testes automatizados (P10/SC-006).

## 1. Subir o session-core e gerar dados sintéticos de sessão/canais

```bash
mvn -pl services/session-core spring-boot:run &

curl -s -X POST http://localhost:8080/api/sessions -H 'Content-Type: application/json' \
  -d '{"title":"quickstart-desktop-shell","profileId":"demo","metadata":{}}'
# anote o "id" retornado

# Nota: POST /api/sessions/{id}/events (AppendEventRequest) só aceita type/source/payload —
# não é possível definir channelId/sourceType/label por esse endpoint (um "correlation" no
# corpo é silenciosamente ignorado). Correlation real só é populada pelo caminho de produção
# (TranscriptFeedClient/TranscriptEventMapper, consumindo /ws/transcripts do transcription-service).
# Por isso este passo valida apenas FR-001/FR-009 (status de sessão e conectividade); a validação
# de agrupamento por canal (FR-002/FR-004/SC-002) é feita pelos fixtures automatizados do Passo 2
# (session_core_client_tests.rs / transcript-feed.test.ts), que reproduzem o formato real de
# HubEvent.correlation produzido por TranscriptEventMapper — e, de ponta a ponta, pela validação
# manual do Passo 3 contra um transcription-service real ou publicador WS de teste.

curl -s http://localhost:8080/actuator/health
```

**Esperado**: `POST /api/sessions` retorna a sessão criada; `GET /actuator/health` retorna `{"status":"UP"}` — validação de canal fica a cargo dos Passos 2 e 3.

## 2. Rodar a suíte automatizada do shell (sem hardware real)

```bash
# Rust — camada de comandos Tauri, contra um servidor HTTP fake local e um executável fake do agent
cargo test --manifest-path apps/desktop-shell/src-tauri/Cargo.toml

# Frontend — lógica de agrupamento/ordenação do feed
npm --prefix apps/desktop-shell test
```

**Esperado**: todos os testes passam, incluindo:

- `session_core_client_tests` (US1/US2) — aponta o cliente HTTP interno para um servidor fake que devolve as mesmas formas de `ConversationSession`/`HubEvent` do passo 1, confirma que `SessionStatusView`/`ChannelStatusView`/`TranscriptFeedEntry` (ver `data-model.md`) preservam `channelId`/`sourceType`/`label` sem misturar canais (SC-002); confirma também que uma falha de `GET /actuator/health` reflete estado `disconnected`/`error`, não dado obsoleto (FR-009).
- `agent_control_tests` (US3) — usa um executável fake no lugar de `assistant-hub-audio`: confirma detecção de "parado" → ação disponível (FR-006/FR-007), start direto bem-sucedido, e que uma falha de start propaga uma mensagem específica, não genérica (FR-008).
- `transcript-feed.test.ts` (US2) — ordena entradas sintéticas fora de ordem por `occurredAt` e confirma saída cronológica correta, sem combinar texto de `mic-1` e `sys-1` na mesma entrada (FR-004).

## 3. Validação manual no Windows de referência (obrigatória para SC-004, não automatizável)

1. Seguir apenas `docs/desktop-shell/packaging.md` (FR-011) para empacotar/instalar o shell na máquina Windows de referência, do zero.
2. Gerar atividade real com metadados de canal para a sessão `quickstart-desktop-shell` do passo 1 — como o passo 1 (curl direto) não consegue definir `channelId`/`sourceType`/`label` (ver nota do Passo 1), use o `windows-audio-agent` real (`assistant-hub-audio run --session <id> --profile <perfil>`) apontando para um `transcription-service` real, ou um publicador WS de teste que emita mensagens `transcript-event.v2` válidas para `session-core.transcript-ingestion.feed-url`, cobrindo ao menos dois canais (ex.: `mic-1`/`microphone` e `sys-1`/`system_audio`).
3. Com o `session-core` acessível pela máquina Windows (`sessionCoreBaseUrl` configurado), abrir o shell e confirmar visualmente:
   - a sessão `quickstart-desktop-shell` aparece com status correto (US1);
   - os canais gerados no passo 3.2 aparecem distintos, com `label` correto (US1);
   - os textos de transcript aparecem no feed, identificados por canal, na ordem de chegada (US2);
   - com o agent Windows real parado, o shell mostra "parado" e uma ação/instrução clara; iniciando pelo shell (ou manualmente, conforme a instrução exibida), o status muda para "ativo" (US3).
4. Fechar a janela do shell e confirmar que o processo do `session-core` (e o do agent, se estava rodando) **não** foi encerrado junto (edge case da spec).
5. Registrar o resultado em `docs/validation/` (ambiente, commit, passos, resultado), conforme P10.

**Esperado**: todos os itens do passo 3.3 conferem visualmente; nenhum processo auxiliar é morto ao fechar o shell (passo 3.4); evidência registrada (passo 3.5).

## 4. Confirmar que o modo Developer não regride

```bash
mvn -pl services/session-core -am test
PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests
```

**Esperado**: as suítes já existentes continuam verdes — introduzir o shell não altera `session-core` nem `transcription-service` (SC-005/FR-012).

## Critérios de sucesso mapeados

| Critério | Como este quickstart valida |
|---|---|
| SC-001 (status sem CLI em <10s) | Passo 3.3, primeiro item (validação manual visual) |
| SC-002 (feed preserva channelId/sourceType/label) | Passo 2 (`session_core_client_tests`, `transcript-feed.test.ts`) e Passo 3.3 |
| SC-003 (ação clara sobre o agent, sem doc externa) | Passo 2 (`agent_control_tests`) e Passo 3.3, último item |
| SC-004 (build reproduzível na máquina de referência) | Passo 3.1 |
| SC-005 (modo Developer sem regressão) | Passo 4 |
| SC-006 (testes automatizados sem GPU/hardware) | Passo 2 inteiro (servidor/agent fake, nenhum dispositivo real) |
