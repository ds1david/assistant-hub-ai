# STT Header Requirements Checklist: sessionId e profile no Streaming Foundation

**Purpose**: Unit tests for English — validate quality, clarity, and completeness of STT header requirements before implement  
**Created**: 2026-07-25  
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

**Depth**: Standard  
**Audience**: Author + PR reviewer (G1/G2)  
**Focus**: Header visibility, copy, multi-session primary, profile note, URL base, channel non-pollution, docs

## Requirement Completeness

- [x] CHK001 Are requirements defined for showing sessionId in the STT dashboard header (not only connection status)? [Completeness, Spec §US1, §FR-001]
- [x] CHK002 Are requirements defined for copying the full primary sessionId? [Completeness, Spec §US2, §FR-003]
- [x] CHK003 Are requirements defined for default agent-origin profile **note** (FR-006) and MAY name only without schema (FR-005)? [Completeness, Spec §US3, §FR-005–FR-006, analyze U2]
- [x] CHK004 Are requirements defined for STT base URL in the header as **MUST** (not optional)? [Completeness, Spec §US4, §FR-011, analyze I1]
- [x] CHK005 Are documentation requirements explicit for header sessionId and copy vs PowerShell log? [Completeness, Spec §US4, §FR-012]
- [x] CHK006 Is out-of-scope stated for transcript-event.v2 changes, agent auto-align, and Assistente? [Completeness, Spec §Out of Scope, §FR-013]

## Requirement Clarity

- [x] CHK007 Is “sessionId completo” unambiguous for acceptance (no silent truncation of copy value)? [Clarity, Spec §FR-002, §FR-008]
- [x] CHK008 Is multi-session **primary** defined as most recently observed (not first-only or undefined)? [Clarity, Spec §FR-010, clarify]
- [x] CHK009 Is observation source limited to transcript feed `sessionId` (not browser URL invention)? [Clarity, Spec §FR-014, clarify]
- [x] CHK010 Is “profile note when unavailable” explicit that inventing a profile name is forbidden? [Clarity, Spec §FR-005–FR-006]
- [x] CHK011 Is empty/waiting state without fabricated id specified? [Clarity, Spec §FR-009, §US1 scenario 2]

## Requirement Consistency

- [x] CHK012 Do header-only requirements stay consistent with “do not pollute channel cards”? [Consistency, Spec §FR-007, §US3 scenario 3]
- [x] CHK013 Do FR-011 (URL base MUST) and US4/Key Entities agree after analyze (no «opcional» drift)? [Consistency, Spec §FR-011, §US4, §Key Entities, analyze I1]
- [x] CHK014 Do FR-010 multi rules and Copiar-primary rules stay aligned (count indicator)? [Consistency, Spec §FR-003, §FR-010, analyze A2]
- [x] CHK015 Are automated vs manual SC split documented (SC-001/SC-004 manual; structure/state pytest)? [Consistency, Spec §Success Criteria, §Assumptions, analyze C1]

## Acceptance Criteria Quality

- [x] CHK016 Can SC-001 (identify sessionId in header after first event) be verified without PowerShell logs? [Measurability, Spec §SC-001]
- [x] CHK017 Can SC-002 (copy exact primary) be verified with fakes or documented manual clipboard path? [Measurability, Spec §SC-002, clarify]
- [x] CHK018 Can SC-003 (long id layout ≥64 chars) be specified without vague “looks fine”? [Measurability, Spec §SC-003]
- [x] CHK019 Are US1–US2 acceptance scenarios written as Given/When/Then with observable header state? [Acceptance Criteria, Spec §US1–US2]

## Scenario & Edge Case Coverage

- [x] CHK020 Are empty-feed + connected status scenarios covered? [Coverage, Spec §US1 scenario 2, §FR-009]
- [x] CHK021 Are dual-session observation and primary flip covered? [Coverage, Spec §FR-010, Edge Cases]
- [x] CHK022 Are clipboard failure and manual selection fallback covered? [Edge Case, Spec §US2 scenario 3, §FR-004]
- [x] CHK023 Are blank/whitespace sessionId events excluded from becoming primary? [Edge Case, Spec §data-model Validation]
- [x] CHK024 Is page reload / no persistence of observed sessions acknowledged? [Coverage, Spec §data-model Transitions]
- [x] CHK025 Are long UUID and `session-YYYYMMDD-…` forms both in scope for layout? [Coverage, Spec §US1 scenario 3, §SC-003]

## Dependencies & Assumptions

- [x] CHK026 Is dependency on existing transcript feed (no new endpoint) documented? [Dependency, Spec §Assumptions, plan Decision 2]
- [x] CHK027 Is non-overlap with shell 020/021 framed as visibility-only (not auto-align)? [Assumption, Spec §Assumptions, §Out of Scope]
- [x] CHK028 Is “profile via new contract = future ADR” and “no mysterious source this slice” explicit? [Assumption, Spec §Assumptions, analyze U2]
- [x] CHK031 Is canonical policy module (`header_session_state.py`) vs JS mirror documented so implement does not dual-diverge? [Consistency, plan U1, research Decision 8]

## Ambiguities & Conflicts

- [x] CHK029 Does the spec avoid treating FR-011 as both optional and mandatory after analyze remediação? [Conflict check, Spec §FR-011, §Key Entities, analyze I1]
- [x] CHK030 Is multi-session UI resolved to primary + **count** («N sessões») not vague “lista ou destaque”? [Ambiguity, Spec §FR-010, analyze A2]
- [x] CHK032 Is FR-004 the single copy-feedback requirement (FR-015 retired/reserved)? [Consistency, Spec §FR-004, analyze D1]
- [x] CHK033 Are WebSocket reconnect (preserve state) vs page reload (clear) specified? [Coverage, Spec §Edge Cases, data-model, analyze A1]

## Notes

- Checklist type: requirements quality (not implementation QA).
- Traceability: ≥80% items reference Spec § / Gap / Assumption.
- Analyze remediação 2026-07-25 applied to spec/plan/tasks/data-model/contracts/quickstart.
