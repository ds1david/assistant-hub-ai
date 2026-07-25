# Changelog

All notable product releases of Assistant Hub AI are documented here.

Format: short human summary per SemVer tag. Gaps and debts stay explicit (no invented PASS).

---

## [0.2.0] - 2026-07-25

### Summary

Product consolidation tag **after R1–R6** (streaming foundation through AI Provider Hub on the monorepo). This release hardens **main** for auditability: version consistency, CI coverage (including desktop smoke), release checklist, minimum-flow docs (WSL + Windows agent + desktop), Memory Hub gitignore hygiene, and honest gap/debt tracking.

Not a new domain feature slice.

### Changed

- Monorepo version **0.2.0** (`VERSION` + README + transcription service + windows-audio-agent + CI assert)
- `scripts/release/bump-version.sh` also updates agent `__version__`
- CI: job `desktop-shell-smoke` (npm test/build + `cargo test` for desktop-shell lib; no MSI/tauri build)
- Docs: `docs/release/min-flow.md`, checklist template, README “Fluxo mínimo (release)”
- `.gitignore`: broader Memory Hub `*.db` paths

### Gaps (explicit — not PASS)

| ID | Status | Notes |
|----|--------|-------|
| `SF-020-T024` | **gap** | Process-capture manual Windows validation still pending (`docs/validation/sf-020-windows.md` not present with real PASS) |
| `DESKTOP-T033` | **gap** | Desktop shell manual Windows/GUI validation still pending |

### Known debts

| ID | Tracking |
|----|----------|
| `InvocationResult-sourceType` | [#40](https://github.com/ds1david/assistant-hub-ai/issues/40) |
| `frontend-vite-audit` | [#41](https://github.com/ds1david/assistant-hub-ai/issues/41) — **no Vite major bump in this tag** |

### Release process

- Checklist: `docs/release/checklist-0.2.0.md`
- Tag only on `main` after green CI + Ready for tag YES (human gate)
- Contract: `specs/016-issue-39-release-hardening/contracts/release-process.md`

---

## [0.1.8] - prior

Pre-hardening monorepo line (see git history / previous README). Tag history may include `v0.1.6`.
