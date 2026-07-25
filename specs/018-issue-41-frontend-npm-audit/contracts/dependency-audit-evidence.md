# Contract: Artefato canônico de evidência — auditoria de dependências frontend

**Feature**: `specs/018-issue-41-frontend-npm-audit`  
**Issue**: #41  
**Path canônico**: `docs/validation/issue-41-frontend-npm-audit.md`  
**Date**: 2026-07-25

Este contrato define a **forma e as seções obrigatórias** do artefato de evidência. Não é API HTTP nem schema JSON de domínio.

## 1. Identidade

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Title | sim | Título legível incluindo issue #41 |
| Feature dir | sim | `specs/018-issue-41-frontend-npm-audit` |
| Date | sim | Data ISO da conclusão (ou da baseline se WIP) |
| Commit | sim | SHA do commit cujas versões/lockfile foram auditados no fechamento |
| Environment | sim | WSL/Linux, versão Node (`node -v`), cwd `apps/desktop-shell` |
| Branch note | sim | “no-major-bump” no nome da branch = política da tag #39; **esta fatia prefere major** do toolchain para limpar o audit (spec Q1) |
| PR link | opcional no arquivo; **obrigatório no PR** apontar para este path; PR deve notar branch histórica vs major permitido nesta fatia |

## 2. Seções obrigatórias (ordem recomendada)

### 2.1 Baseline

- Comandos executados (exatos):
  - `npm audit`
  - `npm audit --omit=dev`
- Tabela ou lista de findings com no mínimo: package, severity, direct?, role (`runtime_packaged` \| `dev_ci` \| `both`), fixRequiresMajor, notes curtas. Role `both`/desconhecido + high/critical → barra de close de runtime (FR-013).
- Contagens por severidade.
- Resultado de `--omit=dev` (pass/fail counts).

### 2.2 Decisão (Disposition)

Para cada finding ou família (ex.: `vite+esbuild+vitest`, `eslint+minimatch`):

| Coluna | Obrigatório |
|--------|-------------|
| Família / pacote | sim |
| Ação (`upgraded` / `residual_accepted`) | sim |
| De → Para (versões) | se upgraded |
| Justificativa | sim se residual; curto se upgraded |
| Evidência de inviabilidade | se residual por major inviável |

Cobertura: **100%** dos findings da baseline (SC-002).

### 2.3 Reauditoria

- Mesmos comandos da baseline após mudanças.
- Contagens finais.
- Se residual: lista explícita alinhada a 2.2.

### 2.4 Verificação

| Check | Obrigatório | Critério |
|-------|-------------|----------|
| `npm test` | sim | exit 0 |
| `npm run build` | sim | exit 0 |
| `npm run lint` | sim | exit 0 |
| CI `desktop-shell-smoke` | se job existir | verde no commit/PR; senão anotar “sem job” (não inventar PASS) |

Registrar data/hora ou commit e, se possível, resumo de saída (sem dumps enormes).

### 2.5 Residual (pode ser “nenhum”)

Para cada residual:

- role = `dev_ci` (obrigatório para fechar)
- mitigation
- `reevalNextProductRelease: yes`
- `reevalOnRiskIncrease: yes` (advisory pior ou reclassificação runtime)

**Proibido no close**: residual `runtime_packaged` + severity high/critical.

### 2.6 Close readiness

Parágrafo ou checklist final:

- [ ] SC-007 (sem high/critical runtime; residual só dev/CI com gatilhos)
- [ ] SC-003 (test/build/lint)
- [ ] SC-005 (major documentado ou residual com inviabilidade)
- [ ] Issue #41 pronta para close humano

## 3. Formato

- Markdown versionado no git.
- Sem secrets, tokens, `.env`, áudio ou dumps de `node_modules` (P9 / FR-011).
- URLs de advisory (GitHub Advisory) são permitidas.
- Não commitar saída completa `npm audit --json` se for excessiva; preferir tabela resumida + contagens.

## 4. Compatibilidade / versionamento do contrato

- Mudanças aditivas de seções opcionais são permitidas.
- Remover seções obrigatórias desta fatia exige atualizar a spec #41 (não fazer silenciosamente).

## 5. Consumidores

| Consumidor | Uso |
|------------|-----|
| Revisor de PR | SC-001 — reconstruir baseline e decisão em &lt;20 min |
| Mantenedor de release | Atualizar item `frontend-vite-audit` / changelog |
| Implementador | Template de preenchimento durante a fatia |
