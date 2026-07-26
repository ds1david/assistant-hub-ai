# Release checklist — 0.2.0

Filled for issue #39 (release hardening pós R1–R6).  
Template: [checklist-template.md](./checklist-template.md)

**Atualizado em 2026-07-26** após merges #57 (R5 sidecar) e #58 (R6 breaker/stream) em `main`.

---

## 1. Metadata

| Field | Value |
|-------|-------|
| Version (SemVer) | `0.2.0` |
| Target commit SHA (`main`) | `adc1a4c37363085ce9712dee7d320d9be1ab2521` |
| Date | 2026-07-26 |
| Maintainer | release hardening (issue #39) + post-#58 audit |
| Issue | #39 |

---

## 2. CI (strict green)

| Job ID | Exists | Status | Evidence |
|--------|--------|--------|----------|
| `policy` | yes | _confirm on Actions for `adc1a4c`_ | https://github.com/ds1david/assistant-hub-ai/actions |
| `java` | yes | _confirm on Actions_ | |
| `transcription-python` | yes | _confirm on Actions_ | |
| `windows-audio-agent-unit` | yes | _confirm on Actions_ | |
| `windows-audio-agent-windows-smoke` | yes | _confirm on Actions_ | |
| `compose` | yes | _confirm on Actions_ | |
| `desktop-shell-smoke` | yes | _confirm on Actions_ | |

Local smoke (2026-07-26): `check-version.sh` pass; `session-core` subset breaker/stream + `SessionRepositoryTest` pass; `cargo test --lib` desktop-shell 37 pass.

---

## 3. Version audit

```bash
./scripts/release/check-version.sh
```

| Check | Result |
|-------|--------|
| `check-version.sh` | **pass** on `main` @ `adc1a4c` |
| Notes | `VERSION`, README, FastAPI, agent pyproject + `__init__`, CI assert all `0.2.0` |

---

## 4. Gaps (no invented PASS)

| ID | Description | Status | Evidence path | Notes |
|----|-------------|--------|---------------|-------|
| `SF-020-T024` | Process-capture manual Windows | **gap** | _(none)_ | specs/009-sf-020 T024 |
| `DESKTOP-T033` | Desktop GUI Windows validation | **gap** | _(none)_ | specs/014 T033/T037 |
| `R5-SIDECAR-VAL` | Sidecar packaging Windows | **gap** | `docs/validation/r5-audio-agent-sidecar.md` template only | specs/025 residual |
| `SF-015-HW` | Hardware matrix residual | **gap** | docs/validation/sf-015-* partial | Bluetooth BLOCKED; reboot/hot-plug cases open |
| `SF-018/019-MANUAL` | Windows revalidation hot-plug | **gap** | docs/validation partial | 006 T033, 009/010 reval |
| `TAG-v0.2.0` | Annotated tag on main | **gap** | — | Human gate T021 |

---

## 5. Debts

| ID | Summary | Tracking | Issue / won’t-fix |
|----|---------|----------|---------------------|
| `InvocationResult-sourceType` | `sourceType` consistency | **resolved** in product | #40 merged |
| `frontend-vite-audit` | npm audit / Vite | **resolved** post-tag path | #41; evidence `docs/validation/issue-41-frontend-npm-audit.md` |
| `R5-remaining` | tray, secure store OS, signed update, diag GPU | open | specs/002 |
| `R6-remaining` | DPAPI, NIM presets, `/v1/models`, tokens/cost metrics, privacy-by-profile | open | specs/003 |
| `R3-plus` | semantic index, search, decisions/actions | open | roadmap R3 beyond #29 |
| `R4` | Visual context | open | no spec yet |
| `R7` | Ecosystem | open | no spec yet |

---

## 6. Hygiene

| Check | Result |
|-------|--------|
| `.gitignore` Memory Hub paths | **yes** |
| No tracked memory-hub db | **yes** |
| `config/ai-providers.yaml` not committed | **yes** |
| PRs #57 / #58 on main | **yes** |

---

## 7. Min-flow docs

| Artifact | Present |
|----------|---------|
| README “Fluxo mínimo (release)” | yes |
| `docs/release/min-flow.md` | yes |

---

## 8. Tag sequence

See template §8. Tag `v0.2.0` only after CI green on `adc1a4c` (or later main) + Ready YES.

```bash
git checkout main && git pull
./scripts/release/check-version.sh
# confirm CI green for adc1a4c
git tag -a v0.2.0 -m "Assistant Hub AI 0.2.0"
git push origin v0.2.0
```

---

## 9. Ready for tag

| Question | Answer |
|----------|--------|
| Ready for tag? | **NO** — confirm CI green on SHA + human tag; manual Windows gaps explicit (do not invent PASS) |
| Blockers | Actions green on `adc1a4c`; optional but recommended: record Actions URLs in §2; human tag T021 |
