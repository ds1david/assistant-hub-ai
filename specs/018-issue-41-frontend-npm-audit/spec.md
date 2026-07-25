# Feature Specification: Débito frontend — auditoria de dependências e decisão Vite (issue #41)

**Feature Branch**: `feature/issue-41-debt-frontend-npm-audit-vite-major-no-major-bump`

**Created**: 2026-07-25

**Status**: Draft

**Input**: User description: "Issue #41 — debt: frontend npm audit / Vite major (no major bump in product tag). Débito da release pós R1–R6 (issue #39 / specs/016). Problema: alertas de auditoria de dependências no shell desktop e eventual necessidade de major do toolchain de build frontend (Vite). Na tag de produto atual a decisão foi não fazer major bump do Vite (FR-012 / #39); manter rastreio até decisão explícita de upgrade ou mitigação. Aceite: decisão documentada de upgrade (ou mitigação) das dependências frontend; verificações do desktop (CI/smoke existentes) permanecem verdes após a mudança."

**Referências**: Issue #41 · Issue #39 / `specs/016-issue-39-release-hardening` (FR-012, débitos) · Constituição (P8, P9, P10, G1–G4) · Shell desktop em `apps/desktop-shell` · Checklist de release (`frontend-vite-audit`)

## Clarifications

### Session 2026-07-25

- Q: Estratégia padrão desta fatia para o cluster Vite / toolchain de build (e majors correlatos)? → A: Major permitido e preferido para limpar o cluster — tentar upgrade major do toolchain com adaptação mínima; se inviável (quebra além de adaptação mínima), residual com justificativa.
- Q: Barra mínima de residual para fechar a issue #41? → A: Residual ok só em dev/CI-only (com mitigação operacional documentada); high/critical em runtime do app empacotado bloqueia fechamento.
- Q: Onde inventário baseline + decisão upgrade/residual + reauditoria ficam versionados como artefato canônico? → A: `docs/validation/` canônico — um arquivo de evidência da fatia; PR linka para ele.
- Q: Quais verificações locais do shell desktop são obrigatórias e verdes no commit de conclusão? → A: test + build + lint (os três scripts de qualidade já do projeto), além da reauditoria documentada.
- Q: Condições mínimas de reavaliação quando residual dev/CI-only for aceito? → A: Reavaliar no próximo release de produto e se o risco piorar (nova advisory mais severa ou reclassificação para runtime).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inventariar e entender o risco das dependências do shell desktop (Priority: P1)

Um mantenedor precisa de um inventário legível e atual do estado de auditoria de dependências do shell desktop: o que está vulnerável, severidade, se a correção exige major de toolchain, e se o risco afeta runtime de produção do usuário final ou só ferramenta de desenvolvimento.

**Why this priority**: Sem inventário e classificação, upgrade e mitigação são chutes; a issue existe justamente porque a release adiou a decisão sem fechar o risco.

**Independent Test**: A partir do arquivo canônico em `docs/validation/` produzido por esta fatia, um revisor independente lista cada alerta relevante, sua severidade e a classificação (corrigível sem major / exige major / residual aceito), sem rodar investigação ad hoc do zero.

**Acceptance Scenarios**:

1. **Given** o shell desktop com dependências instaláveis a partir do repositório, **When** um mantenedor executa a auditoria de dependências do projeto desktop, **Then** obtém um relatório reproduzível (comandos e resultado resumido) no arquivo canônico em `docs/validation/`, cobrindo vulnerabilidades reportadas no momento do trabalho.
2. **Given** o relatório de auditoria no arquivo canônico, **When** um revisor lê esse inventário, **Then** cada vulnerabilidade relevante aparece com severidade e indicação se a correção disponível exige major de dependência direta ou transitiva.
3. **Given** alertas que afetam apenas ferramentas de desenvolvimento (lint, servidor de dev, runner de testes) versus dependências de runtime do aplicativo, **When** o inventário canônico é lido, **Then** essa distinção está explícita para priorizar risco ao usuário final versus risco ao desenvolvedor/CI.

---

### User Story 2 - Decidir e executar upgrade ou mitigação documentada (Priority: P1)

Um mantenedor tenta, por padrão, upgrades que limpem o cluster de alertas do shell desktop — **incluindo major do toolchain de build frontend e majors correlatos** quando forem o caminho limpo — com adaptação mínima de config/build/test. Residual com mitigação só entra se o major for inviável (quebra além de adaptação mínima) ou para itens isolados que o inventário justifique deixar de fora. A decisão e o estado final da auditoria ficam documentados e auditáveis.

**Why this priority**: O aceite da issue #41 é a decisão documentada + continuidade das verificações do desktop; inventário sem decisão não fecha o débito.

**Independent Test**: Ler a decisão registrada (upgrade vs mitigação, por família de alerta se necessário) e verificar que o estado do repositório e o relatório pós-trabalho batem com essa decisão; nenhuma vulnerabilidade “some” sem upgrade nem sem nota de residual.

**Acceptance Scenarios**:

1. **Given** o inventário da US1, **When** o mantenedor conclui esta fatia, **Then** o arquivo canônico em `docs/validation/` registra a decisão: upgrade major/non-major aplicado por padrão para limpar o cluster, e/ou residual só onde o major (ou o upgrade) foi inviável — com justificativa curta por item/família sem destino de upgrade; o PR da fatia linka esse arquivo.
2. **Given** a estratégia preferida de limpar o cluster via upgrade (incluindo major de toolchain quando necessário), **When** as dependências do shell desktop são atualizadas, **Then** o lockfile/manifestos do projeto desktop refletem as versões escolhidas e a alteração é revisável em PR focada (sem misturar feature de domínio); adaptações limitam-se ao mínimo para build/test/lint.
3. **Given** o major do toolchain de build frontend (ou correlato) se mostra inviável após tentativa ou análise (quebra além de adaptação mínima), **When** um revisor consulta o material da fatia e o rastreio (issue/checklist), **Then** o residual está explícito, com condições de reavaliação e justificativa de inviabilidade — nunca major silencioso, nem omissão, nem residual “por preguiça” sem tentativa/análise registrada.
4. **Given** o estado pós-decisão, **When** a auditoria de dependências é reexecutada, **Then** o material da fatia registra o resultado (cluster limpo no escopo, ou lista residual alinhada à inviabilidade documentada).
5. **Given** residual proposto em dependência classificada como runtime do app empacotado com severidade high ou critical, **When** o mantenedor tenta fechar a fatia/issue, **Then** o fechamento é bloqueado até upgrade (ou reclassificação fundamentada que remova high/critical de runtime); residual só é aceitável para itens dev/CI-only com mitigação operacional documentada.
6. **Given** residual dev/CI-only aceito no artefato canônico, **When** um revisor lê as condições de reavaliação, **Then** constam no mínimo: (1) reavaliar no próximo release de produto e (2) reavaliar se o risco piorar (advisory mais severa ou reclassificação para runtime).

---

### User Story 3 - Manter o shell desktop verificável e utilizável após a mudança (Priority: P1)

Quem depende do shell desktop (desenvolvedor local ou pipeline) precisa que, após qualquer mudança de dependência ou só documentação de residual, as verificações obrigatórias locais e o smoke mínimo do desktop continuem verdes — **test, build e lint** já usados pelo projeto não regredem.

**Why this priority**: Aceite explícito da issue (“CI/desktop smoke continua verde após mudança”). Débito de segurança não pode quebrar o fluxo de desenvolvimento do desktop.

**Independent Test**: No commit da fatia, executar test, build e lint do shell desktop e, se existir job remoto de desktop, confirmar verde; registrar resultados no artefato canônico em `docs/validation/`.

**Acceptance Scenarios**:

1. **Given** mudanças de dependência ou apenas documentação de residual nesta fatia, **When** os testes automatizados do shell desktop são executados no ambiente de desenvolvimento padrão do monorepo, **Then** passam sem regressão introduzida por esta fatia.
2. **Given** as mesmas mudanças, **When** o build do shell desktop e o lint (scripts de qualidade já do projeto) são executados, **Then** ambos concluem com sucesso.
3. **Given** job remoto de CI de desktop existente no pipeline, **When** o commit/PR desta fatia é avaliado, **Then** esse job permanece verde. Se não houver job, o artefato canônico e o checklist da fatia registram “sem job” e a prova fica em test+build+lint locais documentados — ausência de job não é tratada como PASS inventado.

---

### Edge Cases

- Auditoria limpa no dia do inventário, mas nova advisory aparece antes do merge: o material registra a baseline da data do trabalho; novas advisories pós-baseline não bloqueiam o fechamento se o residual/processo de reavaliação estiver documentado.
- Correção disponível só via `audit fix --force` com major em cascata: não aplicar force cego; tratar como decisão de upgrade major planejada ou residual aceito.
- Vulnerabilidade critical/high em ferramenta de dev/CI com vetor que exige servidor de UI/testes exposto na rede: residual **pode** fechar a issue se mitigação operacional (não expor, não usar o modo vulnerável) e gatilhos de reavaliação (próximo release + piora de risco) estiverem documentados.
- Vulnerabilidade high/critical em dependência de **runtime do app empacotado**: residual **não** fecha a issue; exige upgrade (ou evidência de que o pacote não integra o runtime empacotado — reclassificação para dev/CI-only).
- Major do Vite/toolchain quebra plugins ou testes: primeiro aplicar adaptação mínima no shell desktop; se ainda inviável, reverter o major (ou não aplicá-lo) e documentar residual com justificativa — sem expandir para feature de domínio.
- Dependência apenas de desenvolvimento vs runtime do app empacotado: residual em dev-only com mitigação pode ser aceito com barra diferente de runtime; a classificação US1 orienta a decisão.
- Conflito com a tag de produto já publicada (não major na tag): esta fatia **não** altera a tag já lançada; decisão de upgrade aplica-se à linha de desenvolvimento / próxima release, sem reescrever a política histórica da tag.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O projeto MUST fornecer um inventário versionado do estado de auditoria de dependências do shell desktop na baseline do trabalho. O artefato canônico MUST ser um arquivo sob `docs/validation/` que concentre baseline, decisão upgrade/residual, resultado da reauditoria e evidência de verificação verde; o PR da fatia MUST linkar esse arquivo. Checklist da feature e corpo do PR MAY resumir, mas MUST NOT substituir o canônico.
- **FR-002**: O inventário MUST listar, para cada vulnerabilidade relevante: identificador/advisory ou nome do pacote, severidade reportada, e se a correção conhecida exige major de dependência.
- **FR-003**: O inventário MUST classificar o impacto como runtime do aplicativo do usuário final, ferramenta de desenvolvimento/CI, ou ambos, com base no papel da dependência no shell desktop.
- **FR-004**: Esta fatia MUST registrar uma decisão explícita e versionada de upgrade e/ou mitigação com residual aceito, cobrindo 100% dos itens do inventário (nenhum item sem destino).
- **FR-005**: Quando a decisão incluir upgrades (caso padrão para limpar o cluster), o monorepo MUST atualizar manifestos e lockfile do shell desktop de forma revisável, sem alterar features de domínio; adaptações de config/build/test MUST permanecer mínimas.
- **FR-006**: Bump major do toolchain de build frontend (Vite) e majors correlatos (ex.: runner de testes acoplado) são **permitidos e preferidos** nesta fatia quando forem o caminho limpo para fechar o cluster de alertas da baseline; a decisão de major MUST ficar documentada. Residual para esses majors MUST ocorrer somente se o upgrade for inviável (quebra além de adaptação mínima), com justificativa e condições de reavaliação — fechando o débito #41 sem reescrever a política histórica “no major na tag” da release #39.
- **FR-007**: Após a decisão, o material da fatia MUST registrar o resultado da reauditoria (limpo no escopo, ou residual aceito item a item).
- **FR-013**: Residual MUST NOT ser usado para fechar a issue quando o item for classificado como runtime do app empacotado **e** severidade high ou critical. Residual MAY fechar a issue apenas para itens dev/CI-only, com mitigação operacional e condições de reavaliação documentadas.
- **FR-014**: Todo residual aceito MUST listar no artefato canônico, no mínimo, estes gatilhos de reavaliação: (1) próximo release de produto do monorepo; (2) piora de risco — nova advisory mais severa para o mesmo pacote/caminho, ou reclassificação do impacto para runtime do app empacotado.
- **FR-008**: Após qualquer mudança de dependência desta fatia (ou ao concluir só com residual documentado), as verificações locais obrigatórias do shell desktop — **test, build e lint** — MUST permanecer passando no ambiente padrão do monorepo; o artefato canônico MUST registrar que foram executadas e o resultado.
- **FR-009**: Se existir job remoto de CI para o shell desktop, ele MUST permanecer verde no commit da fatia; se não existir, o material MUST anotar “sem job” e apontar a prova local — sem tratar ausência como PASS.
- **FR-010**: Esta fatia MUST NOT introduzir nova feature de domínio (captura, STT, memória, provedores, UI de produto além do necessário para manter o shell compilando/testando após upgrade de toolchain).
- **FR-011**: Segredos, tokens e conteúdo sensível MUST NOT ser introduzidos em logs, commits ou material de auditoria (P9).
- **FR-012**: O rastreio da issue #41 e, se aplicável, o item de débito no material de release/checklist MUST ser atualizáveis para refletir o fechamento (upgrade feito ou residual aceito com link à evidência desta fatia).

### Key Entities

- **Dependency Audit Inventory**: Snapshot legível das vulnerabilidades do shell desktop na baseline (pacote, severidade, major necessário, runtime vs dev), seção do artefato canônico em `docs/validation/`.
- **Upgrade-or-Mitigate Decision**: Registro explícito por item ou família no mesmo artefato canônico: upgrade aplicado, residual aceito + mitigação/condições, ou adiamento de major com gatilho de reavaliação.
- **Post-Change Verification Record**: Evidência no artefato canônico de que test, build e lint locais (e, se houver, CI desktop) permaneceram verdes após a mudança.
- **Residual Risk Item**: Vulnerabilidade que permanece após a fatia, com justificativa, mitigação e gatilhos de reavaliação (próximo release + piora de risco), no artefato canônico.
- **Canonical Validation Evidence**: Arquivo versionado sob `docs/validation/` que é a fonte única de verdade da fatia para inventário, decisão, reauditoria e verificação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um revisor independente consegue, em menos de 20 minutos, reconstruir a baseline de auditoria e a decisão final (upgrade vs residual) só a partir do arquivo canônico em `docs/validation/` (e do link no PR).
- **SC-002**: 100% dos alertas presentes no inventário baseline têm destino documentado (corrigido por upgrade ou residual aceito com justificativa) — zero omissão.
- **SC-003**: No commit de conclusão da fatia, test, build e lint do shell desktop passam 100%; a evidência consta no artefato canônico em `docs/validation/`.
- **SC-004**: Se existir job remoto de desktop no pipeline, ele está verde no commit/PR da fatia; se não existir, o material registra “sem job” + prova local (nunca PASS inventado por ausência).
- **SC-005**: Zero major silencioso do toolchain de build frontend: major dessa toolchain, quando aplicado, aparece na decisão documentada; se não aplicado, o residual correspondente está listado com justificativa de inviabilidade (não de omissão).
- **SC-006**: Zero nova feature de domínio introduzida pelo trabalho desta fatia (diff revisável limitado a dependências, ajustes mínimos de toolchain/config de build-test, e documentação de decisão/evidência).
- **SC-007**: O débito #41 fica em estado fechável somente se: (a) não restar high/critical em runtime do app empacotado, e (b) todo residual restante for dev/CI-only com mitigação e gatilhos de reavaliação (próximo release + piora de risco) documentados — ou o report estiver limpo no escopo desktop.
- **SC-008**: 100% dos itens residuais aceitos no artefato canônico incluem explicitamente os dois gatilhos mínimos de reavaliação (FR-014).

## Assumptions

- O escopo de dependências é o shell desktop do monorepo (`apps/desktop-shell` e o que ele empacota/declara), não outros ecossistemas (Python, Java/Maven) salvo menção cruzada se compartilhasse o mesmo manifesto — o que hoje não é o caso.
- “No major bump in product tag” refere-se à política da release #39 / tag de produto já tratada; esta fatia fecha o *follow-up* #41 e **prefere** major na linha de desenvolvimento quando necessário para limpar o cluster, sem reescrever a história da tag anterior.
- Nome da branch `feature/issue-41-debt-frontend-npm-audit-vite-major-no-major-bump` reflete o *won't major na tag de produto* (#39 / FR-012 histórico). **Nesta fatia (#41)** a estratégia clarificada é a oposta do “congelar major”: major do toolchain é **permitido e preferido** para limpar o cluster; o nome da branch **não** restringe o trabalho.
- Estratégia padrão (clarificada): major do toolchain de build e correlatos **permitido e preferido** para limpar o cluster de alertas da baseline, com adaptação mínima; residual só se inviável. Upgrades não-major ainda são preferidos quando bastarem para o mesmo item.
- **Adaptação mínima (operacional)**: mudanças só em `package.json` / lockfile, `vite.config.ts`, `eslint.config.js`, `tsconfig.json` e ajustes pontuais em `src/` ou `tests/` necessários para o toolchain compilar/testar/lintar — **sem** nova UI, painéis, contratos de domínio ou features de produto. **Inviável**: após uma tentativa documentada de major (pins + install + adaptações mínimas), `npm test` ou `npm run build` ou `npm run lint` ainda falham **sem** caminho de correção dentro dessa fronteira; então residual dev/CI com FR-014 (não expandir escopo para “fazer o major passar a qualquer custo”).
- Barra de residual (clarificada): high/critical em runtime empacotado bloqueia fechamento; residual aceitável só em dev/CI-only com mitigação operacional. No shell desktop atual, a maior parte do cluster (toolchain de build/test/lint) tende a classificar-se como dev/CI — a classificação US1 é a fonte da verdade, não este palpite. Role `both` ou dúvida: high/critical usa a **mesma barra de runtime** no close (FR-013).
- Artefato canônico (clarificado): um arquivo em `docs/validation/` concentra baseline, decisão, reauditoria e verificação; alinhado a P10 (evidências manuais/validação em `docs/validation/`).
- Verificações locais obrigatórias (clarificadas): test + build + lint.
- Gatilhos de reavaliação de residual (clarificados): próximo release de produto + piora de risco (advisory mais severa ou reclassificação para runtime).
- “Smoke desktop” / verificação local obrigatória (clarificada): scripts de **test, build e lint** do shell desktop + job de CI se houver; esta fatia não exige smoke de app nativo Windows nem pipeline de instalador assinado.
- Ambiente de verificação: WSL para comandos de pacote/testes de frontend conforme prática do monorepo; smoke de app nativo Windows permanece o que o projeto já documenta, sem novo gate de hardware além do já exigido para desktop.
- Fechar a issue no GitHub permanece gate humano (P8); a fatia prepara evidência e PR, não merge/fecha sozinha.

## Out of Scope

- Nova feature de domínio ou redesign de UI do shell.
- Assinatura de instaladores, distribuição para usuários finais, ou empacotamento desktop além do necessário para validar build após upgrade.
- Auditoria e upgrade de dependências Python/Java de outros módulos do monorepo.
- Alterar a política constitucional de versionamento do monorepo ou republicar a tag de produto anterior.
- Aceitar `audit fix --force` cego sem revisão de breaking changes.
- Compromisso de “zero vulnerabilidades para sempre”; apenas baseline + decisão + reauditoria no fechamento da fatia.
