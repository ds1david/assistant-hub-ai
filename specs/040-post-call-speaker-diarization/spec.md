# Feature Specification: Pós-call — diarização opcional de participantes remotos

**Feature Branch**: feat/post-call-speaker-diarization

**Created**: 2026-09-18

**Status**: Draft / Optional — aguardando decisão de produto e Gate G1

**Input**: Permitir identificação de múltiplos participantes no áudio remoto depois da call, sem adicionar custo ou latência ao pipeline realtime.

**Referências**:
- specs/037-durable-transcript-projection-export
- specs/039-realtime-reliability-soak
- Constituição P2, P5, P9 e P10

## Problema

No realtime, a separação system versus microphone já distingue o usuário local dos participantes remotos. Porém o canal system pode conter várias pessoas. Diarização pode enriquecer o transcript final, mas não é requisito para transcrição realtime e não deve competir por GPU durante a call.

Esta feature é deliberadamente pós-call e opcional.

## User Scenarios & Testing

### User Story 1 - Usuário escolhe diarizar após encerrar a call (Priority: P2)

1. Given sessão finalizada com gravação do canal system, When o usuário solicita diarização, Then o processamento ocorre fora do hot path realtime.
2. Given diarização indisponível ou falha, Then a transcrição original continua válida e exportável.

### User Story 2 - Microfone local não precisa de diarização (Priority: P2)

1. Segmentos sourceType microphone preservam o label local existente.
2. Apenas áudio system é submetido ao diarizador por default.
3. O resultado nunca mistura artificialmente system e microphone antes da persistência.

### User Story 3 - Usuário pode mapear speakers (Priority: P2)

1. Resultado inicial pode usar SPEAKER_00, SPEAKER_01 etc.
2. Usuário pode mapear identificadores para nomes amigáveis.
3. Reexportar transcript aplica os nomes mapeados sem alterar o event log bruto.

## Requirements

- **FR-001**: Diarização MUST ser opcional e desabilitada por default no realtime.
- **FR-002**: Diarização MUST executar somente após encerramento da sessão, salvo futura spec explícita.
- **FR-003**: O pipeline realtime MUST ter zero dependência de pyannote/WhisperX ou outro diarizador para funcionar.
- **FR-004**: O diarizador MUST entrar por interface/adaptador independente de fornecedor.
- **FR-005**: A entrada padrão MUST ser a gravação do canal system.
- **FR-006**: O resultado MUST produzir intervalos temporais com speakerId e confidence quando o engine fornecer.
- **FR-007**: A projeção de transcript MUST poder associar speakerId aos segmentos remotos sem reescrever o event log.
- **FR-008**: O usuário MUST poder mapear speakerId para displayName.
- **FR-009**: Reexecutar diarização MUST substituir/versionar apenas a projeção derivada, de forma idempotente.
- **FR-010**: Exportadores da 037 SHOULD incluir speaker labels quando disponíveis.
- **FR-011**: Falha de diarização MUST NOT bloquear consulta/export do transcript sem speakers.
- **FR-012**: Modelos gated/tokens externos MUST ser tratados por configuração segura; nenhum token em logs.
- **FR-013**: Testes automatizados MUST usar diarizador fake e fixtures sintéticas; validação de modelo real é manual conforme P10.
- **FR-014**: Esta feature MUST NOT alterar os SLAs realtime das specs 035/039.

## Key Entities

- DiarizationJob: processamento pós-call com status e versão.
- SpeakerTurn: intervalo start/end associado a speakerId.
- SpeakerIdentity: mapeamento opcional speakerId → displayName.
- DiarizedTranscriptProjection: visão derivada que combina transcript final e speaker turns.

## Success Criteria

- **SC-001**: Desabilitar/ausentar diarização não altera nenhum teste nem SLA do realtime.
- **SC-002**: Fixture com dois speakers remotos produz dois speakerIds distintos usando engine fake.
- **SC-003**: Segmentos de microphone permanecem atribuídos ao canal/local e não passam pelo diarizador por default.
- **SC-004**: Rerun do mesmo job não duplica speaker turns na projeção ativa.
- **SC-005**: Export com speaker mapping reflete nomes amigáveis; sem mapping usa speakerId estável.
- **SC-006**: Falha do job deixa transcript original íntegro e exportável.

## Assumptions

- Gravação do áudio system foi preservada pela sessão.
- A projeção final da 037 possui timestamps suficientes para correlação.
- A decisão sobre engine real fica para plan/research após benchmark de qualidade e custo.

## Out of Scope

- Diarização realtime.
- Voice biometrics/autenticação por voz.
- Reconhecimento permanente de pessoas entre sessões.
- Upload automático para serviço cloud.
- Alteração do áudio bruto.
