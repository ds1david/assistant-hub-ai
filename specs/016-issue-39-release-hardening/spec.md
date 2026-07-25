# Feature Specification: Release Hardening e tag de produto (pós R1–R6)

**Feature Branch**: `feature/issue-39-release-hardening-tag-de-produto-p-s-r1-r6`

**Created**: 2026-07-25

**Status**: Draft

**Input**: User description: "Issue #39 — [release] Hardening + tag de produto (pós R1–R6). Objetivo: deixar main shippable e auditável após R1–R6. Escopo: CI verde (agent, transcription, java/session-core, desktop se houver job); VERSION + tag SemVer (ex. 0.2.0) + changelog curto; README/ops: WSL, agent Windows, Docker STT, session-core, desktop, ai-providers.yaml; evidências: gaps explícitos (SF-020 Windows T024, Desktop T033) sem PASS inventado; higiene: gitignore memory-hub.db sob services/session-core/data/; débitos (sourceType InvocationResult, npm audit vite) listados ou issues separadas. Fora de escopo: nova feature de domínio; bump major do Vite sem decisão explícita. Aceite: checklist de release preenchido; tag publicada; outro dev sobe o fluxo mínimo só com o README."

**Referências**: Issue #39 · Constituição (Versionamento, P8, P9, P10, G3/G4) · `docs/roadmap.md` (R1–R6) · `docs/governance/sdd-process.md` (release) · `docs/validation/` · Specs entregues das fatias R1–R6 (`001`–`015` e correlatas)

## Clarifications

### Session 2026-07-25

- Q: O que conta como “fluxo mínimo no ar” para o aceite (SC-004 / US3)? → A: Full stack incluindo desktop — WSL (transcrição em container + núcleo de sessão e serviços WSL do fluxo) + agente de áudio Windows conectado + shell desktop no ar; todos são obrigatórios para o critério de aceite, não opcionais.
- Q: Quão estrito é “CI verde” antes de publicar a tag de produto? → A: Strict green — todo job remoto de CI no escopo que existir (agent, transcription, session-core, desktop se houver) deve estar verde no commit de release; job ausente é anotado como “sem job”, nunca como PASS; falha de job existente bloqueia a tag (sem exceção justificada nesta fatia).
- Q: Quando a tag SemVer de produto é criada em relação a `main`? → A: Tag on `main` after merge — o trabalho de release é mergeado em `main` com CI no escopo verde; em seguida a tag é criada e publicada nesse commit de `main`.
- Q: Se não houver job remoto de CI para o shell desktop, esta release deve criar um? → A: Smoke job only if easy — adicionar job mínimo de desktop/check somente se encaixar no pipeline existente com baixo esforço; caso contrário permanece “sem job” + prova do fluxo mínimo documentado (US3/SC-004). Se o job for criado, entra na regra strict green.
- Q: Como os débitos técnicos conhecidos devem ser registrados nesta release? → A: List + issue link — cada débito conhecido aparece no material de release (checklist/changelog) e tem issue vinculada, ou nota explícita de “accepted won’t-fix para esta tag” com justificativa.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Confiar que a linha principal está verde e auditável (Priority: P1)

Um mantenedor ou revisor precisa saber, sem adivinhar, que a linha principal do produto está em estado shippable: as verificações automáticas relevantes passam, a versão do produto é única e coerente, e o que ainda não foi validado em hardware real está marcado como gap — nunca como sucesso inventado.

**Why this priority**: Sem uma linha principal confiável e auditável, tag e onboarding de outros devs apenas propagam risco. É o pré-requisito de qualquer release.

**Independent Test**: Inspecionar o estado documentado da release (checklist + status das verificações + lista de gaps) e confirmar que (a) as verificações obrigatórias estão verdes, (b) a versão publicada no produto e na documentação coincidem, e (c) cada gap conhecido aparece como gap, não como PASS.

**Acceptance Scenarios**:

1. **Given** a linha principal após o fechamento de R1–R6, **When** um revisor consulta o checklist de release e o status das verificações automáticas remotas cobertas pelo escopo (agente de áudio, serviço de transcrição, núcleo de sessão e shell desktop quando houver job), **Then** todo job existente está verde no commit de release; job ausente aparece como “sem job” (não como PASS); nenhuma falha de job existente é aceita com exceção.
2. **Given** a documentação e artefatos de versão do repositório, **When** um revisor compara a versão do produto com a versão declarada no material de onboarding e nos pontos de consistência exigidos pelo processo de release, **Then** há uma única versão coerente — sem divergência silenciosa.
3. **Given** gaps conhecidos de validação manual (ex.: captura por processo no Windows e itens de desktop ainda sem evidência completa), **When** um revisor lê as evidências de validação e o material de release, **Then** esses itens aparecem explicitamente como incompletos ou pendentes, sem registro de PASS inventado.

---

### User Story 2 - Publicar uma tag de produto com histórico curto e legível (Priority: P1)

Um mantenedor publica uma tag SemVer de produto (exemplo ilustrativo: 0.2.0) que marca o estado consolidado pós R1–R6, acompanhada de um changelog curto o bastante para outro humano entender o que entrou, o que ficou de fora e quais débitos ficaram registrados.

**Why this priority**: A tag é o artefato de “produto shippable” pedido pela issue; sem ela, o trabalho de hardening não vira um marco auditável.

**Independent Test**: A partir do checklist de release preenchido, executar o processo de release (versão + changelog + tag) e verificar que a tag existe, aponta para o commit esperado e o changelog descreve o marco pós R1–R6 em linguagem legível — sem misturar features de domínio novas.

**Acceptance Scenarios**:

1. **Given** o trabalho de release já mergeado em `main` e todos os jobs remotos de CI no escopo que existem verdes nesse commit de `main`, **When** o mantenedor conclui o processo de release, **Then** existe uma tag SemVer publicada no repositório remoto apontando para esse commit de `main` (não para um commit só de branch de feature/release).
2. **Given** a tag publicada, **When** um leitor abre o changelog da release, **Then** encontra um resumo curto do que a versão entrega (consolidação pós R1–R6), o que permanece gap e os débitos listados ou referenciados.
3. **Given** a constituição do projeto (tag só por processo de release; merge e publicação com gate humano), **When** a tag é criada e publicada, **Then** o fluxo respeita autorização humana explícita — merge em `main` e push da tag não são efeito colateral de um PR de feature.

---

### User Story 3 - Outro desenvolvedor sobe o fluxo mínimo só com o README (Priority: P1)

Um desenvolvedor que ainda não conhece o monorepo consegue, usando apenas o README (e documentos de ops linkados a partir dele), subir o **fluxo mínimo completo**: ambiente WSL com transcrição em container e núcleo de sessão, agente de áudio no Windows **conectado**, shell desktop **no ar**, e configuração de provedores de IA documentada (`ai-providers.yaml` / equivalente). Nenhum desses pilares é opcional para o aceite desta release.

**Why this priority**: Critério de aceite explícito da issue (“outro dev sobe o fluxo mínimo só com o README”). Sem onboarding reproduzível do stack completo, a release não é operacionalmente shippable.

**Independent Test**: Em um ambiente limpo (ou com um revisor no papel de “outro dev”), seguir somente o README e links de ops a partir dele até WSL + agente Windows + desktop estarem no ar com critérios de verificação documentados, cronometrando ou registrando bloqueios que exijam conhecimento tribal fora da documentação.

**Acceptance Scenarios**:

1. **Given** um clone fresco do repositório na tag/release, **When** o desenvolvedor segue o README e os documentos de ops referenciados a partir dele, **Then** consegue preparar o ambiente WSL e validar os pré-requisitos listados sem pedir ajuda fora da documentação.
2. **Given** o ambiente WSL preparado, **When** o desenvolvedor segue as seções de ops para transcrição em container, núcleo de sessão, agente Windows, desktop e provedores de IA, **Then** o fluxo mínimo completo sobe: serviços WSL saudáveis, agente Windows conectado e shell desktop no ar, cada um com critério claro de verificação documentado (health/status ou passos equivalentes).
3. **Given** um passo que depende de hardware ou host Windows, **When** a documentação descreve esse passo, **Then** deixa explícito o que roda no WSL versus no Windows e quais falhas comuns esperar — sem omitir a fronteira de ambiente; a ausência de host Windows ou GPU bloqueia o aceite pleno e deve ser registrada como bloqueio de ambiente, não como “fluxo mínimo OK”.

---

### User Story 4 - Higiene do repositório e débitos explícitos (Priority: P2)

Um mantenedor garante que artefatos locais de runtime não poluem o repositório e que débitos técnicos conhecidos estão listados no material de release ou convertidos em issues separadas — em vez de sumirem no ruído do dia a dia.

**Why this priority**: Higiene e débitos explícitos protegem a auditabilidade da release; não bloqueiam sozinhos o “verde”, mas evitam que a tag esconda lixo e dívida.

**Independent Test**: Verificar que bases locais de memória do núcleo de sessão não entram no controle de versão; revisar a lista de débitos da release (ou issues vinculadas) e confirmar que itens conhecidos (ex.: tipagem `sourceType` em resultados de invocação; alerta de auditoria de dependências do frontend/Vite) estão registrados ou deliberadamente adiados com issue.

**Acceptance Scenarios**:

1. **Given** o núcleo de sessão em uso local gerando base de dados sob o diretório de dados do serviço, **When** o status do repositório é inspecionado, **Then** o arquivo de base local não aparece como candidato a commit (ignorado de forma estável).
2. **Given** débitos conhecidos no momento da release, **When** um revisor consulta o checklist/changelog, **Then** cada débito relevante está listado no material de release **e** aponta para issue vinculada (ou para nota explícita de “accepted won’t-fix para esta tag” com justificativa) — nenhum some por omissão.
3. **Given** a decisão de não fazer bump major do Vite nesta release, **When** o material de release e a issue (ou won’t-fix) de débito são lidos, **Then** essa decisão fica explícita no material de release e no rastreio, sem upgrade silencioso de major.

---

### Edge Cases

- Verificação automática intermitente (flaky): a release não marca PASS; job flaky existente bloqueia a tag até estabilizar ou ser corrigido (sem exceção justificada nesta fatia).
- Job de desktop (ou outro do escopo) ausente no pipeline: o checklist registra “sem job”; ausência não é PASS e não substitui a exigência de verde nos jobs que existem. Se for viável com baixo esforço, pode-se adicionar um smoke job mínimo de desktop; uma vez existente, ele passa a ser gate strict green.
- Gap de validação manual em hardware Windows: permanece como gap documentado; não atrasa a tag se o aceite da issue permitir gaps explícitos, mas nunca vira PASS.
- Divergência de versão entre README, arquivo de versão e componentes: o processo de release falha a consistência até alinhar.
- Outro dev sem GPU ou sem host Windows: a documentação descreve o bloqueio; o aceite pleno do fluxo mínimo (WSL + agente + desktop) **não** é declarado como OK — o bloqueio de ambiente é registrado explicitamente.
- Débito de segurança em dependência de frontend: listado; correção major fora de escopo sem decisão explícita.
- Tentativa de criar tag a partir de PR de feature ou só na branch de release (antes do merge em `main`): fora do processo; a tag só nasce no commit já em `main`, após merge e CI verde, com gate humano.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O projeto MUST manter um checklist de release preenchível e versionado (ou referenciado de forma estável) cobrindo verificações automáticas, consistência de versão, changelog, gaps de evidência, higiene e débitos.
- **FR-002**: Todo job remoto de CI no escopo que existir (agente de áudio, serviço de transcrição, núcleo de sessão e shell desktop, se houver job) MUST estar verde no commit de release antes da tag. Job ausente MUST ser anotado no checklist como “sem job” e MUST NOT ser tratado como PASS. Falha de job existente MUST bloquear a tag (sem exceção justificada nesta fatia).
- **FR-013**: Se o pipeline ainda não tiver job de desktop, esta fatia MAY adicionar um smoke job mínimo de desktop **somente** quando o encaixe no pipeline existente for de baixo esforço; caso contrário MUST permanecer “sem job” e a prova do desktop fica no fluxo mínimo documentado (US3/SC-004). Se o smoke job for adicionado, ele MUST obedecer a FR-002 (strict green).
- **FR-003**: O produto MUST expor uma única fonte de verdade de versão SemVer alinhada entre onboarding, artefatos de release e pontos de consistência já exigidos pelo processo do monorepo.
- **FR-004**: O processo de release MUST produzir um changelog curto legível por humanos para o marco pós R1–R6 (o que entrou, gaps, débitos).
- **FR-005**: O processo de release MUST publicar a tag SemVer de produto somente no commit já presente em `main` (após merge do trabalho de release e CI no escopo verde nesse commit), com autorização humana explícita (conforme constituição). A tag MUST NOT ser criada apenas em branch de feature/release antes do merge em `main`.
- **FR-006**: O README (e ops linkados a partir dele) MUST documentar o fluxo mínimo completo e obrigatório para o aceite: WSL (transcrição em container + núcleo de sessão), agente Windows conectado, shell desktop no ar e configuração de provedores de IA.
- **FR-007**: A documentação de onboarding MUST deixar explícita a fronteira WSL vs. Windows e os critérios de verificação de que cada pilar do fluxo mínimo (WSL, agente, desktop) está no ar; “no ar” exige os três pilares, não um subconjunto.
- **FR-008**: Evidências de validação e material de release MUST registrar gaps conhecidos de forma explícita (incluindo, no mínimo, os gaps citados na issue: validação Windows de captura por processo / SF-020 T024 e item Desktop T033), sem marcar PASS inventado.
- **FR-009**: Bases de dados locais do núcleo de sessão sob o diretório de dados do serviço MUST ser ignoradas pelo controle de versão de forma estável.
- **FR-010**: Débitos técnicos conhecidos no momento da release (incluindo tipagem/consistência de `sourceType` em resultados de invocação e alertas de auditoria de dependências do frontend/Vite) MUST constar no material de release (checklist e/ou changelog) **e** MUST ter issue vinculada, **ou** MUST constar com nota explícita de “accepted won’t-fix para esta tag” e justificativa (sem issue de follow-up nesse caso).
- **FR-011**: Esta fatia MUST NOT introduzir nova feature de domínio (captura, STT, memória, provedores, desktop além de hardening/docs/CI/release).
- **FR-012**: Esta fatia MUST NOT realizar bump major de toolchain de frontend (Vite) sem decisão explícita documentada; na ausência dessa decisão, o item permanece como débito listado.

### Key Entities

- **Release Checklist**: Registro auditável do estado pré-tag (verificações, versão, gaps, débitos, links de evidência).
- **Product Version**: Identificador SemVer único do monorepo no momento da tag.
- **Changelog Entry**: Resumo humano do marco de release (entregas, gaps, débitos).
- **Validation Gap**: Item de evidência manual ou de ambiente que permanece incompleto e não pode ser relatado como sucesso.
- **Technical Debt Record**: Débito conhecido listado no material de release com link para issue de follow-up, ou com nota “accepted won’t-fix para esta tag” e justificativa.
- **Minimum Flow Guide**: Conjunto README + ops que permite a outro desenvolvedor subir o fluxo mínimo completo (WSL + agente Windows + desktop) sem conhecimento tribal, com critérios de verificação por pilar.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos jobs remotos de CI no escopo que existem estão verdes no commit de release. Cada job ausente do escopo aparece no checklist como “sem job” (nunca como PASS). Zero falhas de jobs existentes no commit de release.
- **SC-002**: Um revisor independente consegue confirmar, em menos de 15 minutos, a consistência da versão do produto entre onboarding e artefatos de release.
- **SC-003**: Existe uma tag SemVer publicada no remoto para o marco pós R1–R6, apontando para o commit de release documentado no checklist — e esse commit está em `main`.
- **SC-004**: Um desenvolvedor que não participou da implementação consegue, seguindo apenas o README e links de ops a partir dele, deixar no ar o fluxo mínimo completo — WSL (transcrição + núcleo de sessão) + agente Windows conectado + shell desktop — em um único turno de trabalho padrão (até um dia útil). Bloqueios de ambiente (hardware/GPU/Windows) previstos na documentação impedem declarar o aceite pleno; não contam como sucesso parcial do SC-004.
- **SC-005**: 100% dos gaps de evidência citados na issue (e outros gaps conhecidos no momento da release) aparecem como gap/pendente no material de release ou validação — zero PASS inventado nesses itens.
- **SC-006**: Zero artefato de base local do núcleo de sessão sob o diretório de dados do serviço entra como arquivo versionado na árvore limpa da release.
- **SC-007**: 100% dos débitos conhecidos listados no escopo da issue estão no changelog/checklist **e** têm issue vinculada ou nota “accepted won’t-fix para esta tag” com justificativa.
- **SC-008**: O checklist de release do marco está 100% preenchido (cada item com status e evidência/link ou N/A justificado) antes da publicação da tag.

## Assumptions

- O número SemVer exato (ex.: 0.2.0) será escolhido no processo de release a partir da versão atual do monorepo e do histórico de tags; o exemplo 0.2.0 da issue é ilustrativo, não fixo nesta spec.
- “Linha principal shippable” significa o estado em `main` após o consolidado R1–R6 e o merge do trabalho de release — não um canal de distribuição binária para usuários finais. A tag de produto só é criada nesse commit de `main`, depois do merge e do CI verde.
- Publicação da tag, push e merge seguem gates humanos da constituição (P8, G3, G4); automação pode preparar arquivos e checklist, não publicar sozinha.
- “Outro dev” assume o ambiente oficial do projeto (WSL 2 + host Windows para captura e desktop; Docker com GPU quando o fluxo de transcrição local exigir), conforme README — não um ambiente cloud-only. O aceite do fluxo mínimo exige os três pilares (WSL + agente + desktop); ambiente incompleto é bloqueio, não sucesso parcial.
- Jobs de CI para desktop: se não houver job, o default é “sem job” (não PASS) + prova operacional do desktop no fluxo mínimo. Smoke job mínimo só se baixo esforço no pipeline atual; se criado, vira gate strict green. Esta fatia não inventa produto desktop novo além desse endurecimento opcional de CI.
- Gaps SF-020 T024 e Desktop T033 permanecem aceitáveis na tag desde que explícitos; fechar esses gaps com validação em hardware é trabalho separado.
- Bump major do Vite e correções amplas de auditoria de dependências ficam como débito listado no material de release com issue vinculada (ou won’t-fix justificado), salvo decisão humana explícita documentada no checklist.
- Não há nova superfície de domínio; mudanças de código limitam-se a higiene, consistência de versão, CI, documentação e scripts de release já alinhados ao monorepo.
- Referências a R1–R6 correspondem ao roadmap do produto (Streaming Foundation → … → AI Provider Hub) e às specs/validações já existentes no repositório.

## Out of Scope

- Novas features de domínio (áudio, STT, memória, provedores, UI de produto além de docs/hardening).
- Bump major do Vite (ou upgrades amplos de toolchain frontend) sem decisão explícita.
- Fechar gaps de validação em hardware Windows/GPU que dependem de evidência manual nova (apenas documentar).
- Marketplace de provedores, billing, distribuição assinada para usuários finais além do que já existir no monorepo.
- Alterar a política constitucional de versionamento (fonte única de versão; tag só por processo de release).
- Pipeline de CI desktop completo/pesado (empacotamento, instaladores assinados, matrix ampla) — apenas smoke mínimo se baixo esforço, senão documentar “sem job”.
