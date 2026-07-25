# Processo Spec-Driven Development — Assistant Hub AI

## Objetivo

Tornar o desenvolvimento previsível, auditável e seguro para uso com Claude Code e automação, sem eliminar julgamento humano nos pontos de risco.

## Sequência

```text
Issue
  → Specify (spec.md)
  → Clarify
  → Plan (plan.md)
  → Checklist
  → Tasks (tasks.md)
  → Analyze          ← Gate G2
  → Implement
  → Converge
  → Validate         ← Gate G3
  → PR draft
  → Review           ← Gate G4
  → Merge manual
```

Gate G1 ocorre ao aprovar a spec antes de plan/tasks.

## Artefatos por feature

```text
specs/<nnn>-<key>-<slug>/
  spec.md
  plan.md
  tasks.md
  checklists/
  research.md          # opcional
docs/validation/<key>-*.md   # quando houver manual
docs/adr/NNNN-*.md           # quando decisão estrutural
```

Umbrellas existentes (`001`, `002`, `003`) **não** são renumeradas. Features novas a partir de `004`.

## Automação

- Script: `scripts/wsl/spec-cycle.sh`
- Spec Kit CLI: `specify` + skills `/speckit.*` no Claude Code
- Permitido automatizar: branch, commits, push, PR **draft**
- Proibido automatizar: merge, force push, exclusão de main

## Versionamento

- Fonte: `VERSION` na raiz
- Check: `./scripts/release/check-version.sh`
- Bump local: `./scripts/release/bump-version.sh <semver>` (propaga README, FastAPI, agent pyproject + `__version__`, assert CI)
- Changelog: `CHANGELOG.md` na raiz
- Checklist de release (template): `docs/release/checklist-template.md`
- Checklist preenchido por versão: `docs/release/checklist-<versão>.md`
- Fluxo mínimo (outro dev): `docs/release/min-flow.md` (link no README)
- Tag: somente no commit já em `main`, após CI verde e checklist **Ready for tag = YES** (gate humano; constituição P8). Prefixo `v` + SemVer (ex. `v0.2.0`).

## Definition of Done

Ver constituição e template de PR. Resumo:

1. Spec/plan/tasks/analyze coerentes
2. Testes cobrem aceite e negativos
3. Contratos ok (ou ADR + compatibilidade)
4. CI verde
5. Validação manual registrada se necessária
6. Sem segredos/caches no diff
7. PR draft completa; merge humano
