# Requirements Quality Checklist: Listener de hot-plug nativo MMDevice (SF-019)

**Purpose**: Validar a qualidade (completude, clareza, consistência, mensurabilidade) dos requisitos
desta feature, com peso extra em isolamento de processo (P6/ADR-0007) e testabilidade sem hardware
(P10) — as duas dimensões constitucionais mais arriscadas para este design (listener nativo COM
embutido em subprocesso isolado). Profundidade: autorrevisão padrão pré-`/speckit.tasks`, não um gate
formal de release.
**Created**: 2026-07-21
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [research.md](../research.md)

**Note**: Este checklist testa os REQUISITOS (spec/plan/research), não a implementação — nenhum item
verifica comportamento de código.

## Requirement Completeness

- [ ] CHK001 Are requirements defined for what happens when the native COM registration itself fails at listener startup — not just for a notification received during capture? [Completeness, Spec §FR-006]
- [ ] CHK002 Are requirements defined for listener cleanup/teardown when the worker exits normally, distinct from the removal/backoff path? [Gap]
- [ ] CHK003 Is the debounce window given any testable bound (even an order-of-magnitude range), or is it left entirely open to implementation with no acceptance check? [Completeness, Spec §Assumptions]

## Requirement Clarity

- [ ] CHK004 Is "erro específico de endpoint removido" (FR-002) defined precisely enough to be distinguished from a generic stream error by an automated test, or does it rely only on prose description? [Clarity, Spec §FR-002]
- [ ] CHK005 Is "janela curta" (debounce, Research §4) quantified with any testable bound, or left ambiguous for test design? [Clarity, Research §4]
- [ ] CHK006 Is "imediatamente" (SC-001, FR-002/FR-003) given a concrete, testable meaning beyond "not waiting for the next backoff cycle"? [Ambiguity, Spec §SC-001]

## Requirement Consistency

- [ ] CHK007 Do FR-003 and User Story 2's acceptance scenarios agree on the exact channel state ("em espera de reconexão") required before an arrival notification triggers a resume? [Consistency, Spec §FR-003]
- [ ] CHK008 Do FR-001, Key Entities, and the Clarifications session agree — with no residual contradiction — on exactly which process instantiates the listener? [Consistency, Spec §Clarifications]

## Isolamento de processo (P6/ADR-0007) — peso priorizado

- [ ] CHK009 Is it explicit that a listener instance/registration must never be shared across two different channel workers, even when both target the same `endpointId`? [Completeness, Spec §Edge Cases]
- [ ] CHK010 Are requirements clear that failure of one channel's listener registration must not affect or disable another channel's listener? [Coverage, Spec §FR-006, Plan §Constitution Check P6]
- [ ] CHK011 Is it specified that the listener's thread/callback lifecycle must terminate together with its worker's `stop_event`, with no dangling COM registration after shutdown? [Gap]
- [ ] CHK012 Are requirements defined for a worker terminated by the supervisor mid-notification-processing — is the fate of a partially-handled event specified? [Gap, Edge Case]
- [ ] CHK013 Does the plan's decision to avoid new supervisor↔worker IPC have a corresponding requirement ruling out any future accidental cross-process signaling path for hot-plug events? [Consistency, Plan §Technical Context]

## Testabilidade sem hardware (P10) — peso priorizado

- [ ] CHK014 Are the exact behaviors a fake notification provider must support (subscribe, emit, close) specified as requirements, or only implied by FR-007? [Completeness, Spec §FR-007]
- [ ] CHK015 Is it specified that tests must control debounce timing deterministically (e.g., injectable clock) rather than relying on real sleeps? [Gap, Research §4]
- [ ] CHK016 Are requirements explicit that no test path may load `comtypes`/`pycaw`, even transitively, when exercising the listener's testable behavior? [Clarity, Spec §FR-006/FR-007]
- [ ] CHK017 Is there a success criterion requiring the null/degraded provider path (FR-006) to be exercised by an automated test, not only asserted in prose? [Traceability, Spec §SC-003]
- [ ] CHK018 Is SC-005 ("no máximo uma reação por rajada") specific enough to be verified by a call-count assertion, or does the wording leave room for interpreting what counts as "uma reação"? [Measurability, Spec §SC-005]

## Acceptance Criteria Quality

- [ ] CHK019 Can SC-001 and SC-002 be verified without depending on wall-clock timing assumptions that could flake in CI? [Measurability, Spec §SC-001/SC-002]
- [ ] CHK020 Is SC-004 ("nenhum fallback silencioso") paired with an enumerable list of scenarios a test must cover, or is it an open-ended claim? [Measurability, Spec §SC-004]

## Scenario Coverage

- [ ] CHK021 Are requirements defined for two channels sharing the same `endpointId` receiving arrival/removal notifications at different times (race between independent workers)? [Edge Case, Spec §Edge Cases]
- [ ] CHK022 Is the boundary between this feature's listener and SF-018's initial-resolution-failure contract (FR-007 of SF-018) fully bounded, with no scenario left ambiguous about which spec governs it? [Consistency, Spec §Fora de escopo]

## Dependencies & Assumptions

- [ ] CHK023 Is the assumption that pycaw's underlying comtypes wrapper exposes `IMMNotificationClient` validated anywhere (spike/prototype), or is it an unverified assumption carried into planning? [Assumption, Research §1]
- [ ] CHK024 Is the dependency on the existing `stop_event`/backoff mechanism in `capture.py` documented precisely enough that a future change to that mechanism would be flagged as breaking this feature? [Dependency, Plan §Technical Context]

## Ambiguities & Conflicts

- [ ] CHK025 Is there residual ambiguity about what "retomar no mesmo endpoint físico" (FR-003) means if a device with the same friendly name reappears under a different `endpointId` (e.g., after driver reinstall)? [Ambiguity, Spec §FR-003]

## Notes

- Foco escolhido: isolamento de processo (P6) e testabilidade sem hardware (P10), ponderados acima
  das demais dimensões a pedido do usuário.
- Profundidade: autorrevisão padrão pré-`/speckit.tasks` (não um gate formal de release).
- Itens marcados `[Gap]` indicam requisito ausente na spec/plan atual, não um defeito de implementação.
- Check items off as completed: `[x]`.
