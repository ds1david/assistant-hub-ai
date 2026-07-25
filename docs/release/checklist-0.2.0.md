# Release checklist — 0.2.0

Filled for issue #39 (release hardening pós R1–R6).  
Template: [checklist-template.md](./checklist-template.md)

---

## 1. Metadata

| Field | Value |
|-------|-------|
| Version (SemVer) | `0.2.0` |
| Target commit SHA (`main`) | _fill after merge to main_ |
| Date | 2026-07-25 |
| Maintainer | release hardening (issue #39) |
| Issue | #39 |

---

## 2. CI (strict green)

| Job ID | Exists | Status | Evidence |
|--------|--------|--------|----------|
| `policy` | yes | _pending main_ | fill Actions URL after merge |
| `java` | yes | _pending main_ | |
| `transcription-python` | yes | _pending main_ | |
| `windows-audio-agent-unit` | yes | _pending main_ | |
| `windows-audio-agent-windows-smoke` | yes | _pending main_ | |
| `compose` | yes | _pending main_ | |
| `desktop-shell-smoke` | yes | _pending main_ | new job this release |

---

## 3. Version audit

```bash
./scripts/release/check-version.sh
```

| Check | Result |
|-------|--------|
| `check-version.sh` | **pass** on feature branch after bump to 0.2.0 |
| Notes | Points: `VERSION`, README `## Versão`, FastAPI, agent pyproject + `__init__`, CI assert |

---

## 4. Gaps (no invented PASS)

| ID | Description | Status | Evidence path | Notes |
|----|-------------|--------|---------------|-------|
| `SF-020-T024` | Process-capture manual Windows (specs/009 T024) | **gap** | _(none)_ | Do not invent PASS |
| `DESKTOP-T033` | Desktop GUI Windows validation (specs/014 T033) | **gap** | _(none)_ | Do not invent PASS |

---

## 5. Debts

| ID | Summary | Tracking | Issue / won’t-fix |
|----|---------|----------|---------------------|
| `InvocationResult-sourceType` | `sourceType` / InvocationResult consistency | `issue` | https://github.com/ds1david/assistant-hub-ai/issues/40 |
| `frontend-vite-audit` | npm audit / Vite major | `issue` + won’t major this tag | https://github.com/ds1david/assistant-hub-ai/issues/41 — no Vite major bump in 0.2.0 |

---

## 6. Hygiene

| Check | Result |
|-------|--------|
| `.gitignore` Memory Hub paths | **yes** (root + module + `**/memory-hub.db`) |
| No tracked memory-hub db | **yes** (`git ls-files` empty for those) |
| `config/ai-providers.yaml` not committed | **yes** (gitignored) |

---

## 7. Min-flow docs

| Artifact | Present |
|----------|---------|
| README “Fluxo mínimo (release)” | yes |
| `docs/release/min-flow.md` | yes |
| Three pillars required | yes |

---

## 8. Tag sequence

See template §8. Tag `v0.2.0` only after merge to `main` + CI green + Ready YES.

---

## 9. Ready for tag

| Question | Answer |
|----------|--------|
| Ready for tag? | **NO** — wait for human merge to `main`, green CI on that SHA, then set YES |
| Blockers | Merge + CI evidence on `main`; then human `git tag -a v0.2.0` + push |
