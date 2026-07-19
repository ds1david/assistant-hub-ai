# Constituição — Assistant Hub AI

Status: vigente  
Escopo: todo desenvolvimento no monorepo `assistant-hub-ai`  
Precedência: 1º esta constituição → 2º ADRs aprovados → 3º spec ativa → 4º plan/tasks → 5º CLAUDE.md/AGENTS.md → 6º issue/PR

## Princípios invariantes

### P1 — Especificação antes de código
Nenhuma feature altera código de domínio antes de requisitos, critérios de aceite e fora de escopo estarem em `specs/<nnn>-*/spec.md` e do gate humano de Spec.

### P2 — Core independente de fornecedores
STT, LLM, captura, memória e integrações entram por contratos versionados e plugins. Nenhum serviço de domínio importa SDK de provedor externo.

### P3 — WSL-first, Windows quando necessário
Git, Claude Code, Java, Maven, Docker e testes de serviço rodam no WSL. Captura WASAPI e COM rodam só no Python nativo do Windows. Ambientes virtuais Python nunca são compartilhados entre os dois lados.

### P4 — Contratos versionados
Mudança de schema exige: compatibilidade documentada, ADR quando estrutural, testes de contrato e atualização de samples. Preferir campos aditivos opcionais/anuláveis até migração completa.

### P5 — Separação por canal e origem
`sessionId`, `channelId`, `sourceType`, `label` e metadados de dispositivo permanecem ponta a ponta (agente → WebSocket → evento → dashboard/session-core). Canais não se misturam antes da persistência.

### P6 — Isolamento de endpoint de áudio
Um processo isolado por endpoint WASAPI (ADR-0007). Não compartilhar instância PyAudio entre canais. Falha de um canal não pode silenciar o supervisor.

### P7 — Identidade de dispositivo
Prioridade de seleção: `endpointId` (MMDevice) > `index` > `default`/`nameRegex` (ADR-0011). Sem fallback silencioso quando `endpointId` foi solicitado e não resolve.

### P8 — Automação com autorização
Branch, commits, push e PR draft podem ser automatizados. Merge, force push e fechamento de issue por script são proibidos no fluxo normal. Todo shell step que altera Git ou publica exige gate humano explícito.

### P9 — Privacidade por padrão
Segredos, áudio bruto, tokens e conteúdo sensível não entram em logs, commits, artifacts de CI nem descrições públicas de PR.

### P10 — Qualidade determinística
Testes automatizados não dependem de GPU nem de hardware físico. Validações manuais (Windows/GPU/hardware) geram arquivo em `docs/validation/` com ambiente, commit, passos e resultado.

## Gates humanos obrigatórios

| Gate | Pergunta | Bloqueia |
|------|----------|----------|
| G1 Spec | Problema, aceite e fora de escopo estão corretos? | Plan / Tasks |
| G2 Plan/Analyze | Arquitetura simples, testável e compatível com contratos? | Implement |
| G3 Validate | Testes, diff e evidências manuais bastam para publicar? | Commit final / push / PR |
| G4 Review | PR tecnicamente correta e pronta para main? | Merge |

## Sequência oficial de feature

Issue → Specify → Clarify → Plan → Checklist → Tasks → Analyze → Implement → Converge → Validate → PR draft → Review humano → Merge manual

## Regras operacionais para agentes

1. Ler constituição, ADR relevantes e spec ativa antes de editar.
2. Declarar arquivos afetados e critérios de aceite antes de implementar.
3. Não executar merge, force push, `git push --force` ou exclusão de `main`.
4. Não commitar `.env`, venvs, caches, WAV, tokens ou estado de `.specify/workflows/runs/`.
5. Preferir mudanças pequenas e PRs focadas; não misturar bootstrap, refactor e feature.
6. Ao final do ciclo: diff resumido, riscos, testes executados e evidências.

## Versionamento

- Fonte única: arquivo `VERSION` na raiz do monorepo (período 0.x).
- CI falha se README, serviço FastAPI, `pyproject` do agent ou asserts divergirem de `VERSION`.
- Tag somente por processo de release, nunca por PR de feature.

## Merge e proteção de main

- Squash merge para features comuns.
- Checks obrigatórios verdes.
- Conversas da PR resolvidas.
- Merge sempre humano.
