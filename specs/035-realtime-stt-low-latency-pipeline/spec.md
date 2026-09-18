# Feature Specification: Realtime STT — pipeline de baixa latência

**Feature Branch**: feat/realtime-stt-low-latency-pipeline

**Created**: 2026-09-18

**Status**: Draft — aguardando Gate G1 (Spec)

**Input**: Evoluir o pipeline realtime atual para manter recepção de áudio contínua enquanto a inferência ocorre, controlar backlog por canal e reduzir a latência percebida sem perder ordenação, identidade de canal, finais de utterance ou confiabilidade de disconnect.

**Referências**:
- specs/001-streaming-foundation
- specs/024-issue-55-stt-final-utterance
- specs/034-stt-echo-metrics-disconnect
- ADR-0008 (supressão de eco)
- Constituição P5, P9 e P10

## Problema

O endpoint WebSocket de áudio processa cada janela sequencialmente e aguarda a inferência antes de voltar a receber novos frames. Essa decisão preserva ordenação e simplifica a finalização, porém faz a captura depender dos buffers de WebSocket/TCP durante picos de inferência e pode produzir atraso acumulado em calls longas.

O serviço também usa defaults orientados a qualidade, como beam size 5, que não são necessariamente adequados ao perfil realtime.

## User Scenarios & Testing

### User Story 1 - Transcrição permanece próxima da fala (Priority: P1)

Durante uma call, o usuário vê partials e finais com atraso baixo e estável, sem que o lag cresça continuamente ao longo da sessão.

**Independent Test**: usar engine fake com latência controlável e PCM sintético para provar que o receptor continua consumindo frames enquanto um único worker por canal preserva a ordem de inferência.

**Acceptance Scenarios**:

1. Given um canal recebendo áudio continuamente, When uma inferência demora mais que o intervalo entre frames, Then a tarefa receptora continua aceitando frames até o limite configurado da fila.
2. Given vários chunks do mesmo canal, When são processados, Then a ordem de inferência e emissão permanece igual à ordem de áudio.
3. Given a fila cheia, When chegam novos frames, Then o sistema aplica política explícita de backpressure e registra o evento; não cresce memória sem limite.
4. Given um disconnect, When ainda existe trabalho pendente, Then a política de finalização permanece determinística e não perde o final residual já exigido pela spec 034.

### User Story 2 - Perfil realtime privilegia latência (Priority: P1)

O operador pode executar STT com parâmetros apropriados para realtime sem alterar o comportamento do perfil de maior qualidade.

**Acceptance Scenarios**:

1. O perfil realtime usa beam size 1 por default, mantendo configuração sobrescrevível.
2. O perfil quality pode preservar beam size maior.
3. A escolha de perfil aparece no health/diagnóstico sem registrar conteúdo de áudio ou transcript.

### User Story 3 - Métricas distinguem inferência de lag (Priority: P1)

O operador consegue saber se o Whisper está rápido mas existe backlog, ou se a própria inferência está lenta.

**Acceptance Scenarios**:

1. Métricas por canal expõem inferenceMs, chunkAudioMs, rtf, queueDepth, queuedAudioMs e transcriptionLagMs.
2. RTF é calculado como tempo de inferência dividido pela duração do áudio processado.
3. transcriptionLagMs mede atraso ponta a ponta do áudio até o evento de transcript e não é substituído por inferenceMs.
4. Métricas não mudam a semântica de totalEvents e sampleCount já estabelecida na spec 034.

## Requirements

- **FR-001**: O serviço MUST desacoplar recepção de áudio e inferência por canal.
- **FR-002**: Cada canal MUST possuir no máximo um consumidor de inferência ativo, preservando ordem.
- **FR-003**: A fila de áudio/chunks MUST ser bounded e configurável.
- **FR-004**: O sistema MUST NOT criar paralelismo de múltiplas inferências concorrentes para o mesmo canal.
- **FR-005**: Disconnect MUST aguardar ou finalizar de forma controlada o trabalho necessário para produzir o final residual, sem regressão da spec 034.
- **FR-006**: O perfil realtime MUST permitir beam size 1 e parâmetros próprios de latência.
- **FR-007**: O modelo Whisper MUST permanecer residente; carregamento por chunk é proibido.
- **FR-008**: Métricas MUST incluir queueDepth, queuedAudioMs, inferenceMs, chunkAudioMs, rtf e transcriptionLagMs por canal.
- **FR-009**: Métricas MUST ser observáveis sem GPU real nos testes automatizados por engine fake.
- **FR-010**: sessionId, channelId, sourceType, label e device metadata MUST permanecer ponta a ponta.
- **FR-011**: O contrato transcript-event.v2 SHOULD permanecer compatível; qualquer campo novo MUST ser aditivo e opcional.
- **FR-012**: O hot path MUST NOT escrever áudio em arquivo temporário para inferência.
- **FR-013**: Falha de um canal MUST permanecer isolada dos demais.
- **FR-014**: Logs MUST NOT incluir PCM, tokens, transcript completo ou conteúdo sensível.

## Success Criteria

- **SC-001**: Em benchmark realtime no hardware de validação, RTF p95 do perfil alvo < 0,35.
- **SC-002**: transcriptionLagMs p95 < 2.000 ms em fluxo sustentado compatível com o modelo/hardware homologado.
- **SC-003**: Queue depth não apresenta crescimento monotônico durante sessão estável; após pausa suficiente retorna ao nível de repouso.
- **SC-004**: Zero reordenação de chunks em testes determinísticos com latência variável.
- **SC-005**: Zero perda do final de disconnect nos testes de regressão da spec 034.
- **SC-006**: Testes unitários e de integração desta feature executam sem GPU e sem WASAPI físico.

## Assumptions

- faster-whisper permanece o engine STT principal.
- O Windows audio agent atual continua enviando PCM16 mono 16 kHz.
- A separação system/microphone permanece.
- A spec 036 substituirá o chunking puramente temporal por chunking orientado à fala.

## Out of Scope

- VAD externo e chunking por fala, tratados na 036.
- Persistência consolidada e export, tratados na 037.
- Remoção de WSL/Docker, tratada na 038.
- Soak de longa duração como gate final, tratado na 039.
- Diarização, tratada opcionalmente na 040.
