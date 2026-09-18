# Feature Specification: Realtime STT — Speech-Aware Chunking e VAD

**Feature Branch**: feat/speech-aware-chunking-vad

**Created**: 2026-09-18

**Status**: Draft — aguardando Gate G1 (Spec)

**Input**: Evitar inferência de silêncio e substituir a janela fixa como principal mecanismo de segmentação por uma máquina de estado orientada a fala, mantendo partials frequentes e finais naturais.

**Referências**:
- specs/035-realtime-stt-low-latency-pipeline
- specs/024-issue-55-stt-final-utterance
- specs/034-stt-echo-metrics-disconnect
- Constituição P2, P5, P9 e P10

## Problema

Hoje o StreamingTranscriber acumula uma janela temporal fixa e só então chama faster-whisper, cujo VAD interno decide o que aproveitar. Mesmo quando há silêncio, o pipeline ainda monta janelas e entra no engine STT. Além disso, overlap fixo reprocessa parte do áudio em todas as janelas.

Para calls longas, o chunking deve reagir à fala: abrir um trecho quando a fala começa, fechá-lo após silêncio suficiente e produzir partials intermediários quando o interlocutor fala continuamente.

## User Scenarios & Testing

### User Story 1 - Silêncio não consome inferência (Priority: P1)

**Independent Test**: alimentar frames sintéticos de silêncio e fala em um VAD fake/determinístico e contar chamadas ao engine STT.

**Acceptance Scenarios**:

1. Given somente silêncio, When o pipeline recebe frames, Then zero chamadas ao STT são feitas.
2. Given fala após silêncio, When o VAD sinaliza início, Then o chunk builder preserva pre-roll configurável para não cortar fonemas iniciais.
3. Given fala seguida de silêncio suficiente, Then o chunk é fechado e enviado ao STT.

### User Story 2 - Monólogos geram partials sem esperar o fim da fala (Priority: P1)

1. Given fala contínua maior que maxChunkDuration, When o limite é atingido, Then um chunk parcial é emitido e a captura continua.
2. Given fala contínua por vários limites, Then chunks permanecem ordenados e usam overlap/pre-roll mínimo configurável sem duplicação ilimitada.
3. Given fim natural da utterance, Then o evento final representa o texto estabilizado daquela utterance.

### User Story 3 - VAD pode evoluir sem acoplar o core (Priority: P2)

1. A aplicação usa uma abstração de VoiceActivityDetector.
2. Silero VAD ou implementação equivalente pode ser adaptador inicial.
3. Testes usam detector fake, sem baixar modelo ou depender de GPU.

## Requirements

- **FR-001**: O pipeline MUST executar VAD antes de chamar o engine STT.
- **FR-002**: Frames classificados como silêncio MUST NOT provocar inferência STT.
- **FR-003**: O VAD MUST operar incrementalmente sobre frames, sem exigir arquivo de áudio.
- **FR-004**: O chunk builder MUST possuir estados equivalentes a idle, speech-open e flushing/finalizing.
- **FR-005**: O início de fala MUST suportar pre-roll configurável.
- **FR-006**: O fim de fala MUST usar trailing silence configurável.
- **FR-007**: Fala contínua MUST gerar chunks intermediários por maxChunkDuration configurável.
- **FR-008**: O overlap entre chunks MUST ser configurável e menor que no pipeline fixo atual por default.
- **FR-009**: Valores iniciais recomendados para validação: trailing silence em torno de 500 ms, max chunk em torno de 2 s, pre-roll/overlap em torno de 200 ms; o plan pode ajustar após benchmark.
- **FR-010**: O VAD interno do faster-whisper MAY permanecer como segunda barreira, mas MUST NOT ser a única decisão de silêncio do pipeline realtime.
- **FR-011**: O pipeline MUST preservar sourceType e identidade do canal.
- **FR-012**: Supressão de eco continua após STT; esta feature não introduz AEC acústico.
- **FR-013**: O finalizer existente MUST continuar emitindo no máximo um final por utterance.
- **FR-014**: Métricas MUST registrar speechMs, silenceRejectedMs, chunksCreated e STT calls por canal.
- **FR-015**: Testes MUST ser determinísticos sem GPU/hardware.

## Success Criteria

- **SC-001**: Áudio 100% silencioso produz zero chamadas ao engine STT em teste determinístico.
- **SC-002**: Em fixture com 60% de silêncio, o total de áudio enviado ao STT é materialmente menor que a duração bruta e silenceRejectedMs corresponde ao áudio descartado pelo VAD.
- **SC-003**: Em fala contínua, o primeiro partial é elegível para emissão em até maxChunkDuration + tempo de inferência, sem esperar o fim da utterance.
- **SC-004**: Nenhum chunk excede o limite máximo configurado, salvo tolerância de um frame.
- **SC-005**: Zero finais duplicados nos testes de idle, max-open e disconnect.
- **SC-006**: Suite sem GPU/hardware permanece verde.

## Assumptions

- A fila por canal e métricas de backlog da 035 estão disponíveis.
- O sample rate canônico continua 16 kHz mono PCM16.
- O objetivo é eficiência e latência; alignment por palavra não entra no hot path.

## Out of Scope

- Diarização.
- AEC acústico nativo.
- Persistência/export.
- Runtime Windows nativo do STT.
- Alteração da semântica dos canais system e microphone.
