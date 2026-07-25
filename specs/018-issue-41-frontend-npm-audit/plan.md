# Implementation Plan: Débito frontend — auditoria de dependências e decisão Vite (issue #41)

**Branch**: `feature/issue-41-debt-frontend-npm-audit-vite-major-no-major-bump` (spec dir `018-issue-41-frontend-npm-audit`) | **Date**: 2026-07-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/018-issue-41-frontend-npm-audit/spec.md` (issue #41; clarifications 2026-07-25)

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Fechar o débito **frontend npm audit / Vite major** (#41): inventariar vulnerabilidades do shell desktop (`apps/desktop-shell`), **preferir upgrade major** do toolchain de build/test/lint (Vite + correlatos) com adaptação mínima de config, reauditar, e registrar baseline + decisão + verificação no artefato canônico `docs/validation/`. Residual só para **dev/CI-only** com mitigação e gatilhos de reavaliação; **high/critical em runtime empacotado bloqueia fechamento**. Verificações obrigatórias: **test + build + lint** locais; job CI `desktop-shell-smoke` permanece verde.

Detalhes: [research.md](./research.md). Modelo: [data-model.md](./data-model.md). Contrato do artefato: [contracts/dependency-audit-evidence.md](./contracts/dependency-audit-evidence.md). Validação: [quickstart.md](./quickstart.md).

## Technical Context

**Language/Version**: TypeScript (frontend shell) + Node.js 22 (CI e WSL); Rust/Tauri inalterados em domínio — só revalidados se CI/local cargo test já existir.

**Primary Dependencies (toolchain sob upgrade)**: Vite (hoje ^5.4.x), Vitest (^2.x), ESLint 9 + typescript-eslint (flat config), TypeScript 5.9, jsdom. Runtime de app: `@tauri-apps/api` ^2 (fora do cluster de audit atual).

**Storage**: Arquivo de evidência versionado em `docs/validation/` (markdown). Sem banco, sem secrets.

**Testing**: `npm test` (vitest), `npm run build` (tsc -b + vite build), `npm run lint` (eslint). CI job `desktop-shell-smoke` (npm ci/test/build + cargo test na lib Rust). Sem GPU/hardware (P10).

**Target Platform**: WSL para comandos npm/audit/test/build/lint; job remoto Ubuntu para smoke. App nativo Windows/Tauri full build fora do DoD desta fatia.

**Project Type**: Débito de segurança/higiene de dependências no shell desktop do monorepo (não feature de domínio).

**Performance Goals**: N/A de runtime de produto. Meta de processo: revisor reconcilia baseline + decisão em &lt;20 min (SC-001); suite local verde no commit de fechamento (SC-003).

**Constraints**: Spec clarificada (major preferido; residual só dev/CI; artefato `docs/validation/`; test+build+lint). Constituição P8 (sem merge/close automático), P9 (sem secrets no material de audit), P10 (testes determinísticos), P1 (spec antes de código). Sem `npm audit fix --force` cego. Sem nova UI/domínio.

**Scale/Scope**: Um pacote npm (`apps/desktop-shell`), 1 arquivo de evidência, possível ajuste mínimo de `vite.config.ts` / eslint / package.json + lockfile, nota em changelog/checklist de débito. Sem Python/Java.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|-----------|-----------|
| P1 — Spec antes de código | PASS. Spec + 5 clarificações + checklist 16/16; plan não implementa código de domínio. |
| P2 — Core independente de fornecedores | PASS. Nenhuma integração STT/LLM; só toolchain frontend. |
| P3 — WSL-first | PASS. npm/audit/test no WSL; sem WASAPI. |
| P4 — Contratos versionados | PASS. Sem schema de domínio; contrato feature-local do **artefato de evidência**. |
| P5 — Canal/origem | N/A. |
| P6 — Isolamento áudio | N/A. |
| P7 — Identidade dispositivo | N/A. |
| P8 — Automação com autorização | PASS. Plano não fecha issue/merge; tracking humano. |
| P9 — Privacidade | PASS. Evidência sem tokens/áudio/secrets (FR-011). |
| P10 — Qualidade determinística | PASS. DoD = test/build/lint + audit reproduzível; sem hardware. |
| Versionamento | PASS. Sem tag de produto nesta fatia; não reescreve política da tag #39. |

Nenhuma violação → Complexity Tracking vazio.

### Post-design re-check (Phase 1)

Gates permanecem PASS. Artefatos de design limitam-se a inventário/decisão/verificação de dependências do shell desktop, não introduzem provedores, não tocam contratos de áudio/sessão, e mantêm residual com barra runtime vs dev explícita.

## Project Structure

### Documentation (this feature)

```text
specs/018-issue-41-frontend-npm-audit/
├── plan.md                 # This file
├── research.md             # Phase 0
├── data-model.md           # Phase 1
├── quickstart.md           # Phase 1
├── contracts/
│   └── dependency-audit-evidence.md
├── checklists/
│   └── requirements.md
└── tasks.md                # Phase 2 — /speckit-tasks (não criado aqui)
```

### Source Code / artifacts (repository root)

```text
apps/desktop-shell/
├── package.json              # bumps vite / vitest / eslint (e peers)
├── package-lock.json         # regenerado com npm install
├── vite.config.ts            # adaptação mínima se major exigir
├── eslint.config.js          # flat config; ajustar se ESLint 10 exigir
├── tsconfig.json             # só se major TypeScript/tooling exigir
├── src/                      # sem mudança de domínio prevista
└── tests/                    # devem permanecer verdes

docs/validation/
└── issue-41-frontend-npm-audit.md   # artefato canônico (baseline + decisão + reaudit + verdes)

.github/workflows/ci.yml
└── job desktop-shell-smoke   # manter verde; opcional: acrescentar `npm run lint` se low-effort

CHANGELOG.md                  # nota de débito #41 resolvido (ao fechar fatia)
docs/release/checklist-*.md   # atualizar item frontend-vite-audit se ainda listar open debt
```

**Structure Decision**: Trabalhar só em `apps/desktop-shell` (manifest + lock + configs de toolchain) e no artefato canônico sob `docs/validation/`. Sem novos pacotes npm/Maven. Sem mudanças em `agents/`, `services/session-core` ou `services/transcription-service`. Rust/Tauri só revalidado pelo smoke já existente (cargo test da lib), sem upgrade de crates nesta fatia.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Implementation sketch (for `/speckit-tasks`, not code)

1. **Baseline**  
   - Em `apps/desktop-shell`: `npm ci` (se necessário), `npm audit` (+ opcional `--json` para extrair contagens).  
   - Classificar cada finding: severity, package, fixAvailable/major?, **runtime empacotado vs dev/CI** (hoje: `npm audit --omit=dev` = 0 → cluster atual é dev/CI).  
   - Escrever seções Baseline no artefato canônico.

2. **Upgrade preferido (cluster toolchain)**  
   - Bumps explícitos em `package.json` (não `audit fix --force`): Vite → major que limpe advisories (alvo: latest stable que satisfaça audit), Vitest alinhado ao peer do Vite, ESLint major se necessário para brace-expansion/minimatch.  
   - `npm install` → lockfile.  
   - Adaptação mínima de `vite.config.ts` / vitest entry (`vitest/config` se exigido) / eslint flat config.  
   - Se inviável após tentativa: reverter major, documentar residual (dev/CI) com FR-014.

3. **Verificação**  
   - `npm test && npm run build && npm run lint`  
   - `npm audit` (reauditoria)  
   - Opcional local: `cargo test` em `src-tauri` se ambiente tiver Rust.  
   - CI: `desktop-shell-smoke` verde no PR.

4. **Evidência canônica**  
   - Completar `docs/validation/issue-41-frontend-npm-audit.md` conforme [contracts/dependency-audit-evidence.md](./contracts/dependency-audit-evidence.md).  
   - Link no PR.

5. **Tracking**  
   - CHANGELOG / item de débito release; issue #41 comentário/close **humano** (P8).

## Phases completed by this command

| Phase | Artifact | Status |
|-------|----------|--------|
| 0 Research | [research.md](./research.md) | Done |
| 1 Design | [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md) | Done |
| 2 Tasks | [tasks.md](./tasks.md) | Done (`/speckit-tasks`); remediações analyze I1/I3/U1/U2 aplicadas |
