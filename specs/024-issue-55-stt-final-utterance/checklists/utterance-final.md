# Utterance Finalization Requirements Checklist: STT final-on-utterance (issue #55)

**Purpose**: Validate quality, clarity, completeness, and consistency of requirements for end-of-utterance final transcript emission (requirements-as-unit-tests — not implementation verification)  
**Created**: 2026-07-25  
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [data-model.md](../data-model.md) · [contracts/utterance-finalization.md](../contracts/utterance-finalization.md)  
**Depth**: Standard  
**Audience**: Author + PR reviewer (G2 Plan / pre-implement)  
**Focus**: Finalization policy · cardinality · identity · live-answer boundary · testability · privacy

## Requirement Completeness

- [ ] CHK001 Are open/close rules for an utterance fully specified (open after first useful text; close on idle and max-open)? [Completeness, Spec §FR-003, data-model transitions]
- [ ] CHK002 Are both partial and final publication requirements stated without implying removal of partials? [Completeness, Spec §FR-001, FR-002]
- [ ] CHK003 Is “no final without useful text” documented as a hard rule? [Completeness, Spec §FR-006, Edge Cases]
- [ ] CHK004 Are disconnect residual final rules and double-final prohibition both specified? [Completeness, Spec §FR-010]
- [ ] CHK005 Are documentation obligations for operators (final-on-utterance vs disconnect-only) specified? [Completeness, Spec §FR-012, US4]
- [ ] CHK006 Is the live-answer boundary (final only; no partial invoke) explicitly required? [Completeness, Spec §FR-008, Out of Scope]

## Requirement Clarity

- [ ] CHK007 Is the idle close criterion quantified (default idle window count) rather than only “pausa”? [Clarity, Spec §FR-003, Clarify session]
- [ ] CHK008 Is the max-open timeout quantified with a default (45s)? [Clarity, Spec §FR-003, SC / Edge Cases]
- [ ] CHK009 Is “último texto útil” defined as the final payload source without ambiguous “consolidated better text”? [Clarity, Spec §FR-006, Clarify Q]
- [ ] CHK010 Is latency expectation after pause expressed as “~1 STT window” (not sub-second)? [Clarity, Spec §SC-007]
- [ ] CHK011 Are configurable setting names/defaults documented for idle and max-open? [Clarity, Plan/Settings, Contract]

## Requirement Consistency

- [ ] CHK012 Do FR-001/FR-003 and data-model transitions agree on when a final is emitted? [Consistency, Spec ↔ data-model]
- [ ] CHK013 Does FR-008 remain consistent with 019 FR-003 (no partial auto-answer)? [Consistency, Spec §FR-008, Dependencies]
- [ ] CHK014 Does FR-009 (no question-heuristic change) stay consistent with US2 acceptance (existence of final only)? [Consistency, Spec §US2, FR-009]
- [ ] CHK015 Do SC-001/SC-002 match FR-004 cardinality (exactly one final per closed utterance)? [Consistency, Spec §SC-001/002, FR-004]
- [ ] CHK016 Is zero schema change (FR-013) consistent with contracts/utterance-finalization.md? [Consistency, Spec §FR-013, Contract]

## Acceptance Criteria Quality

- [ ] CHK017 Can SC-001 be verified without disconnecting the agent (measurable procedure exists)? [Measurability, Spec §SC-001, quickstart Manual A]
- [ ] CHK018 Can SC-002 be verified by counting finals vs partials for one utterance? [Measurability, Spec §SC-002]
- [ ] CHK019 Is SC-003 framed as removing permanent awaiting_final (not guaranteeing model quality)? [Measurability, Spec §SC-003]
- [ ] CHK020 Does SC-005 require CI without GPU/WASAPI? [Measurability, Spec §SC-005, Constitution P10]
- [ ] CHK021 Are automated test obligations for the state machine explicit (FR-011)? [Acceptance Criteria, Spec §FR-011]

## Scenario & Edge Case Coverage

- [ ] CHK022 Are multi-utterance sequences (two pauses → two finals) covered in requirements? [Coverage, Spec §US1 A4]
- [ ] CHK023 Are empty/silence-only streams forbidden from emitting ghost finals? [Coverage, Edge Cases]
- [ ] CHK024 Is independent per-channel finalization (system vs microphone) specified? [Coverage, Edge Cases, P5]
- [ ] CHK025 Is echo-suppressed microphone text excluded from opening/feeding final text? [Coverage, Plan R8, Edge Cases]
- [ ] CHK026 Is adaptive-window impact on idle (count windows, not fixed seconds) addressed in requirements or plan assumptions? [Coverage, Plan R9, Spec Assumptions]
- [ ] CHK027 Are reconnect semantics (state per connection; no re-emit of old finals) specified? [Coverage, Edge Cases]

## Non-Functional & Privacy

- [ ] CHK028 Are privacy constraints for logs (no full transcript dump / raw audio) specified? [NFR, Spec §FR-014, P9]
- [ ] CHK029 Is performance/latency expectation technology-agnostic enough for product (SC-007) while plan holds window mapping? [NFR, Spec §SC-007]
- [ ] CHK030 Is “no new event type” an explicit non-functional/compat requirement? [NFR, Spec §FR-013]

## Dependencies & Ambiguities

- [ ] CHK031 Are dependencies on existing session-core/shell final consumption documented without requiring their reimplementation? [Dependency, Spec §Dependencies, Research R10]
- [ ] CHK032 Is sessionId mismatch correctly treated as out-of-scope for this feature’s root cause? [Assumption, Spec §Assumptions]
- [ ] CHK033 Are plan-owned numeric knobs vs product MUST rules clearly separated so implementers know what is fixed by clarify? [Clarity, Spec Clarify vs Plan]
- [ ] CHK034 Does the requirements set intentionally exclude question detection (#52) without contradiction in US2 wording? [Boundary, Spec §Out of Scope, US2 A3]
- [ ] CHK035 Is any remaining ambiguity about “texto consolidado” vs “último texto útil” resolved after clarify? [Ambiguity, Spec §FR-006]

## Notes

- This checklist tests **requirement quality**, not runtime behavior.
- Mark items during G2 / pre-implement review; do not convert into QA test scripts.
- Traceability: ≥80% of items reference Spec/Plan/Contract sections.
