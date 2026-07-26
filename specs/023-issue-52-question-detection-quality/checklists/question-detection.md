# Question Detection Requirements Checklist: Qualidade de detecção de pergunta (issue #52)

**Purpose**: Validar qualidade, clareza e completude dos requisitos de detecção de pergunta (lexical, modo entrevista, gate multimodal, prosódia, ops STT e superfície de resposta) antes da implementação  
**Created**: 2026-07-25  
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [tasks.md](../tasks.md)

**Depth**: Standard  
**Audience**: Reviewer (PR) / Author  
**Focus**: Completeness, clarity, consistency, edge coverage, privacy, deliverability (Phase A vs C)

## Requirement Completeness

- [ ] CHK001 Are response-surface requirements explicit that the model answer appears only in the shell Assistente panel? [Completeness, Spec §FR-001]
- [ ] CHK002 Are lexical question rules complete for interview imperatives (pt/en), vocative, and post-sentence starts? [Completeness, Spec §FR-002]
- [ ] CHK003 Are word-boundary / false-positive rejection rules specified (e.g. `qualidade` vs `qual`)? [Completeness, Spec §FR-002]
- [ ] CHK004 Are Final-only and enabled-origin gates documented as mandatory preconditions? [Completeness, Spec §FR-003]
- [ ] CHK005 Are interview-mode rules complete for system-only expansion and min length? [Completeness, Spec §FR-004]
- [ ] CHK006 Are all new preference fields and defaults listed (`interviewMode`, `useProsody`, `prosodyThreshold`)? [Completeness, Spec §FR-005]
- [ ] CHK007 Is the multimodal candidate formula fully specified (OR of lexical / interview / prosody)? [Completeness, Spec §FR-006]
- [ ] CHK008 Are optional `prosody` fields and privacy constraints (no PCM) defined for the transcript final event? [Completeness, Spec §FR-007]
- [ ] CHK009 Is the prosody extraction source (transcription service, not capture agent) stated as a requirement? [Completeness, Spec §FR-008, Clarify]
- [ ] CHK010 Are STT model upgrade and hotwords operational requirements documented without changing product defaults? [Completeness, Spec §FR-009]

## Requirement Clarity

- [ ] CHK011 Is minimum text length for candidates quantified (not “short” / “long”)? [Clarity, Spec §FR-002/FR-004]
- [ ] CHK012 Is `prosodyThreshold` default and UI policy unambiguous (store 0.65, no dedicated UI control in v1)? [Clarity, Spec §FR-005, Clarify]
- [ ] CHK013 Is empty-state copy policy clear (single generic eligibility message vs multiple reasons)? [Clarity, Spec §US2/US6, Clarify]
- [ ] CHK014 Is “canonical source type system” distinguished from profile labels (conference cam)? [Clarity, Spec §Assumptions]
- [ ] CHK015 Can “does not increase UI latency perceptibly” for lexical/interview be treated as non-blocking CPU work vs hard ms SLA? [Clarity, Spec §NFR-001]

## Requirement Consistency

- [ ] CHK016 Do FR-002 and 019 FR-004 relationship notes agree (shell supersession without full 019 rewrite)? [Consistency, Spec §FR-002]
- [ ] CHK017 Do FR-006, research truth table, and contract `isQuestionCandidate` agree on operator precedence? [Consistency, Spec §FR-006, research R7]
- [x] CHK018 Do FR-008 and the product clarifications table agree on prosody extraction location (STT only)? [Consistency — remediated analyze 2026-07-25]
- [ ] CHK019 Do Phase A ship-alone assumptions match Out of Scope (prosody optional, auto remains off)? [Consistency, Spec §Assumptions / Out of Scope]
- [ ] CHK020 Are SC-001…SC-006 aligned with acceptance scenarios of US1–US6 without contradictory targets? [Consistency, Spec §Success Criteria]

## Acceptance Criteria Quality

- [ ] CHK021 Can SC-001 be verified with automated heuristic fixtures alone? [Measurability, Spec §SC-001]
- [ ] CHK022 Can SC-002 be verified via manual quickstart with a time bound (< 30s after eligible final)? [Measurability, Spec §SC-002]
- [ ] CHK023 Does SC-003 distinguish system vs microphone under interview mode with objective outcomes? [Measurability, Spec §SC-003]
- [ ] CHK024 Does SC-004 define both absence-of-prosody validity and threshold-respecting behavior? [Measurability, Spec §SC-004]
- [ ] CHK025 Is SC-005 documentation-checkable (grep / quickstart section exists)? [Measurability, Spec §SC-005]

## Scenario & Edge Coverage

- [ ] CHK026 Are Partial-vs-Final requirements covered for interrogative text? [Coverage, Spec §Edge Cases]
- [ ] CHK027 Are busy-orchestrator conflict requirements inherited/referenced from 019? [Coverage, Spec §Edge Cases]
- [ ] CHK028 Are sessionId mismatch non-regression requirements present (020/021/022)? [Coverage, Spec §FR-012]
- [ ] CHK029 Is prosody extractor failure (omit field, never drop final) required? [Coverage, Spec §FR-008 / Edge Cases]
- [ ] CHK030 Are multi-sentence Final start-candidates (after `.` / `!`) required? [Coverage, Spec §FR-002 / Edge Cases]
- [ ] CHK031 Are noisy ASR / jargon failure modes addressed (ops STT, not fuzzy matching)? [Coverage, Spec §Edge Cases / US4]

## Non-Functional & Privacy

- [ ] CHK032 Are privacy requirements explicit for tokens, PCM, and full transcript logging? [Completeness, Spec §FR-010 / P9]
- [ ] CHK033 Is prosody CPU budget either quantified or explicitly flag-gated when exceeded? [Clarity, Spec §NFR-002]
- [ ] CHK034 Are additive-contract compatibility expectations stated for clients ignoring `prosody`? [Completeness, Spec §NFR-003]
- [ ] CHK035 Is CI constraint “no GPU / no real WASAPI” reflected in test requirements? [Completeness, Spec §FR-011 / P10]

## Dependencies & Assumptions

- [ ] CHK036 Is dependency on a configured live-answer provider scoped to SC-002 (not detection itself)? [Assumption, Spec §Assumptions]
- [ ] CHK037 Is assumption that remote interviewer audio maps to `sourceType=system` documented? [Assumption, Spec §Assumptions]
- [ ] CHK038 Are out-of-scope items (STT chat UI, AEC, neural speech-act, auto default on) explicit? [Completeness, Spec §Out of Scope]
- [ ] CHK039 Is Phase A independently deliverable without Phase C required for MVP? [Completeness, Spec Clarify / plan]

## Ambiguities & Conflicts

- [ ] CHK040 Is schema strategy free of ambiguity (v2 in-place vs v2.1 dual-read fallback)? [Ambiguity, Spec §FR-007 / research R5]
- [x] CHK041 Does any remaining text still claim prosody is extracted on the Windows agent? [Conflict — remediated analyze 2026-07-25; residual only as explicit MUST NOT]
- [ ] CHK042 Are hotwords path and model env names treated as operational documentation rather than hard product defaults? [Clarity, Spec §FR-009]

## Notes

- Check items off when the **requirements text** satisfies the question — not when code is implemented.
- Prefer fixing the spec/plan over “implementing around” vague requirements.
- Traceability: ≥80% of items reference Spec/Clarify/research sections.
