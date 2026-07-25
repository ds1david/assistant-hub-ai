# Research: Release Hardening e tag de produto (pós R1–R6)

**Feature**: `specs/016-issue-39-release-hardening`  
**Date**: 2026-07-25  
**Goal**: Resolver decisões de implementação para issue #39 sem inventar processo paralelo ao monorepo.

---

## Decision 1 — Fonte de verdade de versão e alvo SemVer do marco

**Decision**: Manter `VERSION` na raiz como única fonte de verdade (constituição). Propagar com `scripts/release/bump-version.sh` + `check-version.sh`. Alvo **recomendado** do marco pós R1–R6: **`0.2.0`** (minor de consolidação a partir de `0.1.8`). A escolha final é executada no passo de release (gate humano), não hardcoded na spec.

**Rationale**: Já existem scripts e job CI `policy` que falham em drift. Tags históricas: só `v0.1.6` visível no remoto local; monorepo em `0.1.8`. Um salto `0.1.8 → 0.2.0` comunica o fechamento do arco R1–R6 sem major (ainda período 0.x).

**Alternatives considered**:
- Permanecer em `0.1.9` (patch): subestima o marco de produto.
- `1.0.0`: prematuro — gaps manuais (SF-020 T024, Desktop T033) e distribuição assinada ainda fora.

**Gaps a fechar no bump**:
- `bump-version.sh` hoje atualiza `VERSION`, README `## Versão`, FastAPI `app.version`, agent `pyproject.toml`, CI assert literal — **não** atualiza `agents/windows-audio-agent/src/assistant_hub_audio/__init__.py` (`__version__`), que o `check-version.sh` **já valida**. Estender o bump (ou alinhar manualmente no release) é obrigatório para `check-version` passar.
- `apps/desktop-shell/package.json` está em `0.1.0` e **não** entra no check atual. **Não** forçar alinhamento nesta fatia (fora do script; risco de ruído). Listar como débito opcional se desejado; produto monorepo = `VERSION`.

---

## Decision 2 — Onde moram checklist, changelog e evidências de gap

**Decision**:
| Artefato | Caminho |
|----------|---------|
| Changelog do monorepo | `CHANGELOG.md` na raiz (Keep a Changelog enxuto, seção por tag) |
| Checklist preenchível do marco | `docs/release/checklist-<versão>.md` (ex.: `docs/release/checklist-0.2.0.md`) gerado a partir de `docs/release/checklist-template.md` |
| Registro de gaps conhecidos | Seção **Gaps** no checklist do marco + referências a `docs/validation/*` e tasks T024/T033; se faltar arquivo de validação, o checklist marca **GAP / não executado**, nunca PASS |
| Processo (ops) | `docs/governance/sdd-process.md` (já menciona release) + links no README; roteiro de fluxo mínimo em `docs/release/min-flow.md` linkado do README |

**Rationale**: Issue pede checklist preenchido, changelog curto e evidências honestas. Separar template reutilizável do preenchimento por versão evita sobrescrever histórico. `docs/validation/` permanece o lugar de evidência manual (P10); release só referencia, não inventa PASS.

**Alternatives considered**:
- Só GitHub Release notes: bom complemento, mas não versionado no git como checklist auditável pré-tag.
- Checklist só na issue #39: some com o ciclo da issue; pior auditabilidade no monorepo.

---

## Decision 3 — Jobs de CI no escopo e smoke desktop

**Decision**: Inventário atual de jobs remotos em `.github/workflows/ci.yml`:

| Job | Escopo issue #39 | Status planejado |
|-----|------------------|------------------|
| `policy` | Sim (versão, shell, secrets) | Obrigatório verde |
| `java` | Sim (`session-core` via reactor Maven) | Obrigatório verde |
| `transcription-python` | Sim | Obrigatório verde |
| `windows-audio-agent-unit` | Sim (agent) | Obrigatório verde |
| `windows-audio-agent-windows-smoke` | Sim (agent Windows runner) | Obrigatório verde |
| `compose` | Sim (ops STT/compose) | Obrigatório verde |
| **desktop (novo)** | Sim se criado | **Smoke mínimo — adicionar** |

**Smoke desktop (baixo esforço — FR-013 opção C)**:

```yaml
# Esboço: job desktop-shell-smoke em ubuntu-latest
# - Node LTS: npm ci && npm test && npm run build  (apps/desktop-shell)
# - Rust stable: cargo test --manifest-path apps/desktop-shell/src-tauri/Cargo.toml
# NÃO: cargo tauri build / MSI / WebView2 (Windows-only, pesado)
```

A lib Rust de negócio já é testável sem GUI no Linux/WSL (`docs/desktop-shell/packaging.md`, research da feature 014). Frontend já tem `vitest` + script `test`. Isso encaixa no pipeline existente com ~dois steps e cache padrão — **baixo esforço**, portanto **criar o job** e incluí-lo no gate strict green.

**Rationale**: Clarificação C + inventário real = smoke viável; ausência de job desktop hoje seria “sem job” e enfraqueceria o pilar desktop do fluxo mínimo sem custo alto de CI.

**Alternatives considered**:
- Não criar job: válido pela letra de FR-013 se “baixo esforço” for rejeitado; pior para SC-001 auditável do pilar desktop.
- Job `windows-latest` + `tauri build`: alto esforço, instaladores, WebView2 — fora de escopo (spec Out of Scope).

---

## Decision 4 — Ordem operacional da tag (merge → CI → tag)

**Decision** (alinha clarificação Q3):

1. PR de hardening (docs, CI smoke, gitignore, bump prep se aplicável) → review → **merge humano em `main`**.
2. Confirmar jobs no escopo **verdes no commit de `main`**.
3. Se o bump de versão ainda não estiver em `main`, um commit de release em `main` (ou PR mínimo) com `bump-version.sh` + changelog + checklist preenchido → merge → CI verde de novo.
4. **Humano** cria e faz push da tag `vX.Y.Z` **no SHA de `main`** (não na feature branch).
5. Opcional: GitHub Release a partir da tag, colando o trecho do `CHANGELOG.md`.

**Nunca**: tag automática em CI de PR; tag na branch de feature; force-push de tag sem decisão humana.

**Rationale**: Constituição P8 + FR-005. Scripts existentes **não** criam tag (`bump-version.sh` deixa isso explícito).

---

## Decision 5 — Higiene `memory-hub.db`

**Decision**: Default real do serviço (`application.yml` / `MemoryHubProperties`):  
`data/session-core/memory-hub.db` (relativo ao CWD do processo).  
`.gitignore` **já** ignora `data/session-core/*.db` e `*.db-*`.

A issue citou `services/session-core/data/` — caminho plausível se o processo for iniciado com CWD no módulo. **Endurecer** `.gitignore` com:

```gitignore
# Memory Hub (CWD raiz e CWD módulo)
data/session-core/*.db
data/session-core/*.db-*
services/session-core/data/*.db
services/session-core/data/*.db-*
**/memory-hub.db
**/memory-hub.db-*
```

Verificar que nenhum `.db` de hub está trackeado; se estiver, `git rm --cached` (sem apagar dado local do dev).

**Rationale**: FR-009 + P9; cobrir ambos os CWDs evita regressão silenciosa.

---

## Decision 6 — README / fluxo mínimo (três pilares)

**Decision**: README continua ponto de entrada. Adicionar seção **Fluxo mínimo (release)** com links para `docs/release/min-flow.md`, que detalha na ordem:

1. **WSL**: bootstrap, `.env`, compose/STT, `session-core` health.
2. **Windows agent**: install/run, conexão ao STT, critério “conectado”.
3. **Desktop shell**: dev ou instalado, painel sessão/agent, critério “no ar”.
4. **Provedores**: copiar `samples/ai-providers/providers.example.yaml` → `config/ai-providers.yaml` (gitignored), `docs/security/provider-secrets.md`.

Cada pilar com: pré-requisitos, comandos, **critério de verificação** (health URL, CLI, UI), e falhas comuns WSL vs Windows.

**Rationale**: SC-004 / US3 exigem full stack; README hoje cobre bem WSL/compose e pouco desktop/session-core/providers como caminho único.

---

## Decision 7 — Débitos e gaps (list + issue)

**Decision**: No checklist e no changelog, tabela:

| Item | Tipo | Tracking |
|------|------|----------|
| SF-020 T024 — validação Windows process capture | Gap evidência | Status GAP; sem `docs/validation/sf-020-windows.md` ou arquivo com PASS inventado |
| Desktop T033 — validação manual Windows shell | Gap evidência | Status GAP; validação GUI Windows pendente |
| `sourceType` em `InvocationResult` (consistência/tipagem) | Débito | Issue GitHub nova ou existente + link |
| npm audit / Vite major | Débito | Issue + won’t-fix de major nesta tag (FR-012) |

**Rationale**: Clarificação Q5 (list + issue link). Não corrigir os débitos nesta fatia (FR-011).

---

## Decision 8 — Escopo de código vs docs

**Decision**: Mudanças de código **permitidas** nesta fatia:

- `.github/workflows/ci.yml` (job desktop smoke; asserts de versão via bump)
- `scripts/release/bump-version.sh` (propagar `__version__` do agent)
- `.gitignore` (higiene db)
- Docs: README, `CHANGELOG.md`, `docs/release/*`, possivelmente nota em `docs/governance/sdd-process.md`
- Preenchimento do checklist (conteúdo, não lógica de domínio)

**Proibido**: features de domínio, bump major Vite, fechar gaps manuais inventando PASS, merge/tag por script não supervisionado.

---

## Resolved “unknowns”

| Unknown | Resolution |
|---------|------------|
| SemVer exato | Recomendado `0.2.0`; gate humano no release |
| Desktop CI? | Sim — smoke Node+Rust lib em ubuntu |
| Path do db | `data/session-core/` + endurecer paths alternativos |
| Changelog | `CHANGELOG.md` raiz |
| Tag prefix | `v` + SemVer (`v0.2.0`) alinhado à tag existente `v0.1.6` |
