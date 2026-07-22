---

description: "Task list for Janela adaptativa de áudio com base em métricas (SF-022)"
---

# Tasks: Janela adaptativa de áudio com base em métricas (SF-022)

**Input**: Design documents from `/specs/008-sf-022-adaptive-window/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Incluídos — `spec.md` FR-009 exige explicitamente testes automatizados sem GPU/hardware, e cada User Story define seu próprio "Independent Test".

**Organization**: Tarefas agrupadas por user story (`spec.md`), para implementação e teste independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: A qual user story a tarefa pertence (US1, US2, US3)
- Caminhos de arquivo são absolutos-relativos ao repositório

## Path Conventions

Serviço já existente `services/transcription-service` (ver `plan.md` → Project Structure):

- `services/transcription-service/app/config.py` — `Settings` (campos novos)
- `services/transcription-service/app/transcriber.py` — `StreamingTranscriber` (método aditivo)
- `services/transcription-service/app/adaptive_window.py` — módulo novo (`AdaptiveWindowState`, `AdaptiveWindowChannel`, `AdaptiveWindowRegistry`)
- `services/transcription-service/app/main.py` — wiring em `audio_stream` + endpoint `GET /v1/sessions/{sessionId}/metrics`
- `services/transcription-service/tests/` — testes novos e estendidos
- `contracts/transcript-event.v2.schema.json` (raiz do repo) — contrato consumido, sem alteração (FR-006)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar configuração e a capacidade genérica de trocar a janela em tempo de execução — sem nenhuma dependência nova (`plan.md` → Technical Context).

- [x] T001 [P] Adicionar os 7 campos novos (`adaptive_window_enabled`, `adaptive_window_min_seconds`, `adaptive_window_latency_high_ms`, `adaptive_window_latency_low_ms`, `adaptive_window_step_seconds`, `adaptive_window_stable_evaluations`, `adaptive_window_min_samples`) com os padrões documentados em `services/transcription-service/app/config.py` (ver `research.md` §6 / `data-model.md` → Configuração)
- [x] T002 [P] Adicionar `StreamingTranscriber.set_window_seconds(seconds: float) -> None` em `services/transcription-service/app/transcriber.py`, recalculando `_window_bytes` a partir do novo valor e levantando `ValueError` se não ficar estritamente acima do overlap configurado (ver `research.md` §2)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Estrutura de dados mínima usada por todas as user stories — sem lógica de decisão ainda (isso é implementado incrementalmente em US1/US2, ver Tests-first abaixo).

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase estar completa.

- [x] T003 Criar `AdaptiveWindowState` (dataclass: `window_seconds`, `active_direction`, `pending_direction`, `pending_count`) e o construtor de `AdaptiveWindowChannel` (armazena `settings`, inicia o estado em `whisper_window_seconds`, valida `adaptive_window_min_seconds > whisper_overlap_seconds` levantando `ValueError` — ver `research.md` §5) em `services/transcription-service/app/adaptive_window.py` (depende de T001). `evaluate()` ainda não existe/é um stub — a lógica de decisão é adicionada em US1 (encolher) e US2 (crescer)

**Checkpoint**: Estrutura de estado pronta — as user stories podem começar.

---

## Phase 3: User Story 1 - Janela encolhe quando a latência sobe (Priority: P1) 🎯 MVP

**Goal**: Um canal cujo `p95Ms` ultrapassa o limite superior de forma sustentada tem sua janela de captura/segmentação reduzida em passos controlados, sem nunca ficar abaixo do piso seguro, com o estado de piso observável.

**Independent Test**: Instanciar `AdaptiveWindowChannel` diretamente e chamar `evaluate(p95_ms=..., sample_count=...)` repetidamente com valores sintéticos de latência alta sustentada, sem GPU, hardware nem WebSocket — verificar que a janela retornada diminui em passos controlados e nunca ultrapassa o piso configurado.

### Tests for User Story 1 ⚠️

> Escrever estes testes primeiro; devem falhar antes da implementação (T003 ainda não tem lógica de encolhimento).

- [x] T004 [P] [US1] Escrever `services/transcription-service/tests/test_adaptive_window.py`: p95 estável e saudável → janela não muda (AC1); p95 sustentado acima do limite por N avaliações → janela reduz em um passo controlado, nunca abaixo do piso (AC2); já no piso com p95 ainda alto → nenhuma redução adicional, estado "no piso" observável via atributo do objeto (AC3); `sampleCount` insuficiente ou `p95Ms` ausente → nenhuma mudança (FR-008); um único pico isolado (1 avaliação) não é suficiente para mudar a janela (histerese de ativação, FR-003)

### Implementation for User Story 1

- [x] T005 [US1] Implementar em `services/transcription-service/app/adaptive_window.py` o ramo de encolhimento e o ramo estável de `AdaptiveWindowChannel.evaluate(p95_ms, sample_count) -> float` (checagem de amostras insuficientes, cálculo de `desired` para "down"/"stable", confirmação por `adaptive_window_stable_evaluations`, passo controlado por `adaptive_window_step_seconds`, recorte no piso `adaptive_window_min_seconds` — ver `research.md` §3/§6); o ramo "up" permanece tratado como "stable" nesta fase (ativado em US2) — depende de T003; faz T004 passar
- [x] T006 [US1] Ligar `AdaptiveWindowChannel` ao handler `audio_stream` em `services/transcription-service/app/main.py`: quando `settings.adaptive_window_enabled`, instanciar um `AdaptiveWindowChannel` por conexão, chamar `.evaluate(p95_ms, sample_count)` logo após `metrics.record_transcription(...)` (usando `metrics.session_snapshot(session_id)` já existente, filtrando pelo `channel_id`), aplicar o resultado via `transcriber.set_window_seconds(...)` e logar em `INFO` toda mudança de janela (`sessionId`, `channelId`, valor anterior, novo, direção) — ver `research.md` §1/§4 — depende de T002, T005
- [x] T007 [P] [US1] Escrever `services/transcription-service/tests/test_adaptive_window_endpoint.py` (novo arquivo): via `create_app(metrics_registry=...)` pré-populado com amostras de latência alta sintéticas (mesmo padrão de `test_session_metrics_endpoint.py`), confirmar que a janela realmente aplicada por `StreamingTranscriber` diminui end-to-end; caso companheiro com a flag desabilitada (padrão) prova que nenhuma mudança ocorre (SC-007, ponta a ponta) — depende de T006

**Checkpoint**: US1 completa e testável de forma independente (`pytest -q tests -k adaptive_window`, `quickstart.md` §1).

---

## Phase 4: User Story 2 - Janela volta a crescer quando a latência normaliza (Priority: P2)

**Goal**: Depois de um encolhimento, um canal cujo `p95Ms` volta a ficar saudável por um período mínimo tem sua janela recuperada gradualmente até o valor padrão (teto), sem oscilar a cada avaliação.

**Independent Test**: Reduzir a janela de um `AdaptiveWindowChannel` sintético (como em US1) e então alimentar `evaluate()` com `p95Ms` consistentemente baixo por N avaliações consecutivas — verificar que a janela cresce em passos controlados até o padrão, sem ultrapassá-lo e sem reverter de direção antes do período mínimo de estabilidade.

### Tests for User Story 2 ⚠️

> Estender o arquivo de US1; estes casos devem falhar até T009 (o ramo "up" ainda é tratado como "stable" após T005).

- [x] T008 [P] [US2] Estender `services/transcription-service/tests/test_adaptive_window.py`: após reduzir a janela, p95 saudável por N avaliações consecutivas → janela cresce em passo controlado em direção ao padrão (AC1); padrão nunca é ultrapassado mesmo com p95 continuamente baixo (AC3, teto = Clarifications); p95 oscilando acima/abaixo do limite entre avaliações consecutivas não reverte a direção a cada avaliação (AC2, histerese de reversão)

### Implementation for User Story 2

- [x] T009 [US2] Confirmado sem alteração adicional: o ramo "up" já foi implementado junto com o ramo "down" em T005 (algoritmo único do state machine, ver `research.md` §3) — T008 passou de primeira contra o código já existente, sem precisar mudar `services/transcription-service/app/adaptive_window.py`

**Checkpoint**: US1 e US2 funcionam de forma independente e conjunta (`pytest -q tests -k adaptive_window`).

---

## Phase 5: User Story 3 - Ajuste é isolado por sessão/canal e observável, sem afetar o contrato (Priority: P3)

**Goal**: Canais distintos da mesma sessão convergem para janelas independentes sem vazamento; o evento `transcript-event.v2` publicado continua validando contra o contrato existente independentemente da janela usada; o valor de janela aplicado por canal é consultável via `GET /v1/sessions/{sessionId}/metrics`.

**Independent Test**: Rodar dois canais sintéticos da mesma sessão com perfis de latência opostos e verificar que cada um converge para sua própria janela; inspecionar um evento publicado com janela ajustada contra `contracts/transcript-event.v2.schema.json`; consultar `GET /v1/sessions/{sessionId}/metrics` e confirmar que `windowMs` reflete o valor aplicado.

### Tests for User Story 3 ⚠️

- [x] T010 [P] [US3] Estender `services/transcription-service/tests/test_adaptive_window_endpoint.py`: dois canais da mesma sessão com perfis de latência opostos (um degradado, um saudável) convergem para janelas diferentes, sem que o ajuste de um influencie o outro (AC1)
- [x] T011 [P] [US3] Estender `services/transcription-service/tests/test_adaptive_window_endpoint.py`: um evento `transcript.partial.v2`/`transcript.final.v2` publicado a partir de áudio segmentado com janela ajustada ainda valida contra `contracts/transcript-event.v2.schema.json` (mesmo schema já usado por `test_ws_audio_contract.py`) e não ganha nenhum campo novo relacionado ao tamanho de janela (AC2, SC-003)
- [x] T012 [P] [US3] Estender `services/transcription-service/tests/test_adaptive_window_endpoint.py`: `GET /v1/sessions/{sessionId}/metrics` reporta `windowMs` por canal igual ao valor efetivamente aplicado; `windowMs` é `null` com a flag desabilitada ou antes da primeira avaliação do canal (AC3, FR-007)

### Implementation for User Story 3

- [x] T013 [P] [US3] Criar `AdaptiveWindowRegistry` em `services/transcription-service/app/adaptive_window.py`: dict thread-safe `(session_id, channel_id) -> window_ms`, mesmo padrão de lock de `LatencyMetricsRegistry`, limitado por `settings.metrics_max_channels` (ver `data-model.md` → AdaptiveWindowRegistry) — depende de T003
- [x] T014 [US3] Em `services/transcription-service/app/main.py`: registrar em `AdaptiveWindowRegistry` toda vez que a janela de um canal é aplicada (estende o wiring de T006) e adicionar o campo `windowMs` (por canal, `null` quando ausente) à resposta já existente de `GET /v1/sessions/{sessionId}/metrics` — depende de T013, T006; faz T012 passar
- [x] T015 [US3] Confirmado sem alteração: cada conexão WebSocket instancia seu próprio `AdaptiveWindowChannel` local em `audio_stream` (T006); nenhum estado mutável de decisão é compartilhado entre canais — apenas o `AdaptiveWindowRegistry` é compartilhado, e é isolado por chave `(sessionId, channelId)`. T010 passou de primeira, sem exigir mudança em `main.py`/`adaptive_window.py`

**Checkpoint**: As três user stories funcionam de forma independente e conjunta.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Fechamento da issue #17 — suíte completa verde, documentação de operação e evidência da validação.

- [x] T016 [P] Rodar a suíte completa (`PYTHONPATH=services/transcription-service .venv-transcription/bin/python -m pytest -q services/transcription-service/tests`) e confirmar ausência de regressão, sem GPU/hardware (FR-009, SC-005)
- [x] T017 [P] Executar `quickstart.md` (validação automatizada + inspeção manual do campo `windowMs`) e registrar o resultado no resumo da PR
- [x] T018 [P] Criar `docs/validation/sf-022-adaptive-window.md` documentando a política (parâmetros, algoritmo de histerese, número máximo de avaliações para atingir piso/teto a partir dos valores padrão) de forma testável, para satisfazer FR-010/SC-006 e fechar o item CHK011 do checklist `g2-plan-gate.md`
- [x] T019 [P] Atualizar `docs/validation/sf-016-latency-metrics.md` com uma nota sobre o campo aditivo `windowMs` em `GET /v1/sessions/{sessionId}/metrics`, fechando o item CHK002 do checklist `g2-plan-gate.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: depende do Setup (T001) — BLOQUEIA todas as user stories
- **User Stories (Phase 3–5)**: todas dependem da conclusão da Fase 2
  - US1 (P1) é o MVP e deve ser concluída primeiro na prática, pois US2 e US3 completam/estendem o mesmo `AdaptiveWindowChannel.evaluate()` e o mesmo wiring em `main.py` que US1 cria (T005/T006)
  - US2 completa a lógica de decisão (mesmo método, ramo "up") — não pode ser paralelizada com US1 no mesmo arquivo, mas é testável de forma independente assim que T005 existe
  - US3 pode prosseguir em paralelo com US2 depois que T006 (US1) existir, já que toca preocupações distintas (registry/observabilidade/isolamento) do mesmo wiring
- **Polish (Phase 6)**: depende de todas as user stories desejadas estarem completas

### User Story Dependencies

- **User Story 1 (P1)**: depende apenas da Fase 2 — sem dependência de outra story
- **User Story 2 (P2)**: depende da Fase 2 e de T005 (US1) já existir, pois completa o mesmo método `evaluate()`; ainda assim testável de forma independente (T008 não depende de T010/T013 de US3)
- **User Story 3 (P3)**: depende da Fase 2 e de T006 (US1) já existir (wiring em `main.py`); testável de forma independente de US2

### Parallel Opportunities

- T001 e T002 (Setup) em paralelo
- Dentro de US1: T004 (teste) antes de T005; T007 depende de T006, mas pode ser escrito em paralelo com T005/T006 (arquivo novo, sem dependência de código para ser *escrito*, só para *passar*)
- Dentro de US3: T010, T011, T012 (testes) em paralelo entre si; T013 em paralelo com os testes (arquivo novo); T014 depende de T013 e T006; T015 depende de T006 e T010
- T016, T017, T018, T019 (Polish) em paralelo

---

## Parallel Example: User Story 1

```bash
# Escrever o teste de unidade da política em paralelo com a preparação do teste de integração:
Task: "Escrever services/transcription-service/tests/test_adaptive_window.py (AC1/AC2/AC3/FR-008)"
Task: "Criar services/transcription-service/tests/test_adaptive_window_endpoint.py (esqueleto, fixtures)"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Fase 1: Setup
2. Completar Fase 2: Foundational (bloqueia todas as stories)
3. Completar Fase 3: User Story 1
4. **PARAR e VALIDAR**: `pytest -q tests -k adaptive_window` + `quickstart.md` §1, com a flag ainda desabilitada por padrão em produção
5. Esse MVP já prova o comportamento central da issue #17 (encolher sob latência alta), atrás de um flag seguro (FR-011)

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 → testar independentemente → encolhimento comprovado (MVP)
3. US2 → testar independentemente → recuperação e histerese comprovadas
4. US3 → testar independentemente → isolamento, contrato inalterado e observabilidade HTTP comprovados, fechando os critérios de aceite da issue #17
5. Cada story agrega valor sem quebrar a anterior

### Ordem sugerida (equipe única)

Dada a dependência real de arquivo (`adaptive_window.py`/`main.py` criados em US1 e completados por US2/US3), a ordem sequencial P1 → P2 → P3 é mais simples do que paralelizar entre desenvolvedores neste caso específico.

---

## Notes

- `[P]` = arquivos diferentes, sem dependência de tarefa incompleta
- Rótulo `[Story]` mapeia a tarefa à user story correspondente em `spec.md`
- Testes devem ser escritos e falhar antes da implementação correspondente
- Fazer commit após cada tarefa ou grupo lógico
- Parar em qualquer checkpoint para validar a story isoladamente
- Evitar: tarefas vagas, conflito no mesmo arquivo sem necessidade, dependências entre stories que quebrem a independência de teste
- Itens `[Gap]`/`[Ambiguity]` do checklist `checklists/g2-plan-gate.md` não cobertos por uma tarefa explícita (ex.: CHK004, CHK014) permanecem como decisões já registradas em `research.md` — revisar no gate G2 antes do Implement
