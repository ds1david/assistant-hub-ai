# Data Model: Release Hardening e tag de produto

**Feature**: `specs/016-issue-39-release-hardening`  
**Date**: 2026-07-25  

Modelo de **artefatos de release e evidência** (não domínio de sessão/áudio). Persistência = arquivos versionados no monorepo + tag Git remota.

---

## Entities

### ProductVersion

| Field | Type | Rules |
|-------|------|--------|
| `semver` | string | `MAJOR.MINOR.PATCH` (0.x); fonte de verdade: arquivo `VERSION` |
| `tagName` | string | `v` + `semver` (ex.: `v0.2.0`) |
| `commitSha` | string | SHA em `main` no momento da tag |
| `consistencyPoints` | list | README `## Versão`, transcription `app.version`, agent `pyproject` + `__version__`, CI assert se literal |

**Validation**: `./scripts/release/check-version.sh` exit 0.  
**Lifecycle**: draft (bump local) → merged to `main` → tagged.

---

### ReleaseChecklist

| Field | Type | Rules |
|-------|------|--------|
| `version` | ProductVersion.semver | Identifica o marco |
| `path` | path | `docs/release/checklist-<version>.md` |
| `ciJobs[]` | CiJobStatus | Um por job no escopo (ver abaixo) |
| `gaps[]` | ValidationGap | Inclui no mínimo SF-020 T024 e Desktop T033 |
| `debts[]` | TechnicalDebtRecord | Inclui sourceType/InvocationResult e Vite/npm audit |
| `hygiene` | object | gitignore memory-hub; sem `.db` trackeado |
| `minFlowDoc` | link | README + `docs/release/min-flow.md` |
| `filledAt` / `filledBy` | metadata | Opcional; humano |
| `readyForTag` | boolean | true só se todos os itens obrigatórios OK (CI existentes verdes; gaps/debts registrados; versão consistente; checklist 100% preenchido) |

**States**: `empty-template` → `in-progress` → `complete` → `superseded` (próxima versão).

---

### CiJobStatus

| Field | Type | Rules |
|-------|------|--------|
| `jobId` | string | Nome do job no workflow (`policy`, `java`, …) |
| `exists` | boolean | Job presente no YAML |
| `status` | enum | `green` \| `red` \| `absent` |
| `evidence` | string | Link Actions run ou SHA + data |
| `notes` | string | Se `absent` → texto “sem job” (nunca `green`) |

**Rule**: `red` ⇒ `readyForTag = false`. `absent` ⇒ documentado, não bloqueia por falha, mas não conta como pass.

Jobs esperados (research Decision 3): `policy`, `java`, `transcription-python`, `windows-audio-agent-unit`, `windows-audio-agent-windows-smoke`, `compose`, `desktop-shell-smoke` (novo).

---

### ValidationGap

| Field | Type | Rules |
|-------|------|--------|
| `id` | string | Ex.: `SF-020-T024`, `DESKTOP-T033` |
| `description` | string | O que falta provar |
| `evidencePath` | path \| null | `docs/validation/...` se existir |
| `status` | enum | `gap` \| `pass` \| `not-applicable` |
| `inventedPassForbidden` | const true | Nunca marcar `pass` sem arquivo de evidência real |

**Minimum set for this release**:
1. SF-020 Windows manual (T024) — esperado `gap` até `docs/validation/sf-020-windows.md` existir com PASS real.
2. Desktop manual Windows (T033) — esperado `gap` até validação GUI registrada.

---

### TechnicalDebtRecord

| Field | Type | Rules |
|-------|------|--------|
| `id` | string | Curto, estável |
| `summary` | string | Uma linha |
| `tracking` | enum | `issue` \| `wontfix-this-tag` |
| `issueUrl` \| `issueNumber` | string/int | Obrigatório se `tracking=issue` |
| `wontfixRationale` | string | Obrigatório se `wontfix-this-tag` |
| `inChangelog` | boolean | true |

**Minimum set**:
1. Consistência/`sourceType` em resultados de invocação (`InvocationResult`).
2. npm audit / Vite major (won’t major bump this tag + issue ou won’t-fix justificado).

---

### ChangelogEntry

| Field | Type | Rules |
|-------|------|--------|
| `version` | string | SemVer |
| `date` | date | ISO ou YYYY-MM-DD |
| `summary` | markdown | Curto: consolidação R1–R6 |
| `added` / `changed` / `fixed` | lists | Opcional Keep a Changelog |
| `gaps` | list | Links/ids dos ValidationGap |
| `debts` | list | Links TechnicalDebtRecord |

**Storage**: seção em `CHANGELOG.md` (mais recente no topo).

---

### MinimumFlowGuide

| Field | Type | Rules |
|-------|------|--------|
| `entryPoint` | path | `README.md` |
| `detailPath` | path | `docs/release/min-flow.md` |
| `pillars` | list | `wsl`, `windows-agent`, `desktop` — **todos** obrigatórios para aceite SC-004 |
| `providers` | section | Config `ai-providers` documentada |
| `verifyCriteria[]` | string | Health/status por pilar |

Não é entidade runtime — é documentação estruturada.

---

### ProductTag (Git)

| Field | Type | Rules |
|-------|------|--------|
| `name` | string | `v` + ProductVersion.semver |
| `target` | commit | Deve ser ancestral de `origin/main` / igual ao tip de release em `main` |
| `createdBy` | human | Gate P8 |
| `checklistRef` | path | ReleaseChecklist.path com `readyForTag=true` |

---

## Relationships

```text
ProductVersion 1 ── produces ── 1 ChangelogEntry
ProductVersion 1 ── audited-by ── 1 ReleaseChecklist
ReleaseChecklist * ── contains ── * CiJobStatus
ReleaseChecklist * ── contains ── * ValidationGap
ReleaseChecklist * ── contains ── * TechnicalDebtRecord
ProductVersion 1 ── tagged-as ── 0..1 ProductTag
MinimumFlowGuide ── referenced-by ── ReleaseChecklist
```

---

## Validation rules (cross-entity)

1. Tag só se checklist `readyForTag` e `ProductVersion.consistencyPoints` OK.
2. Todo `TechnicalDebtRecord` tem issue **ou** won’t-fix justificado.
3. Todo gap citado na issue #39 aparece com `status=gap` se não houver evidência real.
4. Nenhum `memory-hub*.db` trackeado no commit de release.
