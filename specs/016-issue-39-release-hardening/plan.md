# Implementation Plan: Release Hardening e tag de produto (pós R1–R6)

**Branch**: `016-issue-39-release-hardening` | **Date**: 2026-07-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-issue-39-release-hardening/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Após R1–R6 o monorepo precisa de um marco **shippable e auditável**: CI strict green nos jobs existentes, versão SemVer única e coerente, changelog curto, checklist de release preenchido, documentação do **fluxo mínimo completo** (WSL + agent Windows + desktop), gaps manuais explícitos (SF-020 T024, Desktop T033) sem PASS inventado, higiene de `memory-hub.db`, e débitos com issue link (ou won’t-fix). A tag Git `vX.Y.Z` só nasce no commit já em `main`, com gate humano.

Abordagem: reutilizar `VERSION` + `scripts/release/*`; estender o bump para cobrir `__version__` do agent; adicionar job CI **desktop-shell-smoke** (baixo esforço: npm test/build + cargo test da lib); criar `CHANGELOG.md`, `docs/release/*` e endurecer `.gitignore`; **não** implementar features de domínio nem bump major do Vite.

## Technical Context

**Language/Version**: Shell (bash) para release scripts; YAML GitHub Actions; Markdown docs. Sem mudança de runtime de domínio. Tooling já no monorepo: Java 21 / Maven (job `java`), Python 3.10–3.12 (transcription/agent), Node/Vite 5 + Rust (desktop-shell, apenas smoke).

**Primary Dependencies**: GitHub Actions (`ci.yml`); scripts existentes `scripts/release/check-version.sh`, `bump-version.sh`; npm/vitest e cargo test para smoke desktop; Docker compose wrapper opcional no job `compose`.

**Storage**: Arquivos versionados (`VERSION`, `CHANGELOG.md`, `docs/release/*`, `.gitignore`). Runtime `memory-hub.db` permanece local e ignorado. Tag Git no remoto. Sem banco novo.

**Testing**: CI remoto como gate; `check-version.sh` local; suítes já existentes dos módulos; smoke desktop (vitest + cargo test); validação de processo via [quickstart.md](./quickstart.md). Testes não dependem de GPU/hardware (P10); SC-004 full stack é validação manual documentada.

**Target Platform**: Manutenção e CI em Ubuntu (Actions) + WSL dev; agent smoke em `windows-latest`; fluxo mínimo completo exige host Windows para agent + desktop.

**Project Type**: Release / ops / documentation hardening do monorepo (não app de domínio novo).

**Performance Goals**: N/A de latência de produto. SC-002: auditoria de versão &lt; 15 min. SC-004: onboarding em até um dia útil com docs.

**Constraints**: P8 — sem merge/tag automatizados; P9 — sem secrets/db no git; P1 — spec/clarify antes de implementar; FR-011/012 — sem feature de domínio e sem Vite major; tag só em `main` após CI verde; gaps sem PASS inventado.

**Scale/Scope**: Um workflow CI (+1 job), poucos scripts/docs, um checklist por versão, uma tag de produto. ~1 marcos SemVer (recomendado `0.2.0`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|-----------|-----------|
| P1 — Spec antes de código | PASS. Spec + clarify (5 Q) + checklist 16/16; implementação ainda não iniciada. G1 humano antes de Implement. |
| P2 — Core independente de fornecedores | N/A / PASS. Nenhuma integração de STT/LLM nova. |
| P3 — WSL-first | PASS. Scripts/docs/CI editados no WSL; agent/desktop smoke usam runners adequados; min-flow documenta fronteira WSL/Windows. |
| P4 — Contratos versionados | PASS. Sem schema de domínio novo; contrato de processo em `contracts/release-process.md` (feature-local). |
| P5 — Canal/origem | N/A. Release não altera pipeline de canais. |
| P6 — Isolamento áudio | N/A. |
| P7 — Identidade dispositivo | N/A. |
| P8 — Automação com autorização | PASS. Plano proíbe merge/tag por bot; sequência humana explícita (research D4). |
| P9 — Privacidade | PASS. Higiene de db; não commitar `config/ai-providers.yaml`/secrets; CI já tem grep de secrets. |
| P10 — Qualidade determinística | PASS. CI/smoke sem hardware; gaps manuais em `docs/validation` referenciados como GAP. |
| Versionamento (constituição) | PASS. Mantém `VERSION` + scripts; tag só por processo de release. |

Nenhuma violação → Complexity Tracking vazio.

### Post-design re-check (Phase 1)

Gates permanecem PASS. Artefatos `research.md`, `data-model.md`, `contracts/release-process.md`, `quickstart.md` não introduzem SDK de provedor, não pedem force-push, e separam evidência manual de PASS de CI.

## Project Structure

### Documentation (this feature)

```text
specs/016-issue-39-release-hardening/
├── plan.md                 # This file
├── research.md             # Phase 0
├── data-model.md           # Phase 1
├── quickstart.md           # Phase 1
├── contracts/
│   └── release-process.md  # Phase 1 — maintainer contract
├── checklists/
│   └── requirements.md
└── tasks.md                # Phase 2 — /speckit-tasks (not this command)
```

### Source Code (repository root) — files this feature may touch

```text
VERSION                              # bump no passo de release
CHANGELOG.md                         # novo
README.md                            # seção fluxo mínimo + links
.gitignore                           # memory-hub paths extras
.github/workflows/ci.yml             # job desktop-shell-smoke
scripts/release/
├── bump-version.sh                  # incluir __version__ do agent
└── check-version.sh                 # já valida; manter
docs/release/
├── checklist-template.md            # novo
├── checklist-<versão>.md            # preenchido no release
└── min-flow.md                      # roteiro três pilares
docs/governance/sdd-process.md       # link opcional ao checklist/changelog
docs/validation/                     # só referência a gaps; não inventar PASS
apps/desktop-shell/                  # apenas consumido pelo smoke CI (sem feature nova)
agents/windows-audio-agent/.../__init__.py   # versão via bump
services/transcription-service/...   # versão via bump (já)
```

**Structure Decision**: Nenhuma árvore de domínio nova. Artefatos de release em `docs/release/` + `CHANGELOG.md` na raiz; processo formalizado em `specs/016-.../contracts/release-process.md`. Smoke desktop reutiliza `apps/desktop-shell` existente sem empacotar MSI no CI.

## Complexity Tracking

> N/A — sem violações constitucionais a justificar.

## Implementation outline (for /speckit-tasks)

Ordem sugerida (não substitui tasks.md):

1. **Foundational**: gitignore memory-hub; estender `bump-version.sh`; template checklist + min-flow stub; job `desktop-shell-smoke` no CI.  
2. **US1 auditabilidade**: inventário CI no template; política de gaps; alinhar docs de versão.  
3. **US3 onboarding**: `docs/release/min-flow.md` + README.  
4. **US4 débitos**: issues + linhas no template/changelog.  
5. **US2 release**: bump `VERSION` (ex. 0.2.0), `CHANGELOG.md`, checklist preenchido, PR → merge main → CI verde → tag humana.  
6. **Polish**: sdd-process links; quickstart dry-run; evidências no PR.

## Generated artifacts (Phase 0–1)

| Artifact | Path |
|----------|------|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contract | [contracts/release-process.md](./contracts/release-process.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

## Next command

```text
/speckit-tasks
```
