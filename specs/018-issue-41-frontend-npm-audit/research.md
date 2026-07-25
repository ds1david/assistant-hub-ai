# Research: Débito frontend npm audit / Vite major (issue #41)

**Feature**: `specs/018-issue-41-frontend-npm-audit`  
**Date**: 2026-07-25  
**Spec**: [spec.md](./spec.md) (clarifications session 2026-07-25)

## Decision 1 — Escopo do inventário e classificação runtime vs dev

**Decision**: Inventariar **somente** `apps/desktop-shell` via `npm audit` (e `npm audit --omit=dev` para validar runtime de produção do pacote). Classificar cada finding:

| Papel | Critério prático |
|-------|------------------|
| **dev/CI** | Aparece só com devDependencies (toolchain: vite, vitest, eslint e transitivas); ou advisory afeta servidor de dev / runner de teste / linter |
| **runtime empacotado** | Dependency de produção (`dependencies`) ou código empacotado no bundle do app do usuário final |

**Baseline observada no plan (2026-07-25, ambiente de desenvolvimento)**:

- `npm audit`: 10 vulnerabilidades (1 critical, 6 high, 3 moderate) — cluster em **vite / vitest / esbuild / eslint / minimatch / brace-expansion**.  
- `npm audit --omit=dev`: **0 vulnerabilidades**.  
- Conclusão: cluster atual é **dev/CI-only** para a barra FR-013; ainda assim a estratégia da spec **prefere upgrade major** para limpar o report, não aceitar residual por omissão.

**Rationale**: Clarificação Q2; SC-007. Distinguir runtime evita bloquear fechamento por tooling enquanto ainda exige limpeza preferencial.

**Alternatives considered**:
- Tratar todo finding como runtime — rejeitado: distorce risco ao usuário final do app Tauri.  
- Ignorar audit dev — rejeitado: issue #41 e release #39 listam o débito explicitamente.

## Decision 2 — Estratégia de upgrade (major preferido, sem force cego)

**Decision**:

1. **Preferir** bumps explícitos de versão em `package.json` + `npm install` (lockfile commitado).  
2. **Não** usar `npm audit fix --force` como caminho principal (quebra sem revisão).  
3. Ordem sugerida de cluster:  
   - **Vite** → major que elimine advisories do range atual (fixAvailable reportado: vite@8.x; versões atuais ~5.4.x).  
   - **Vitest** → major alinhado ao peer do Vite novo (fixAvailable reportado: vitest@4.x; atual 2.1.x).  
   - **ESLint** → major se necessário para limpar brace-expansion/minimatch (fixAvailable: eslint@10.x; projeto já em ESLint 9 flat config).  
4. Manter `@tauri-apps/api` e TypeScript sem major desnecessário nesta fatia, salvo peer conflict.  
5. Se após tentativa o major quebrar build/test/lint além de **adaptação mínima de config**, documentar residual dev/CI com FR-014 e manter versões viáveis.

**Adaptação mínima permitida**:

- Ajustes em `vite.config.ts` (import de `vitest/config` se exigido; manter `clearScreen: false`, porta `5173`, `strictPort`, `outDir: dist`).  
- Ajustes em `eslint.config.js` / peers `typescript-eslint` se ESLint 10 exigir.  
- Scripts npm só se nomes de CLI mudarem.  
- **Não** reescrever UI, painéis, ou bindings Tauri.

**Rationale**: Clarificação Q1; FR-005/FR-006; evita force cego (out of scope).

**Alternatives considered**:
- Só residual sem tentar major — rejeitado (Q1 prefer major).  
- Zero vulnerabilidades obrigatório sem residual — rejeitado (Q2 permite residual dev/CI).  
- Subir só patch dentro de Vite 5 — insuficiente: advisories listam ranges até 6.4.x com fix major.

## Decision 3 — Artefato canônico de evidência

**Decision**: Um único arquivo:

`docs/validation/issue-41-frontend-npm-audit.md`

Conteúdo mínimo definido em [contracts/dependency-audit-evidence.md](./contracts/dependency-audit-evidence.md): metadados (data, commit, ambiente), baseline, classificação, decisão por família, reauditoria, verificação test/build/lint, residual+FR-014 se houver, link issue #41.

PR da fatia **deve** linkar esse arquivo. Checklist da feature / corpo do PR podem resumir, não substituir.

**Rationale**: Clarificação Q3; P10; SC-001.

**Alternatives considered**: só PR body; só `specs/018/...` — rejeitados na clarificação.

## Decision 4 — Verificação local e CI

**Decision**:

| Camada | Obrigatório |
|--------|-------------|
| Local (WSL) | `npm test`, `npm run build`, `npm run lint` em `apps/desktop-shell` + reauditoria `npm audit` |
| CI | Job existente `desktop-shell-smoke` verde (`npm ci`, `npm test`, `npm run build`, `cargo test` na lib) |
| Lint no CI | **Recomendado low-effort**: adicionar `npm run lint` no step frontend do job para espelhar DoD local; não bloqueia o plan se omitido, desde que local esteja documentado no artefato |
| Tauri MSI / GUI Windows | **Fora** do DoD desta fatia |

**Rationale**: Clarificação Q4; FR-008/FR-009; CI já existe (não inventar PASS por ausência).

**Alternatives considered**: só test+build — rejeitado (Q4). Smoke nativo Windows obrigatório — rejeitado (out of scope / ambiente).

## Decision 5 — Residual e reavaliação

**Decision**: Residual aceito **apenas** se:

1. Item classificado **dev/CI-only**, e  
2. Upgrade inviável com justificativa (quebra além de adaptação mínima), e  
3. Mitigação operacional (ex.: não expor Vitest UI / dev server a rede não confiável; não usar `npm audit fix --force` em CI), e  
4. Gatilhos FR-014: **próximo release de produto** + **piora de risco** (advisory mais severa ou reclassificação runtime).

High/critical em **runtime empacotado** → **não fecha** issue.

**Rationale**: Clarificações Q2 e Q5.

## Decision 6 — Tracking de débito e release

**Decision**: Ao concluir:

- Atualizar `CHANGELOG.md` (nota curta: débito #41 — audit frontend / decisão upgrade).  
- Atualizar item `frontend-vite-audit` em material de release/checklist se ainda apontar “open / won’t major”.  
- Fechar/comentar issue #41 **somente com gate humano** (P8).

**Rationale**: FR-012; alinhamento com release #39 que abriu o débito.

## Decision 7 — Fora de escopo técnico confirmado

- Sem feature de domínio desktop, sem mudança de session-core/agent/transcription.  
- Sem auditoria Python/Java.  
- Sem republicar tag de produto.  
- Sem ADR novo: não há contrato de domínio versionado; evidência + bumps de devDependencies.  
- Sem empacotamento/assinatura de instalador.

## Open items deferred to implement (not research blockers)

- Versões exatas pinadas no `package.json` no dia do implement (mover para latest stable que limpe audit naquele momento).  
- Se Vite 8 + Vitest 4 exigirem mudança de API de config, aplicar o mínimo e anotar no artefato canônico a seção “Adaptações de config”.  
- Decisão final de incluir `npm run lint` no YAML do CI (recomendado; task opcional marcada no tasks).

## Baseline snapshot (for implementers)

```text
# apps/desktop-shell (approx. at plan time)
vite@5.4.x, vitest@2.1.x, eslint@9.x, typescript@5.9.x
@tauri-apps/api@2.x (prod) — audit --omit=dev: 0
npm audit: ~10 findings, fixes report majors (vite 8 / vitest 4 / eslint 10)
```

Reexecutar audit no implement — números acima são snapshot de pesquisa, não verdade eterna.
