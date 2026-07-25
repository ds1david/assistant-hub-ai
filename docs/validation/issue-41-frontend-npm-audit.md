# Validation evidence: frontend dependency audit / Vite major (issue #41)

**Feature**: `specs/018-issue-41-frontend-npm-audit`  
**Issue**: [#41](https://github.com/ds1david/assistant-hub-ai/issues/41)  
**Date**: 2026-07-25  
**Environment**: WSL/Linux, Node `v24.18.0`, cwd `apps/desktop-shell`  
**Baseline commit**: `89fe00d` (pre-upgrade pins)  
**Close commit**: _(fill on final commit / PR)_  

**Branch note**: “no-major-bump” in branch name = product-tag #39 policy (won’t major Vite in 0.2.0). **This slice (#41) prefers major** toolchain upgrade to clear the audit cluster (spec Q1).

---

## Baseline

**Commands**:

```bash
cd apps/desktop-shell
npm ci
npm audit
npm audit --omit=dev
```

**Summary counts** (pre-upgrade):

| Severity | Count |
|----------|------:|
| critical | 1 |
| high | 6 |
| moderate | 3 |
| low | 0 |
| **total** | **10** |

**prodOnlyClean**: `true` — `npm audit --omit=dev` → **0 vulnerabilities**.

### Findings

| packageName | severity | isDirect | role | fixRequiresMajor | fixAvailableVersion | notes / advisory |
|-------------|----------|----------|------|------------------|---------------------|------------------|
| vitest | critical | yes | `dev_ci` | yes | 4.1.10 | GHSA-5xrq-8626-4rwp (Vitest UI server); via vite chain |
| vite | high | yes | `dev_ci` | yes | 8.1.5 | GHSA-4w7w-66w2-5vf9, GHSA-v6wh-96g9-6wx3, GHSA-fx2h-pf6j-xcff + esbuild |
| esbuild | moderate | no | `dev_ci` | yes (via vite) | (via vite 8.1.5) | GHSA-67mh-4wv8-2f99 dev server |
| eslint | high | yes | `dev_ci` | yes | 10.8.0 | via minimatch / brace-expansion |
| minimatch | high | no | `dev_ci` | yes (via eslint) | (via eslint 10) | transitive |
| brace-expansion | high | no | `dev_ci` | yes (via eslint) | (via eslint 10) | GHSA-mh99-v99m-4gvg |
| @eslint/config-array | high | no | `dev_ci` | yes (via eslint) | (via eslint 10) | via minimatch |
| @eslint/eslintrc | high | no | `dev_ci` | yes (via eslint) | (via eslint 10) | via minimatch |
| @vitest/mocker | moderate | no | `dev_ci` | yes (via vitest) | (via vitest 4) | via vite |
| vite-node | moderate | no | `dev_ci` | yes (via vitest) | (via vitest 4) | via vite |

**Classification note**: Entire cluster is toolchain (build/test/lint). Production dependency `@tauri-apps/api` not in report; `npm audit --omit=dev` clean → no `runtime_packaged` high/critical at baseline.

---

## Disposition

| Family / package | Action | From → To | Justification |
|------------------|--------|-----------|---------------|
| vite + esbuild + vite-node + @vitest/mocker | `upgraded` | vite 5.4.x → **8.1.5** | Major preferred to clear advisory cluster (research Decision 2) |
| vitest | `upgraded` | 2.1.x → **4.1.10** | Peer-aligned with Vite 6/7/8 |
| eslint + minimatch + brace-expansion + @eslint/* | `upgraded` | eslint 9.x → **10.8.0**; `@eslint/js` → **10.0.1** | Clears brace-expansion/minimatch high |
| typescript-eslint | `upgraded` | 8.46.x → **8.65.x** | Peer supports eslint 10 |
| @tauri-apps/api | not_applicable | unchanged | Prod dep; not in audit cluster |

**Config adaptation (minimal)**:

- `vite.config.ts`: `defineConfig` from `vitest/config` (Vite 8 + Vitest 4); preserved `clearScreen: false`, port `5173`, `strictPort`, `outDir: dist`
- `package.json` lint script: `eslint src tests` (flat config; drop `--ext .ts`)

**Force audit**: not used (`npm audit fix --force` avoided).

---

## Reaudit

**Commands** (post-upgrade):

```bash
cd apps/desktop-shell
npm audit
npm audit --omit=dev
```

| Check | Result |
|-------|--------|
| `npm audit` | **0 vulnerabilities** |
| `npm audit --omit=dev` | **0 vulnerabilities** |
| Installed pins | vite@8.1.5, vitest@4.1.10, eslint@10.8.0 |

---

## Verification

| Check | Result | Notes |
|-------|--------|-------|
| `npm test` | **pass** | 4 files / 20 tests (vitest 4.1.10) |
| `npm run build` | **pass** | tsc -b + vite 8.1.5 build |
| `npm run lint` | **pass** | eslint 10.8.0 flat config |
| CI `desktop-shell-smoke` | pending push | Job exists; `npm run lint` added to workflow (local DoD complete). Never invent PASS for remote until PR green |
| `cargo test` (src-tauri) | **pass** | Local: agent_control + ai_provider + session_core client suites green |

---

## Residual

**None.** Reaudit clean in full and prod-only scopes.

---

## Close readiness

- [x] SC-003 — test / build / lint pass; recorded above  
- [x] SC-005 — major documented (vite 8, vitest 4, eslint 10) in Disposition  
- [x] SC-006 — no domain features; only package pins, lockfile, vite config import, lint script, docs, CI lint step  
- [x] SC-007 — no high/critical runtime residual; report clean  
- [x] SC-008 — N/A (no residual items)  
- [x] Issue #41 ready for **human** close after merge (P8 — do not auto-close)

**PR body should link**: `docs/validation/issue-41-frontend-npm-audit.md`  
**PR note**: Branch name is historical (no Vite major in product tag #39); this PR major-bumps Vite/Vitest/ESLint per #41.
