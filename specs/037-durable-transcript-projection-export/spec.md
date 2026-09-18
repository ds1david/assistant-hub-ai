# Feature Specification: Transcript durável — projeção, recuperação e exportação

**Feature Branch**: feat/durable-transcript-projection-export

**Created**: 2026-09-18

**Status**: Draft — aguardando Gate G1 (Spec)

**Input**: Transformar o event stream realtime já persistido em uma transcrição canônica por sessão, continuamente recuperável e exportável, sem perder o histórico de eventos partial/final.

**Referências**:
- specs/001-streaming-foundation
- specs/024-issue-55-stt-final-utterance
- specs/034-stt-echo-metrics-disconnect
- specs/035-realtime-stt-low-latency-pipeline
- SessionPersistenceStore / SessionRepository existentes
- Constituição P4, P5, P9 e P10

## Problema

O session-core já persiste HubEvent em SQLite, mas event log e documento final são conceitos diferentes. Uma utterance pode gerar vários partials e um final. Para salvar e exportar uma call, o produto precisa de uma projeção estável em que os partials atualizam um segmento aberto e o final o consolida.

O event log deve permanecer auditável; a projeção é derivada e reconstruível.

## User Scenarios & Testing

### User Story 1 - Call fica salva mesmo se o processo parar (Priority: P1)

1. Given vários finais já persistidos, When o desktop ou STT encerra inesperadamente, Then após reinício a sessão recupera todos os segmentos finais já confirmados.
2. Given um partial ainda aberto no momento da queda, Then ele não é promovido silenciosamente a final; a política de recovery decide explicitamente se o mantém como draft ou o descarta da exportação final.

### User Story 2 - Partial não duplica a transcrição final (Priority: P1)

1. Given partial A, partial AB e final ABC do mesmo canal/utterance, Then a projeção final contém um único segmento ABC.
2. Given canais system e microphone, Then segmentos permanecem separados por origem e ordenados cronologicamente.
3. Given sessão reidratada, Then a projeção reconstruída é idempotente.

### User Story 3 - Usuário exporta a call (Priority: P1)

A sessão pode ser exportada em formatos de uso humano e máquina.

**Acceptance Scenarios**:

1. Export TXT contém transcript cronológico legível.
2. Export Markdown preserva timestamp, origem/canal e texto.
3. Export JSON preserva metadados estruturados.
4. Export VTT e SRT usam apenas segmentos finais com timestamps válidos.
5. Reexportar a mesma sessão sem novas mudanças produz conteúdo semanticamente equivalente.

## Requirements

- **FR-001**: O HubEvent persistido MUST continuar sendo a fonte auditável imutável.
- **FR-002**: O sistema MUST manter uma projeção de transcript por sessão e canal.
- **FR-003**: Cada canal MUST possuir no máximo um segmento de utterance aberto por vez.
- **FR-004**: Evento partial MUST criar ou atualizar o segmento aberto; MUST NOT criar uma linha final adicional a cada revisão.
- **FR-005**: Evento final MUST consolidar o segmento aberto correspondente.
- **FR-006**: A projeção MUST preservar sessionId, channelId, sourceType, label, occurredAt e texto final.
- **FR-007**: A projeção MUST ser persistida em SQLite ou reconstruível deterministicamente do event log; a decisão exata fica para o plan.
- **FR-008**: Startup MUST reidratar a projeção sem duplicar segmentos.
- **FR-009**: O sistema MUST expor consulta da transcrição consolidada por sessão.
- **FR-010**: O sistema MUST exportar TXT, Markdown, JSON, VTT e SRT.
- **FR-011**: Export final MUST usar somente segmentos finalizados, salvo opção explícita de incluir drafts.
- **FR-012**: Falha de export MUST NOT corromper a projeção persistida.
- **FR-013**: Arquivos de export SHOULD ser gerados atomicamente via arquivo temporário + rename ou mecanismo equivalente.
- **FR-014**: Dados sensíveis não entram em logs de export.
- **FR-015**: Testes de projeção e export MUST rodar sem GPU/hardware.
- **FR-016**: A feature SHOULD evitar alteração incompatível de transcript-event.v2; caso seja necessário identificador de utterance, ele MUST ser aditivo/opcional e seguir P4.

## Key Entities

- TranscriptProjection: visão consolidada por sessão.
- TranscriptSegment: trecho aberto ou final, associado a canal/origem.
- TranscriptExport: representação materializada em um formato.
- ProjectionCheckpoint: opcional, para reidratação incremental.

## Success Criteria

- **SC-001**: Sequência partial → partial → final resulta em exatamente um segmento final.
- **SC-002**: Reprocessar o mesmo conjunto de eventos duas vezes produz a mesma projeção sem duplicatas.
- **SC-003**: Reinício do session-core preserva 100% dos finais já persistidos em testes de recovery.
- **SC-004**: Exportadores TXT/MD/JSON/VTT/SRT passam golden tests determinísticos.
- **SC-005**: Sessão com system + microphone mantém ordem temporal e identidade de canal em 100% dos testes.
- **SC-006**: Um crash simulado durante export não altera o estado persistido da sessão.

## Assumptions

- Session-core permanece responsável por sessão, memória e SQLite.
- O transcription-service continua publicando partial/final.
- Gravação de áudio é paralela e não precisa ser embutida no SQLite.

## Out of Scope

- Diarização de participantes remotos.
- Resumo por LLM.
- Edição colaborativa do transcript.
- Sincronização em nuvem.
- Formatos DOCX/PDF nesta feature.
