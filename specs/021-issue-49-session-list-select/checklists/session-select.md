# Session Selection Requirements Checklist: Sessão — seleção na lista e alinhar agent

**Purpose**: Unit tests for English — validate quality, clarity, and completeness of session-selection and agent-alignment requirements before implement  
**Created**: 2026-07-25  
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

**Depth**: Standard  
**Audience**: Author + PR reviewer (G1/G2)  
**Focus**: Selection reliability, create→active, refresh/orphan, list vs STT-only ids, agent id linkage, docs

## Requirement Completeness

- [ ] CHK001 Are requirements defined for selecting an existing session from the list (not only create)? [Completeness, Spec §US1, §FR-001]
- [ ] CHK002 Are requirements defined for create-session automatically becoming active? [Completeness, Spec §US2, §FR-005]
- [ ] CHK003 Are requirements defined for list refresh preserving vs clearing active session? [Completeness, Spec §FR-006]
- [ ] CHK004 Are requirements defined for agent start/restart using the active session id? [Completeness, Spec §US3, §FR-008–FR-010]
- [ ] CHK005 Are documentation requirements explicit for list-sessions vs agent-only session strings? [Completeness, Spec §US4, §FR-014]
- [ ] CHK006 Is out-of-scope stated for accepting STT-only ids in list-sessions without core create? [Completeness, Spec §Out of Scope, §FR-015]

## Requirement Clarity

- [ ] CHK007 Is “identificador completo” / full active id display unambiguous for acceptance tests? [Clarity, Spec §FR-002, clarify]
- [ ] CHK008 Is orphan-after-refresh behavior quantified as active → null (not vague “invalid”)? [Clarity, Spec §FR-006, clarify]
- [ ] CHK009 Is “no auto-select first item” stated as a hard rule (not implied)? [Clarity, Spec §FR-001, clarify]
- [ ] CHK010 Is list-item truncation vs full id on active label distinguished clearly? [Clarity, Spec §FR-002, clarify]
- [ ] CHK011 Is “list-sessions only reflects session-core” free of synonyms that could mean STT path ids? [Clarity, Spec §FR-007, §US4]

## Requirement Consistency

- [ ] CHK012 Do selection requirements stay consistent with 020 (select must not restart agent)? [Consistency, Spec §FR-011, §Assumptions, 020 FR-009]
- [ ] CHK013 Do agent start requirements stay compatible with 020 Direct/Guided and mismatch rules? [Consistency, Spec §US3, §FR-008–FR-012]
- [ ] CHK014 Do docs requirements align between FR-014 and Success Criteria SC-006? [Consistency, Spec §FR-014, §SC-006]
- [ ] CHK015 Are FR-013 automated coverage items aligned with SC-001–SC-005? [Consistency, Spec §FR-013, §Success Criteria]

## Acceptance Criteria Quality

- [ ] CHK016 Can SC-001 (select never leaves “none selected”) be objectively verified in automated tests? [Measurability, Spec §SC-001]
- [ ] CHK017 Can SC-003 (preserve vs orphan) be verified with pure reconcile fixtures without hardware? [Measurability, Spec §SC-003, P10]
- [ ] CHK018 Can SC-004 (start uses exact active id, not session-YYYYMMDD) be asserted with fakes? [Measurability, Spec §SC-004]
- [ ] CHK019 Are US1–US2 acceptance scenarios written as Given/When/Then with observable UI state? [Acceptance Criteria, Spec §US1–US2]

## Scenario & Edge Case Coverage

- [ ] CHK020 Are empty-list + create flows covered in requirements? [Coverage, Spec §US2]
- [ ] CHK021 Are dual-session switch scenarios covered? [Coverage, Spec §US1 scenario 3]
- [ ] CHK022 Are requirements defined for blank/malformed session ids on list items? [Edge Case, Spec §Edge Cases]
- [ ] CHK023 Are requirements defined for bootstrap with populated list and no active session? [Edge Case, Spec §Edge Cases, clarify]
- [ ] CHK024 Are requirements defined for list failure (core down) vs successful orphan clear? [Coverage, Spec §US2 scenario 2, data-model refresh_fail]
- [ ] CHK025 Are requirements defined for agent path id `session-YYYYMMDD-…` not appearing in list? [Coverage, Spec §FR-007, §Edge Cases]

## Dependencies & Assumptions

- [ ] CHK026 Is dependency on 019/020 for Assistente and mismatch surfaces documented without re-specifying full 020? [Dependency, Spec §Dependencies, §Assumptions]
- [ ] CHK027 Is “no cross-restart persistence of activeSessionId” documented as intentional assumption? [Assumption, Spec §Assumptions, clarify]
- [ ] CHK028 Is “any list status selectable” consistent across FR-001 and edge cases? [Consistency, Spec §FR-001, clarify]

## Ambiguities & Conflicts

- [ ] CHK029 Does the spec avoid conflicting “keep invalid active” vs “clear orphan” language? [Conflict check, Spec §FR-006]
- [ ] CHK030 Is overlap with 020 framed as compatible reuse rather than duplicate conflicting FRs? [Ambiguity, Spec §Assumptions]

## Notes

- Check items off when reviewing the **written requirements**, not the code.
- Traceability target: ≥80% of items reference Spec § / Gap / Assumption (this list meets that).
- Depth: Standard G1 gate companion to `requirements.md` (content quality) — this file is domain-focused (session select).
