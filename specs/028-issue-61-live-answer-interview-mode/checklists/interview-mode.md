# Interview Mode Requirements Checklist: Live-answer contexto + 1ª pessoa

**Purpose**: Unit tests for English — validate requirement quality for issue #61 (contexto misto, estilo entrevista, disparo≠contexto, latência docs)  
**Created**: 2026-07-26  
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)  
**Depth**: Standard  
**Audience**: Author + PR reviewer (G2)  
**Focus**: Contexto misto, estilo 1ª pessoa, preferências, latência/docs, limites de escopo

## Requirement Completeness

- [x] CHK001 Are requirements for mixed **context** (system + microphone finals) fully specified independently of **trigger** origins? [Completeness, Spec §Distinção, FR-001, FR-008]
- [x] CHK002 Is the session preference “include my voice in context” documented with default, persistence, and isolation rules? [Completeness, Spec §FR-004, FR-006, SC-008]
- [x] CHK003 Are canonical context labels specified as fixed product strings (not left open-ended)? [Completeness, Spec §FR-007, Clarify]
- [x] CHK004 Is interview-mode **style** (1st person, oral length, honesty) specified with testable instruction requirements? [Completeness, Spec §FR-009–011]
- [x] CHK005 Are prohibited meta-assistant patterns listed for automated style regression? [Completeness, Spec §FR-012]
- [x] CHK006 Are documentation requirements for latency chain links and interview ops knobs explicit? [Completeness, Spec §FR-014–015, US4]
- [x] CHK007 Is “answer surface = Assistente panel, not STT dashboard” required in docs? [Completeness, Spec §FR-018]

## Requirement Clarity

- [x] CHK008 Is “default ON” for include-mic-context unambiguous when the stored field is **missing** vs explicitly false? [Clarity, Spec §FR-004, data-model]
- [x] CHK009 Is the injection mechanism for interview style constrained (fixed input prefix vs hub system prompt)? [Clarity, Spec §FR-009, Clarify R4]
- [x] CHK010 Is runtime handling of model style violations unambiguous (display as-is vs reject)? [Clarity, Spec §FR-012b]
- [x] CHK011 Is FR-017 latency UI requirement clearly “preserve per-turn latencyMs” rather than inventing a new global metric? [Clarity, Spec §FR-017]
- [x] CHK012 Can “~30–90 seconds of oral reading” be validated without requiring wall-clock speech timing in CI? [Clarity/Measurability, Spec §FR-009, Assumption tests]

## Requirement Consistency

- [x] CHK013 Do requirements consistently keep `enabledSourceTypes` as **trigger-only** and never redefine it as context filter? [Consistency, Spec §FR-008, US1.4]
- [x] CHK014 Is `question-only` mode consistently exempt from mixed context and from include-mic preference effects? [Consistency, Spec §FR-003, US1.3]
- [x] CHK015 Does style requirement activate only with `interviewMode` while include-mic remains independent? [Consistency, Spec §FR-013, Edge Cases, Clarify]
- [x] CHK016 Are 019 window limits (segments/chars) still the governing limits without silent override? [Consistency, Spec §FR-001, research R8]

## Acceptance Criteria Quality

- [x] CHK017 Are SC-001/SC-002 objectively testable from built invoke input alone (no live LLM)? [Measurability, Spec §SC-001–002]
- [x] CHK018 Does SC-004 test instruction presence + detector fixtures rather than live model personality? [Measurability, Spec §SC-004, FR-012]
- [x] CHK019 Is non-trigger on microphone-only finals covered by both FR and SC with default origins? [Measurability, Spec §FR-008, SC-003]
- [x] CHK020 Is “no partial auto-invoke” regression covered by SC-006 and FR-016? [Measurability, Spec §SC-006]

## Scenario & Edge Case Coverage

- [x] CHK021 Are empty-mic and empty-system context scenarios defined? [Coverage, Spec §Edge Cases]
- [x] CHK022 Is unknown/non-canonical `sourceType` handling specified for **context** (omit)? [Coverage, Spec §FR-007b]
- [x] CHK023 Are interviewMode × includeMicrophoneInContext combinations covered? [Coverage, Spec §Edge Cases]
- [x] CHK024 Is out-of-scope list explicit for partial invoke, TTS, real stealth interview, STT rewrite? [Coverage, Spec §Out of Scope]

## Dependencies & Assumptions

- [x] CHK025 Is dependence on Final utterance emission (024) and existing Assistente (019/023) documented? [Dependency, Spec §Dependencies]
- [x] CHK026 Is the assumption that mic/system finals already carry canonical `sourceType` in the feed stated? [Assumption, Spec §Assumptions]
- [x] CHK027 Are P9 logging constraints restated for this feature’s responses? [Consistency, Spec §FR-020]

## Ambiguities & Conflicts

- [x] CHK028 Do any remaining “optional” FR items conflict with mandatory SC (e.g., latency UI)? [Conflict check, Spec §FR-017 vs SC]
- [x] CHK029 Is terminology consistent for preference name (`includeMicrophoneInContext` vs UI label)? [Terminology, Spec §Key Entities, contracts]
- [x] CHK030 After clarify, are open plan-only wording details (exact instruction prose) clearly deferred without blocking G2? [Ambiguity, research Open items]

## Notes

- Depth: Standard pre-implement gate (requirements quality, not runtime QA).
- Traceability: ≥80% items reference Spec § / Clarify / data-model / research.
- **2026-07-26 implement**: items marked complete after FR-003 align + full shell implementation (contexto misto, prefs, instrução 1ª pessoa, docs, vitest/cargo green).
