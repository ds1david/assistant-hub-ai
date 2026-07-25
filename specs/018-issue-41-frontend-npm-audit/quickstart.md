# Quickstart de validação: débito frontend npm audit (issue #41)

**Feature**: `specs/018-issue-41-frontend-npm-audit`  
**Objetivo**: provar inventário → upgrade (ou residual dev/CI) → reauditoria → test/build/lint verdes, com evidência canônica em `docs/validation/`.

## Pré-requisitos

- WSL com Node.js compatível com o CI (Node 22 recomendado; `node -v`).
- Working tree na branch da feature com mudanças de `apps/desktop-shell` aplicadas.
- Rede para `npm ci` / registry npm.
- Sem GPU, sem host Windows, sem Tauri MSI para o DoD desta fatia.

## Documentos de referência

- [spec.md](./spec.md) — FR/SC e clarificações  
- [research.md](./research.md) — decisões de upgrade  
- [data-model.md](./data-model.md) — entidades do inventário  
- [contracts/dependency-audit-evidence.md](./contracts/dependency-audit-evidence.md) — forma do artefato  

## 1. Baseline (antes ou no início do trabalho)

```bash
cd apps/desktop-shell
npm ci
npm audit
npm audit --omit=dev
```

**Esperado**:

| Comando | Esperado no baseline histórico | Notas |
|---------|--------------------------------|-------|
| `npm audit` | findings &gt; 0 (cluster vite/vitest/eslint) | Registrar tabela no artefato |
| `npm audit --omit=dev` | 0 vulnerabilities | Confirma role dev/CI do cluster atual |

Preencher seção **Baseline** de `docs/validation/issue-41-frontend-npm-audit.md`.

## 2. Upgrade (caminho preferido)

1. Editar `package.json`: majors de Vite / Vitest / ESLint (e peers) conforme research.  
2. `npm install`  
3. Ajustes mínimos de config se o toolchain exigir.  
4. **Não** usar `npm audit fix --force` como atalho.

## 3. Verificação obrigatória (DoD local)

```bash
cd apps/desktop-shell
npm test
npm run build
npm run lint
npm audit
npm audit --omit=dev
```

**Esperado**:

| Check | Critério de aceite |
|-------|--------------------|
| `npm test` | exit 0 |
| `npm run build` | exit 0 |
| `npm run lint` | exit 0 |
| `npm audit` | 0 findings **ou** residual só dev/CI documentado com FR-014 |
| `npm audit --omit=dev` | 0 findings (high/critical runtime bloqueia close) |

Registrar na seção **Verificação** + **Reauditoria** do artefato canônico.

### Opcional (espelha CI Rust)

```bash
cd apps/desktop-shell/src-tauri
cargo test
```

## 4. CI remoto

No PR: job `desktop-shell-smoke` em `.github/workflows/ci.yml` deve ficar **verde**  
(`npm ci` + `npm test` + `npm run build` + `cargo test` da lib).

Se o implement adicionar `npm run lint` ao job (recomendado no research), esse step também deve passar.

## 5. Artefato canônico e PR

1. Completar `docs/validation/issue-41-frontend-npm-audit.md` conforme o contrato.  
2. No corpo do PR: link para esse arquivo + resumo (upgraded X→Y / residual Z).  
3. Close da issue #41: **gate humano** após merge (P8).

## 6. Critérios de falha rápida

| Sintoma | Ação |
|---------|------|
| test/build/lint falham após major | Adaptação mínima de config; se inviável → residual dev/CI + justificativa |
| audit limpo em dev mas prod (`--omit=dev`) sujo high/critical | **Não fechar**; corrigir runtime |
| Major aplicado sem menção no artefato | Viola SC-005 — documentar |
| Evidência só no corpo do PR, sem `docs/validation/` | Viola FR-001 / Q3 |

## 7. Tempo alvo

Revisor independente: &lt; 20 minutos do artefato canônico → baseline + decisão (SC-001).
