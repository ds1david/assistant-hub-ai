# Data Model: Inventário e decisão de auditoria de dependências (frontend)

**Feature**: `specs/018-issue-41-frontend-npm-audit`  
**Date**: 2026-07-25

Modelo **documental** (markdown em `docs/validation/`), não persistência de aplicação. Entidades alimentam o artefato canônico e o contrato [dependency-audit-evidence.md](./contracts/dependency-audit-evidence.md).

## Entity: `DependencyFinding`

Uma vulnerabilidade (ou entrada agregada por pacote) reportada pela auditoria.

| Campo | Tipo | Regras |
|-------|------|--------|
| `packageName` | string | Nome do pacote npm (direto ou transitivo) |
| `severity` | enum | `critical` \| `high` \| `moderate` \| `low` \| `info` (como no report) |
| `advisoryIds` | string[] | GHSA/CVE/URLs do report quando disponíveis |
| `isDirect` | boolean | Dependência direta do `package.json`? |
| `role` | enum | `runtime_packaged` \| `dev_ci` \| `both` |
| `fixRequiresMajor` | boolean | Correção conhecida exige major de dependência direta ou transitiva relevante |
| `fixAvailableVersion` | string, opcional | Versão sugerida pelo audit, se houver |
| `rangeAffected` | string, opcional | Range reportado |
| `notes` | string, opcional | Vetor (dev server, lint DoS, etc.) |

### Regras de `role`

- Se o pacote só entra via `devDependencies` (ou é ferramenta de build/test/lint) → `dev_ci`.  
- Se está em `dependencies` ou integra o bundle/runtime do app → `runtime_packaged`.  
- Em dúvida documentada → `both` e tratar com a barra mais restritiva (como runtime para high/critical).  
- **`both` ou dúvida**: para severidade **high/critical**, mesma barra de `runtime_packaged` no close (FR-013) — residual não fecha a issue até upgrade ou reclassificação fundamentada para `dev_ci` puro.

## Entity: `AuditBaseline`

Snapshot no início do trabalho.

| Campo | Tipo | Regras |
|-------|------|--------|
| `capturedAt` | date (ISO) | Data da coleta |
| `commit` | string | SHA curto ou full do commit baseline |
| `environment` | string | Ex.: WSL, Node version |
| `command` | string | Ex.: `npm audit` em `apps/desktop-shell` |
| `summaryCounts` | map severity→count | Totais do report |
| `prodOnlyClean` | boolean | Resultado de `npm audit --omit=dev` (esperado true no baseline atual) |
| `findings` | `DependencyFinding[]` | Lista completa relevante |

## Entity: `DispositionDecision`

Destino de um finding (ou família de findings).

| Campo | Tipo | Regras |
|-------|------|--------|
| `target` | string | Pacote ou família (ex.: `vite+vitest`, `eslint+minimatch`) |
| `action` | enum | `upgraded` \| `residual_accepted` \| `not_applicable` |
| `fromVersion` | string, opcional | Antes |
| `toVersion` | string, opcional | Depois (se upgraded) |
| `justification` | string | Obrigatório se residual; curto se upgraded |
| `inviabilityEvidence` | string, opcional | O que quebrou além de adaptação mínima (se residual) |

### Transições válidas

```text
[finding in baseline]
        │
        ├─► upgraded ──────────────────────────────► reaudit
        │
        └─► residual_accepted
                constraints:
                  - role must be dev_ci (or both reclassified to dev_ci with evidence)
                  - if role runtime_packaged AND severity in {high,critical}
                        → INVALID (blocks issue close)
                  - must attach ResidualRiskRecord
```

## Entity: `ResidualRiskRecord`

Só quando `action = residual_accepted`.

| Campo | Tipo | Regras |
|-------|------|--------|
| `findingRef` | string | Link ao finding/família |
| `mitigation` | string | Controles operacionais (não expor dev server/UI de testes, etc.) |
| `reevalNextProductRelease` | boolean | MUST be true (FR-014) |
| `reevalOnRiskIncrease` | boolean | MUST be true (FR-014) — advisory pior ou reclassificação runtime |
| `owner` | string, opcional | Mantenedor/time |

## Entity: `VerificationRecord`

Prova de DoD local (+ CI se aplicável).

| Campo | Tipo | Regras |
|-------|------|--------|
| `npmTest` | pass/fail + notes | Obrigatório pass |
| `npmBuild` | pass/fail + notes | Obrigatório pass |
| `npmLint` | pass/fail + notes | Obrigatório pass |
| `npmAuditPost` | summary | Contagens pós-upgrade |
| `ciDesktopSmoke` | pass / sem job / fail | Se job existe, must pass; se fail, fatia não fecha |
| `cargoTestLib` | opcional | CI já roda; local se disponível |
| `commit` | string | Commit das versões finais |

## Entity: `CanonicalEvidenceDocument`

Agregado versionado em `docs/validation/issue-41-frontend-npm-audit.md`.

| Seção | Conteúdo |
|-------|----------|
| Header | Feature, issue #41, commit, data, Node |
| Baseline | `AuditBaseline` |
| Decisions | lista de `DispositionDecision` |
| Reaudit | `npm audit` pós + `omit=dev` |
| Verification | `VerificationRecord` |
| Residuals | `ResidualRiskRecord[]` (pode ser vazio) |
| Close readiness | Boolean: SC-007 satisfazível? |

## Relationships

```text
CanonicalEvidenceDocument
  ├── 1 AuditBaseline
  │      └── * DependencyFinding
  ├── * DispositionDecision  (cobre 100% dos findings / famílias)
  ├── 0..* ResidualRiskRecord
  └── 1 VerificationRecord
```

## Validation rules (spec mapping)

| Regra | Spec |
|-------|------|
| 100% findings com disposition | FR-004, SC-002 |
| Residual high/critical runtime proibido no close | FR-013, SC-007 |
| Residual com 2 gatilhos | FR-014, SC-008 |
| test+build+lint pass | FR-008, SC-003 |
| Artefato em `docs/validation/` | FR-001, Q3 |
| Sem secrets no documento | FR-011, P9 |
