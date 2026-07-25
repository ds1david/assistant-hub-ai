# Contract: Release process (monorepo product tag)

**Feature**: `specs/016-issue-39-release-hardening`  
**Version**: 1  
**Kind**: process / maintainer contract (not a runtime API)

This document is the stable interface between maintainers and the repository for a product SemVer tag after R1–R6 hardening.

---

## 1. Version consistency

| Obligation | Interface |
|------------|-----------|
| Single source of truth | File `VERSION` at repo root (SemVer `X.Y.Z`) |
| Propagate | `./scripts/release/bump-version.sh <semver>` MUST update all points consumed by the checker, including agent `__version__` after this feature |
| Verify | `./scripts/release/check-version.sh` MUST exit 0 on the release commit |
| Tag name | Git tag `v` + contents of `VERSION` (e.g. `v0.2.0`) |

---

## 2. CI gate (strict green)

On the **release commit on `main`**:

| Job ID | Required if present |
|--------|---------------------|
| `policy` | green |
| `java` | green |
| `transcription-python` | green |
| `windows-audio-agent-unit` | green |
| `windows-audio-agent-windows-smoke` | green |
| `compose` | green |
| `desktop-shell-smoke` | green if job exists |

**Rules**:
- Failing job ⇒ tag forbidden.
- Missing job ⇒ checklist records `status: absent` / “sem job”; not a pass.
- This feature adds `desktop-shell-smoke` (Node test/build + `cargo test` for `src-tauri` on Ubuntu). Once present, it is required green.

---

## 3. Checklist file schema (markdown)

Path: `docs/release/checklist-<VERSION>.md`

Required sections (headings):

1. **Metadata** — version, target commit SHA (filled after merge), date, maintainer  
2. **CI** — table: job id | exists | status | evidence link  
3. **Version** — output summary of `check-version.sh`  
4. **Gaps** — table: id | status (`gap`/`pass`/`n-a`) | evidence path | notes  
5. **Debts** — table: id | summary | issue URL or won’t-fix rationale  
6. **Hygiene** — memory-hub gitignore; `git ls-files` check for `*.db`  
7. **Min-flow docs** — links to README + `docs/release/min-flow.md`  
8. **Ready for tag** — explicit YES/NO  

Minimum gap rows: `SF-020-T024`, `DESKTOP-T033`.  
Minimum debt rows: `InvocationResult-sourceType`, `frontend-vite-audit`.

Template: `docs/release/checklist-template.md`.

---

## 4. Changelog

Path: `CHANGELOG.md` (repo root).

For each tagged version, a section:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Summary
…

### Gaps
- …

### Known debts
- … (#issue)
```

Must not claim PASS for open validation gaps.

---

## 5. Tag publication sequence

```text
1. Hardening + version bump + docs merged to main (human merge)
2. All existing in-scope CI jobs green on that main commit
3. Checklist file complete with Ready for tag = YES
4. Human: git tag -a vX.Y.Z <main-sha> && git push origin vX.Y.Z
5. Optional: GitHub Release from tag body = changelog section
```

**Forbidden**:
- Tag only on feature/release branch before main merge  
- Automated merge/tag without human gate  
- Invented PASS in gaps section  

---

## 6. Minimum flow documentation contract

Consumers: a developer following only README + linked ops.

MUST document three pillars and verification criteria:

| Pillar | Verify (examples) |
|--------|-------------------|
| WSL stack | Compose/STT up; session-core health UP |
| Windows agent | Process running; connected to STT endpoint |
| Desktop shell | Window/UI up; session and/or agent panel reflects live stack |

Providers config path and secrets policy MUST be linked (`samples/ai-providers/`, `docs/security/provider-secrets.md`).

Incomplete environment ⇒ document block; MUST NOT claim full min-flow success.

---

## 7. Out of contract

- Domain feature behavior (audio, STT, memory, providers beyond docs)  
- Vite major upgrade  
- Closing hardware validation gaps  
- Signed installers / auto-update channels  
