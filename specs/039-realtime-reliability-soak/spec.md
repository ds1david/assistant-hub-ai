# Feature Specification: Realtime STT — reliability, recovery e soak

**Feature Branch**: test/realtime-reliability-soak

**Created**: 2026-09-18

**Status**: Draft — aguardando Gate G1 (Spec)

**Input**: Transformar o pipeline realtime em uma capacidade confiável para calls longas, validando estabilidade de fila, memória, VRAM, persistência, reconnect e finalização.

**Referências**:
- specs/034-stt-echo-metrics-disconnect
- specs/035-realtime-stt-low-latency-pipeline
- specs/036-speech-aware-chunking-vad
- specs/037-durable-transcript-projection-export
- specs/038-native-windows-runtime
- Constituição P9 e P10

## Problema

Baixa latência em testes curtos não garante uma call estável de uma ou duas horas. O produto precisa provar que lag, filas, memória, VRAM e contadores não degradam com o tempo, e que falhas operacionais não apagam transcript já confirmado.

## User Scenarios & Testing

### User Story 1 - Call longa não acumula atraso (Priority: P1)

1. Given sessão longa com fala e silêncio, Then queue depth e transcription lag permanecem estáveis.
2. Given períodos de pausa, Then backlog retorna ao estado de repouso.
3. Given duas horas de execução, Then o serviço não apresenta crescimento de memória/VRAM compatível com leak.

### User Story 2 - Falhas comuns são recuperáveis (Priority: P1)

1. STT reiniciado durante a call: agente reconecta e novos trechos voltam a ser processados.
2. Endpoint de áudio removido e recolocado: política existente de hotplug é respeitada.
3. session-core reiniciado: transcript já persistido é reidratado; novos eventos voltam a ser persistidos após reconexão.
4. Desktop encerrado de forma controlada: finais pendentes e SQLite são concluídos dentro do timeout de shutdown.

### User Story 3 - Evidência de validação é reproduzível (Priority: P2)

Toda validação real Windows/GPU gera documento com commit, hardware, versões, duração, métricas e resultado.

## Requirements

- **FR-001**: MUST existir suíte de stress determinística sem GPU/hardware usando fake STT e PCM sintético.
- **FR-002**: MUST existir roteiro de soak real Windows/GPU conforme P10.
- **FR-003**: O gate mínimo real MUST incluir execuções de 30 min, 1 h e 2 h; 4 h é recomendado antes de release estável.
- **FR-004**: O soak MUST registrar RTF, inferenceMs, transcriptionLagMs, queueDepth, queuedAudioMs, dropped frames/windows, RSS, CPU, GPU e VRAM quando disponíveis.
- **FR-005**: O sistema MUST preservar finais confirmados já persistidos após restart do STT ou session-core.
- **FR-006**: Reconnect MUST NOT duplicar indiscriminadamente segmentos finais já consolidados.
- **FR-007**: O teste MUST incluir ao menos system + microphone simultâneos.
- **FR-008**: O teste MUST incluir períodos prolongados de silêncio para validar VAD e recuperação de filas.
- **FR-009**: O teste MUST incluir fala contínua para validar max chunk e backlog.
- **FR-010**: O teste MUST incluir disconnect/teardown para regressão da spec 034.
- **FR-011**: Logs/evidências MUST NOT conter áudio bruto, tokens ou transcript sensível real; usar conteúdo sintético quando possível.
- **FR-012**: Falhas encontradas no soak que violem critérios MUST bloquear o gate de release até resolução ou waiver humano documentado.

## Success Criteria

- **SC-001**: Em host homologado, RTF p95 < 0,35 durante o período medido após warm-up.
- **SC-002**: transcriptionLagMs p95 < 2.000 ms e não apresenta tendência monotônica crescente durante steady state.
- **SC-003**: Zero dropped audio frames atribuíveis ao pipeline da aplicação no soak homologado.
- **SC-004**: Após pausas de fala, queueDepth retorna ao nível de repouso em tempo compatível com o backlog acumulado e não cresce sessão após sessão.
- **SC-005**: RSS após warm-up não cresce mais que 25% entre a marca de 15 min e o final do soak de 2 h, salvo justificativa documentada.
- **SC-006**: VRAM após warm-up não apresenta drift superior a 512 MiB no soak de 2 h, salvo cache explicitamente identificado e estabilizado.
- **SC-007**: Zero perda de transcript final já persistido em cenários de restart testados.
- **SC-008**: Zero final duplicado por reconnect/teardown nos cenários determinísticos.
- **SC-009**: Stress CI de multi-canal passa repetidamente sem race de métricas/finalização.
- **SC-010**: Cada validação real publica docs/validation com ambiente, commit, comandos, duração e resultados.

## Assumptions

- Specs 035–038 estão implementadas ou suficientemente estáveis para medição.
- Critérios de performance são para hardware homologado e podem originar perfis distintos por capacidade.
- O objetivo é estabilidade local; não inclui HA distribuída.

## Out of Scope

- Benchmark competitivo contra serviços cloud.
- Clusterização do STT.
- Failover entre máquinas.
- Diarização.
