# Quickstart validation: Release Hardening (issue #39)

**Feature**: `specs/016-issue-39-release-hardening`  
**Purpose**: Prove the release process and docs work end-to-end without inventing domain features.

See also: [contracts/release-process.md](./contracts/release-process.md), [data-model.md](./data-model.md), [research.md](./research.md).

---

## Prerequisites

- WSL workspace with Git, Docker (for compose checks), SDKMAN/Java/Maven for local java if desired  
- Access to GitHub Actions for the repo (CI evidence)  
- Optional for full SC-004: Windows host with agent + desktop toolchain  
- Human authorization for merge and tag (constitution P8)

---

## Passo 0 — Baseline (antes das mudanças)

```bash
cd /home/david/workspace/assistant-hub-ai
./scripts/release/check-version.sh
git status
git ls-files '*.db' '**/memory-hub.db' || true
```

**Esperado**: checker reflete estado atual; nenhum `memory-hub.db` trackeado (ou lista vazia após higiene).

---

## Passo 1 — Higiene e scripts de versão

Após implementar FR-009 e extensão do `bump-version.sh`:

```bash
# Simular bump local (use versão de teste só em branch; reverter se necessário)
./scripts/release/bump-version.sh 0.2.0   # ou a versão escolhida no release
./scripts/release/check-version.sh
```

**Esperado**: exit 0; `VERSION`, README, FastAPI, agent pyproject, agent `__init__.py`, CI assert alinhados.

```bash
# Confirmar ignore patterns
git check-ignore -v data/session-core/memory-hub.db \
  services/session-core/data/memory-hub.db 2>/dev/null || true
```

**Esperado**: paths cobertos pelo `.gitignore`.

---

## Passo 2 — CI local / remoto

### Desktop smoke (espelha o job novo)

```bash
cd apps/desktop-shell
npm ci
npm test
npm run build
cd src-tauri && cargo test && cd ../..
```

### Suítes já cobertas por CI (opcional local)

```bash
mvn test
PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests
PYTHONPATH=agents/windows-audio-agent/src pytest -q agents/windows-audio-agent/tests
./scripts/release/check-version.sh
```

### Remoto

Após push/merge em `main`, abrir o run de Actions do SHA de release e preencher a tabela CI do checklist: cada job existente **green**; nenhum red.

---

## Passo 3 — Artefatos de release

1. Criar `docs/release/checklist-template.md` e `docs/release/checklist-<versão>.md` preenchido.  
2. Criar/atualizar `CHANGELOG.md` com seção da versão (Summary, Gaps, Known debts).  
3. Garantir `docs/release/min-flow.md` + links no README.  
4. Issues de débito abertas (ou won’t-fix justificado) e linkadas no checklist.

**Esperado**: checklist com **Ready for tag = YES** só se SC-001/002/005/006/007/008 satisfeitos; gaps T024/T033 como **gap** se não houver evidência real.

---

## Passo 4 — Fluxo mínimo (SC-004) — só README + links

Em clone fresco na tag/commit de release, **sem** conhecimento tribal:

1. Seguir README → WSL bootstrap, `.env`, subida STT/compose, session-core.  
2. Verificar health documentado.  
3. Seguir seção agent Windows; confirmar “conectado”.  
4. Seguir seção desktop; confirmar shell “no ar”.  
5. Seguir provedores (`ai-providers` sample → config local gitignored).

**Pass**: três pilares no ar com critérios documentados.  
**Block**: falta Windows/GPU — registrar bloqueio; **não** marcar SC-004 completo.

---

## Passo 5 — Tag (gate humano)

Somente depois de merge em `main` + CI verde + checklist YES:

```bash
git checkout main
git pull
# confirmar SHA
git rev-parse HEAD
# anotar no checklist
git tag -a "v$(tr -d '[:space:]' < VERSION)" -m "Release $(tr -d '[:space:]' < VERSION)"
git push origin "v$(tr -d '[:space:]' < VERSION)"
```

**Esperado**: tag no remoto aponta para o SHA de `main` documentado; GitHub mostra a tag.

**Proibido nesta validação**: tag na feature branch; push sem checklist YES.

---

## Passo 6 — Auditoria rápida (SC-002)

Revisor independente, &lt; 15 min:

- [ ] `VERSION` == README `## Versão` == `check-version.sh` OK  
- [ ] Checklist CI todos green / absent explícito  
- [ ] Gaps sem PASS inventado  
- [ ] Débitos com issue ou won’t-fix  
- [ ] Tag `v*` no SHA de main  

---

## Definition of done (esta feature)

| Critério | Como provar |
|----------|-------------|
| SC-001 | Actions no SHA de main |
| SC-002 | Passo 6 |
| SC-003 | `git ls-remote --tags` + SHA |
| SC-004 | Passo 4 em ambiente completo |
| SC-005 | Checklist Gaps |
| SC-006 | `git ls-files` + gitignore |
| SC-007 | Checklist Debts + issues |
| SC-008 | Checklist 100% preenchido |
