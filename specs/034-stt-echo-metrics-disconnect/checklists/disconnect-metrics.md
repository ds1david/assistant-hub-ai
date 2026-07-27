# Disconnect & Echo Metrics Requirements Checklist: STT finalização no disconnect

**Purpose**: Validar qualidade, clareza e cobertura dos requisitos desta feature (unit tests for English) — não a implementação em runtime  
**Created**: 2026-07-27  
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [contracts/session-metrics-disconnect.md](../contracts/session-metrics-disconnect.md)  
**Depth**: Standard  
**Audience**: Reviewer (PR / G2)  
**Focus**: disconnect residual, contagem de métricas, eco, multi-canal, timeouts/observabilidade

## Requirement Completeness

- [x] CHK001 Are residual finalization requirements on channel disconnect fully specified for open and already-idle utterances? [Completeness, Spec §FR-001, §Edge Cases]
- [x] CHK002 Is the definition of a “delivered” event for metrics documented (what increments sampleCount/totalEvents)? [Completeness, Spec §Clarifications, §FR-002]
- [x] CHK003 Are multi-channel nested teardown requirements (system + microphone) documented with expected counts? [Completeness, Spec §US2, §FR-008]
- [x] CHK004 Are feed fan-out timeout bounds specified as product requirements (not only plan notes)? [Completeness, Spec §FR-012]
- [x] CHK005 Is stress acceptance for the echo scenario quantified (minimum repetitions)? [Completeness, Spec §FR-009, §SC-005]

## Requirement Clarity

- [x] CHK006 Is “must not abandon finalization because the audio client closed” unambiguous about permanent loss vs. temporary early read? [Clarity, Spec §FR-001, §SC-002]
- [x] CHK007 Is the ordering “record metrics before send awaits” stated as a requirement (not only research)? [Clarity, Spec §FR-003]
- [x] CHK008 Is skip of direct audio-WS send for disconnect finals distinguished from idle/max-open finals? [Clarity, Spec §FR-004, Clarifications]
- [x] CHK009 Is sequential per-connection processing stated so disconnect ticks cannot be dropped by a queue policy? [Clarity, Spec §FR-011]

## Requirement Consistency

- [x] CHK010 Do metrics counting rules stay consistent with ADR-0008 (suppressed echo never delivered)? [Consistency, Spec §FR-005, ADR-0008]
- [x] CHK011 Are disconnect finals consistent with 024 (no double final after idle without new residual)? [Consistency, Spec §Edge Cases, 024]
- [x] CHK012 Do SC-001–SC-003 numeric expectations align with FR-002/FR-005/FR-008? [Consistency, Spec §Success Criteria]
- [x] CHK013 Is “no schema change” consistent across Spec Assumptions, Plan, and Contract? [Consistency, Spec §Assumptions, Plan, Contract]

## Acceptance Criteria Quality

- [x] CHK014 Can SC-001 (sampleCount == 2 after partial + disconnect final) be objectively verified without GPU? [Measurability, Spec §SC-001]
- [x] CHK015 Is the 2-second poll window for multi-channel metrics completion measurable and testable? [Measurability, Spec §SC-002]
- [x] CHK016 Does SC-004 clearly forbid multiplying counts by feed subscriber N? [Measurability, Spec §SC-004]
- [x] CHK017 Is SC-005 stress criterion actionable (≥ 60 runs) for CI or local gate? [Measurability, Spec §SC-005, quickstart]

## Scenario Coverage

- [x] CHK018 Are primary flows covered: single-channel disconnect metrics, echo multi-channel, isolation, operator/CI trust? [Coverage, Spec §US1–US4]
- [x] CHK019 Are exception/recovery paths covered: closed audio client, slow feed subscriber, cancel during teardown? [Coverage, Spec §Edge Cases, §FR-001]
- [x] CHK020 Is empty/no-useful-text disconnect covered (no invented samples)? [Coverage, Spec §Edge Cases]
- [x] CHK021 Are retention interactions (sampleCount vs totalEvents after many events) acknowledged? [Coverage, Spec §Edge Cases, data-model]

## Edge Case & Non-Functional Coverage

- [x] CHK022 Are privacy constraints on disconnect logs specified (ids/counters only, no PCM)? [NFR, Spec §FR-010, P9]
- [x] CHK023 Are deterministic test requirements (no GPU/WASAPI) explicit? [NFR, Spec §FR-009, P10]
- [x] CHK024 Are channel identity requirements for disconnect finals (sessionId/channelId/sourceType/label) explicit? [NFR, Spec §FR-004, P5]

## Dependencies & Assumptions

- [x] CHK025 Is dependency on 024 utterance policy (idle/max-open unchanged) documented as assumption? [Assumption, Spec §Assumptions]
- [x] CHK026 Is dependency on existing metrics endpoint shape (no new fields) documented? [Dependency, Spec §FR-007, Contract]
- [x] CHK027 Is out-of-scope for AEC / shell metrics UI / echo threshold redesign explicit? [Boundary, Spec §Out of Scope]

## Ambiguities & Conflicts

- [x] CHK028 Is any remaining ambiguity about “delivered vs successfully received by all subscribers” resolved? [Ambiguity, Spec §Clarifications]
- [x] CHK029 Do plan timeouts (1.0s / 0.5s) match FR-012 without conflicting numbers elsewhere? [Consistency, Spec §FR-012, Plan, Contract]
- [x] CHK030 Is the relationship between permanent loss (bug) and early-read poll (allowed) free of contradiction? [Conflict check, Spec §US1 A2, §SC-002]

## Notes

- Items are requirements-quality checks; mark `[x]` when the **written requirements** satisfy the question.
- Traceability: prefer Spec section + Contract + Plan when validating G2.
- Soft cap respected (~30 items).

### Review pass (2026-07-27)

All CHK001–CHK030 marked complete against clarified spec + plan + contract. Implementation verified on branch `fix/stt-echo-metrics-disconnect-final`: suite 126 passed; echo stress 60/60; metrics-before-prosody/send hardening applied.
