# Release checklist template — Assistant Hub AI

Copy to `docs/release/checklist-<VERSION>.md` and fill before tagging.

Contract: `specs/016-issue-39-release-hardening/contracts/release-process.md`

---

## 1. Metadata

| Field | Value |
|-------|-------|
| Version (SemVer) | _TBD_ |
| Target commit SHA (`main`) | _fill after merge_ |
| Date | _YYYY-MM-DD_ |
| Maintainer | _name_ |
| Issue | #39 |

---

## 2. CI (strict green)

On the **release commit on `main`**: every job that **exists** must be **green**.  
Job **absent** → status `absent` / “sem job” — **never** treat as pass.  
Any **red** → **tag forbidden**.

| Job ID | Exists | Status (`green` / `red` / `absent`) | Evidence (Actions run URL or SHA+date) |
|--------|--------|--------------------------------------|----------------------------------------|
| `policy` | yes | | |
| `java` | yes | | |
| `transcription-python` | yes | | |
| `windows-audio-agent-unit` | yes | | |
| `windows-audio-agent-windows-smoke` | yes | | |
| `compose` | yes | | |
| `desktop-shell-smoke` | yes | | |

---

## 3. Version audit

Run from repo root:

```bash
./scripts/release/check-version.sh
```

Must exit **0**. Consistency points:

| Point | Path / pattern |
|-------|----------------|
| Source of truth | `VERSION` |
| README | `README.md` → `## Versão X.Y.Z` |
| Transcription service | `services/transcription-service/app/main.py` → FastAPI `version=` |
| Agent package | `agents/windows-audio-agent/pyproject.toml` → `version=` |
| Agent CLI | `agents/windows-audio-agent/src/assistant_hub_audio/__init__.py` → `__version__` |
| CI assert (if literal) | `.github/workflows/ci.yml` → `app.version == '…'` |

| Check | Result |
|-------|--------|
| `check-version.sh` | _pass / fail_ |
| Notes | |

---

## 4. Gaps (no invented PASS)

**Policy**: status is only `gap` | `pass` | `n-a`.  
Mark `pass` **only** with a real evidence file under `docs/validation/` (or equivalent) that documents environment, commit, steps, and result.  
**Never** invent PASS for unrun hardware/GUI validation.

| ID | Description | Status | Evidence path | Notes |
|----|-------------|--------|---------------|-------|
| `SF-020-T024` | Process-capture manual Windows validation (specs/009 T024) | `gap` | _(none until `docs/validation/sf-020-windows.md`)_ | Expected gap until host Windows build ≥ 20348 validation exists |
| `DESKTOP-T033` | Desktop shell manual Windows/GUI validation (specs/014 T033) | `gap` | _(none until docs/validation entry)_ | Expected gap until WebView2 reference machine validation exists |

Add other known gaps as rows; same rules.

---

## 5. Debts (list + issue or won’t-fix)

Each debt **must** have a GitHub issue URL **or** an explicit **accepted won’t-fix for this tag** rationale.

| ID | Summary | Tracking | Issue URL / won’t-fix rationale |
|----|---------|----------|----------------------------------|
| `InvocationResult-sourceType` | Consistency/typing of `sourceType` on provider `InvocationResult` | `issue` | _link_ |
| `frontend-vite-audit` | npm audit / Vite major upgrade | `issue` or `wontfix-this-tag` | _link or rationale (no major Vite bump this tag — FR-012)_ |

---

## 6. Hygiene

| Check | Result |
|-------|--------|
| `.gitignore` covers Memory Hub db paths | |
| `git ls-files` has no `memory-hub.db` / session-core `*.db` | |
| No secrets / `config/ai-providers.yaml` committed | |

```bash
git ls-files '*.db' '**/memory-hub.db' || true
git check-ignore -v data/session-core/memory-hub.db services/session-core/data/memory-hub.db 2>/dev/null || true
```

---

## 7. Min-flow docs

| Artifact | Present / link |
|----------|----------------|
| README entry “Fluxo mínimo (release)” | `README.md` |
| Detail guide | `docs/release/min-flow.md` |
| Three pillars required (WSL + Windows agent + desktop) | yes / no |

---

## 8. Tag sequence (human gate)

1. Hardening + version bump + docs merged to **`main`** (human merge).  
2. All existing in-scope CI jobs **green** on that `main` commit.  
3. This checklist **Ready for tag = YES**.  
4. Human: annotated tag `v` + contents of `VERSION` on that SHA; push tag.  
5. Optional: GitHub Release body = `CHANGELOG.md` section.

**Forbidden**: tag only on feature/release branch before `main`; automated merge/tag without human gate.

See also: `CHANGELOG.md`, `specs/016-issue-39-release-hardening/contracts/release-process.md`.

---

## 9. Ready for tag

| Question | Answer |
|----------|--------|
| Ready for tag? | **YES** / **NO** |
| Blockers | |

Ready only if: CI green (or absent documented), version check pass, gaps honest, debts tracked, hygiene OK, min-flow docs linked, SHA on `main` recorded.
