# Feature Specification: Janela adaptativa de áudio com base em métricas (SF-022)

**Feature Branch**: `feature/sf-022-sf-022-janela-adaptativa-de-udio-com-base-em-m-t`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Issue #17 — Ajustar a janela de captura/segmentação usando métricas de latência (SF-016) sem quebrar o contrato transcript-event.v2. Política de ajuste baseada em p50/p95, limites seguros (min/max) e histerese para evitar oscilação, isolamento por sessão/canal, testes sem GPU/hardware, observabilidade do ajuste aplicado."

**Referências**: Issue #17 · Umbrella `specs/001-streaming-foundation/` (item SF-022) · Depende da SF-016 (métricas de latência p50/p95 por sessão/canal, ver `docs/validation/sf-016-latency-metrics.md` e `services/transcription-service/app/metrics.py`) · Contrato `contracts/transcript-event.v2.schema.json` (permanece inalterado) · Janela atual de captura/segmentação: `whisper_window_seconds`/`whisper_overlap_seconds` em `services/transcription-service/app/config.py`, consumida por `StreamingTranscriber` em `services/transcription-service/app/transcriber.py`.

## Clarifications

### Session 2026-07-22

- Q: O teto de crescimento da janela adaptativa deve ser o próprio valor padrão atual (3.2s), ou um máximo configurável separado que pode superar o padrão? → A: O teto é o próprio valor padrão atual — a janela nunca ultrapassa o baseline de hoje; o ajuste é puramente defensivo (encolhe sob estresse, recupera até o padrão, nunca cresce além dele).
- Q: A política de ajuste deve ser avaliada a cada transcrição concluída do canal (orientada a evento) ou em um intervalo fixo de relógio independente da taxa de transcrições? → A: Orientada a evento — uma avaliação a cada transcrição concluída (segmento) daquele canal, reaproveitando o fluxo já existente do `StreamingTranscriber`, sem novo timer/agendador em background.
- Q: A decisão de encolher/crescer deve exigir concordância entre p50 e p95, ou p95 sozinho já é suficiente? → A: p95 é o sinal suficiente para a decisão; p50 permanece exposto apenas para observabilidade, sem atuar como porta adicional de decisão.
- Q: O ajuste adaptativo deve ter uma flag de habilitar/desabilitar (seguindo o padrão `echo_suppression_enabled`), e qual o valor padrão? → A: Nova flag de configuração, desabilitada por padrão (opt-in); com a flag desabilitada, o comportamento permanece idêntico ao atual (janela estática), sem nenhuma avaliação de política.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Janela encolhe quando a latência sobe (Priority: P1)

Durante uma sessão ativa, a latência de transcrição de um canal (p95) sobe de forma sustentada acima de um limite saudável — por exemplo, por carga momentânea na GPU. O sistema reduz gradualmente o tamanho da janela de captura/segmentação daquele canal, dentro de um intervalo seguro, para devolver a latência a um patamar aceitável mais rápido, sem alterar o contrato de eventos publicado.

**Why this priority**: É o motivo de existir da issue #17 — sem esta capacidade, o operador só percebe uma sessão travando/atrasando sem nenhuma resposta automática do sistema.

**Independent Test**: Alimentar o registro de métricas de um canal com amostras de latência sintéticas cujo p95 ultrapassa o limite superior configurado, sem GPU nem hardware de áudio real, e verificar que a política de ajuste calcula uma nova janela menor que a anterior, respeitando o limite mínimo configurado.

**Acceptance Scenarios**:

1. **Given** um canal com p95 de latência estável e dentro dos limites saudáveis, **When** a política de ajuste é avaliada, **Then** a janela permanece no valor atual (nenhuma mudança é aplicada).
2. **Given** um canal cujo p95 de latência ultrapassa o limite superior de forma sustentada (não uma única amostra isolada), **When** a política de ajuste é avaliada, **Then** a janela desse canal é reduzida em um passo controlado, sem nunca ficar abaixo do mínimo seguro configurado.
3. **Given** um canal já na janela mínima permitida e com p95 ainda acima do limite, **When** a política de ajuste é avaliada, **Then** a janela permanece no mínimo (nenhuma redução adicional é tentada) e o fato de estar no piso fica observável.

---

### User Story 2 - Janela volta a crescer quando a latência normaliza (Priority: P2)

Depois de um período de latência alta que reduziu a janela de um canal, a latência volta a ficar consistentemente baixa (p95 dentro da faixa saudável por um período mínimo; p50 permanece disponível apenas para observabilidade, sem ser porta de decisão). O sistema aumenta gradualmente a janela de volta em direção ao valor padrão, para recuperar o contexto fonético que beneficia a qualidade da transcrição, sem causar oscilação (não some e volta a cada avaliação).

**Why this priority**: Sem recuperação, a primeira degradação de latência da sessão penalizaria a qualidade de transcrição permanentemente — a issue exige explicitamente histerese para evitar oscilação, o que implica também poder crescer de volta de forma estável.

**Independent Test**: Após reduzir a janela de um canal sintético por latência alta, alimentar o registro com amostras de latência consistentemente baixas por um número mínimo de avaliações consecutivas e verificar que a janela cresce em passos controlados até o padrão, sem nunca ultrapassá-lo e sem alternar para baixo novamente antes do período mínimo de estabilidade.

**Acceptance Scenarios**:

1. **Given** um canal com janela reduzida anteriormente e p95 voltando a ficar dentro da faixa saudável, **When** essa condição se mantém por um número mínimo de avaliações consecutivas (janela de estabilidade), **Then** a janela do canal aumenta em um passo controlado em direção ao valor padrão.
2. **Given** um canal cuja latência oscila acima e abaixo do limite entre avaliações consecutivas (não estável o suficiente), **When** a política é avaliada repetidamente, **Then** a janela não muda de direção a cada avaliação — a histerese evita ajustes revertidos em sequência imediata.
3. **Given** um canal cuja janela já está no valor padrão (teto de recuperação), **When** a política é avaliada e a latência continua baixa, **Then** a janela permanece no valor padrão (nenhum crescimento além dele).

---

### User Story 3 - Ajuste é isolado por sessão/canal e observável, sem afetar o contrato (Priority: P3)

Uma sessão com múltiplos canais (por exemplo, microfone e áudio do sistema) tem cada canal avaliado e ajustado de forma independente — a degradação de latência em um canal não altera a janela de outro canal da mesma sessão nem de outras sessões. O valor de janela aplicado a cada momento é observável (métricas/logs), e os eventos `transcript-event.v2` publicados continuam com o mesmo formato de sempre, independentemente do tamanho de janela usado para gerá-los.

**Why this priority**: É a garantia de segurança e de fronteira explícita na issue ("Contrato v2 inalterado", "Isolamento por sessão/canal", "Observabilidade do ajuste aplicado") — vem depois das duas histórias de comportamento porque valida que o ajuste não introduz efeitos colaterais indevidos.

**Independent Test**: Rodar a política de ajuste para dois canais sintéticos da mesma sessão com perfis de latência opostos (um degradado, um saudável) e verificar que cada canal converge para uma janela diferente e correta; inspecionar o payload de um evento v2 publicado com janela ajustada e confirmar que seu formato é idêntico ao de um evento gerado com a janela padrão; consultar o valor de janela aplicado por canal via métrica/log.

**Acceptance Scenarios**:

1. **Given** dois canais na mesma sessão com perfis de latência distintos, **When** a política de ajuste é avaliada para ambos, **Then** cada canal converge de forma independente para sua própria janela, sem que o ajuste de um influencie o outro.
2. **Given** um canal cuja janela foi ajustada para um valor diferente do padrão, **When** um evento `transcript.partial.v2`/`transcript.final.v2` é publicado a partir de áudio segmentado nessa janela, **Then** o payload do evento é validado pelo mesmo contrato `transcript-event.v2.schema.json` e não contém nenhum campo novo relacionado ao tamanho de janela.
3. **Given** um ajuste de janela aplicado a um canal, **When** o valor atual da janela desse canal é consultado (métrica ou log estruturado), **Then** o valor observado corresponde exatamente ao valor efetivamente usado na segmentação do canal naquele momento.

---

### Edge Cases

- O que acontece quando um canal é novo e ainda não tem amostras suficientes de latência (SF-016 retorna `sampleCount` baixo ou métricas nulas)? A política não ajusta — o canal usa a janela padrão até acumular amostras suficientes para uma decisão confiável (ver Assumptions).
- O que acontece se a latência degradar tão rápido que múltiplos limites sejam cruzados em uma única avaliação? O passo de redução por avaliação permanece limitado (nunca pula direto para o mínimo), mesmo que o p95 esteja muito acima do limite.
- O que acontece quando o canal é encerrado (fim da sessão ou desconexão) enquanto tem uma janela ajustada diferente do padrão? O estado de ajuste daquele canal é descartado; não há necessidade de persistir ou restaurar o ajuste entre sessões (ver Assumptions).
- O que acontece se `whisper_min_audio_seconds` ou `whisper_overlap_seconds` (configurações existentes) entrarem em conflito com os novos limites min/max de janela? O limite mínimo seguro desta feature nunca pode ficar menor ou igual ao overlap configurado, para preservar a invariante já existente (`overlap < window`).
- O que acontece durante a reconexão de hot-plug (SF-019) de um dispositivo no meio de uma sessão? O canal recém-reconectado reinicia a avaliação de ajuste do zero (sem herdar o estado de ajuste anterior daquele endpoint), tratado como um canal novo.
- O que acontece quando um canal fica temporariamente sem novas transcrições concluídas (silêncio prolongado)? A política não é reavaliada nesse intervalo — a janela permanece no último valor aplicado até a próxima transcrição concluída, já que a avaliação é orientada a evento, não a um relógio.
- O que acontece quando a flag de ajuste adaptativo está desabilitada (valor padrão)? Todos os canais usam a janela estática atual, sem nenhuma avaliação de política, mesmo havendo métricas de latência disponíveis para eles.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST calcular, para cada canal de cada sessão ativa, uma janela de captura/segmentação alvo com base no `p95Ms` de latência (sinal de decisão) já exposto pela SF-016 para aquele canal; `p50Ms` e `sampleCount` permanecem disponíveis para observabilidade e para a checagem de amostras suficientes (FR-008), sem atuar como porta adicional de decisão.
- **FR-002**: O sistema MUST manter um limite mínimo seguro configurável de janela, estritamente maior que o overlap configurado para aquele canal; o teto de crescimento/recuperação MUST ser o próprio valor padrão da janela (`whisper_window_seconds`) — não existe um máximo configurável separado maior que o padrão, e a janela ajustada nunca MUST ultrapassar esse valor.
- **FR-003**: O sistema MUST aplicar histerese na política de ajuste — mudanças de direção (crescer após reduzir, ou vice-versa) exigem que a condição de latência observada se mantenha estável por um número mínimo de avaliações consecutivas, para evitar oscilação a cada avaliação. Cada avaliação ocorre uma vez por transcrição concluída (segmento) daquele canal — a política é orientada a evento, não a um intervalo fixo de relógio.
- **FR-004**: O sistema MUST aplicar os ajustes em passos controlados (incrementos/decrementos limitados por avaliação), nunca saltando diretamente do valor atual para o mínimo ou o máximo em uma única avaliação.
- **FR-005**: O sistema MUST isolar o estado e o resultado do ajuste por combinação de sessão e canal — o ajuste de um canal MUST NOT alterar a janela de outro canal, seja da mesma sessão ou de outra.
- **FR-006**: O sistema MUST continuar publicando eventos `transcript-event.v2` (`transcript.partial.v2`/`transcript.final.v2`) em conformidade com `contracts/transcript-event.v2.schema.json`, sem nenhuma alteração de campo, independentemente do tamanho de janela usado para gerar o evento.
- **FR-007**: O sistema MUST expor o valor de janela atualmente aplicado a cada canal de forma observável (métrica e/ou log estruturado), permitindo auditar quando e por que um ajuste ocorreu.
- **FR-008**: O sistema MUST usar a janela padrão (valor atual de `whisper_window_seconds`) para qualquer canal sem amostras suficientes de latência para uma decisão confiável, evitando ajustes baseados em dados insuficientes.
- **FR-009**: Testes automatizados MUST verificar a política de ajuste (redução, recuperação, histerese, limites, isolamento por canal) usando métricas de latência sintéticas, sem depender de GPU, hardware de áudio real ou execução de modelo STT.
- **FR-010**: A política de ajuste e seus parâmetros (limites de latência, min/max de janela, passo de ajuste, período de estabilidade) MUST ser documentados de forma testável, permitindo que outro desenvolvedor reproduza o comportamento esperado a partir da documentação.
- **FR-011**: O sistema MUST fornecer uma flag de configuração dedicada, desabilitada por padrão, que controla se o ajuste adaptativo de janela está ativo. Com a flag desabilitada, todos os canais MUST usar a janela estática atual (`whisper_window_seconds`), sem nenhuma avaliação da política, preservando o comportamento anterior a esta feature.

### Key Entities *(include if feature involves data)*

- **Política de janela adaptativa**: função de decisão que, a partir do snapshot de latência de um canal (SF-016), determina se a janela de captura/segmentação deve crescer, encolher ou permanecer igual, respeitando limites e histerese. Não persiste em banco; vive em memória junto ao processo do serviço de transcrição.
- **Estado de ajuste por canal**: janela atual aplicada, direção do último ajuste e contador de avaliações estáveis para uma combinação `(sessionId, channelId)`; descartado quando o canal/sessão termina.
- **Snapshot de latência (SF-016)**: entrada da política — `p95Ms` é o sinal usado na decisão de ajuste; `p50Ms` e `sampleCount` permanecem disponíveis para observabilidade e para a checagem de amostras suficientes; já existente e inalterado por esta feature.
- **Janela de captura/segmentação**: quantidade de áudio (atualmente em segundos, ver `whisper_window_seconds`) acumulada antes de ser enviada ao modelo de transcrição; esta feature torna esse valor dinâmico por canal em vez de estático global.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em cenários de latência sustentada acima do limite configurado, a janela do canal afetado converge para um valor menor dentro de, no máximo, um número fixo e documentado de avaliações, sem nunca violar o mínimo seguro.
- **SC-002**: Em cenários de recuperação de latência, a janela do canal volta ao valor padrão em um número fixo e documentado de avaliações, sem reverter de direção antes do período mínimo de estabilidade.
- **SC-003**: 0% dos eventos `transcript-event.v2` publicados durante os testes desta feature falham a validação contra `contracts/transcript-event.v2.schema.json`, independentemente do tamanho de janela usado.
- **SC-004**: Em sessões com dois ou mais canais com perfis de latência distintos, 100% dos ajustes aplicados em teste permanecem isolados ao canal de origem (nenhum vazamento de estado entre canais).
- **SC-005**: 100% dos testes automatizados desta feature (política de ajuste, limites, histerese, isolamento, observabilidade) passam sem exigir GPU ou hardware de áudio físico.
- **SC-006**: A documentação da política de ajuste é suficiente para um novo desenvolvedor prever, para um snapshot de latência dado, qual será a janela resultante, sem precisar ler o código-fonte da implementação.
- **SC-007**: Com a flag de ajuste adaptativo desabilitada (valor padrão), 100% do comportamento de segmentação observado em teste é idêntico ao comportamento anterior a esta feature — nenhuma mudança de janela ocorre.

## Assumptions

- A política de ajuste consome os campos já expostos por `GET /v1/sessions/{sessionId}/metrics` (SF-016) — `p95Ms` como sinal de decisão, `p50Ms` e `sampleCount` como observabilidade/checagem de amostras suficientes — sem exigir nenhuma nova métrica ou alteração no `LatencyMetricsRegistry` existente.
- O valor padrão da janela (ponto de partida e único teto de recuperação) é o `whisper_window_seconds` já configurado hoje (3.2s); não existe um máximo configurável separado maior que esse padrão — o ajuste é estritamente defensivo (encolhe sob estresse, recupera até o padrão), nunca uma tentativa de melhorar a qualidade além do baseline atual.
- O estado de ajuste por canal vive inteiramente em memória, no mesmo processo do serviço de transcrição; não há persistência em banco (Memory Hub / R3) nem necessidade de restaurar o estado após um restart do serviço — está fora de escopo, conforme a issue.
- Um canal recém-conectado ou reconectado (incluindo hot-plug, SF-019) começa sempre na janela padrão, tratado como sem histórico de ajuste anterior.
- Os limites de latência (o que conta como "sustentado", quantas avaliações formam o período de estabilidade) e os limites de janela (mínimo/passo) são parâmetros configuráveis com valores padrão razoáveis, documentados e testáveis — não exigem descoberta automática nem aprendizado de máquina.
- A flag de habilitação segue o mesmo padrão já usado para outras mudanças de comportamento na captura/segmentação (ex.: `echo_suppression_enabled`), mantendo consistência de configuração no serviço de transcrição.
- Captura por processo isolado (SF-020) e qualquer superfície de UI desktop para visualizar/configurar o ajuste estão fora de escopo desta feature, conforme definido na issue.
- Persistência de métricas de latência em banco de dados está fora de escopo desta feature; a SF-016 já as mantém em memória e esta feature apenas as lê.
