# Feature Specification: R5 — Audio Agent como sidecar supervisionado

**Feature Branch**: `025-r5-audio-agent-sidecar`

**Created**: 2026-07-26

**Status**: Draft

**Input**: User description: "R5 — empacotar o agent WASAPI (`assistant-hub-audio`) como sidecar do shell Tauri, com resolução de binário, health/versão e supervisor de ciclo de vida (start/stop coordenado). Fecha o maior buraco de `specs/002-desktop-distribution/` após a fatia local `specs/014-issue-35-desktop-tauri-shell-local/`."

**Referências**: `specs/002-desktop-distribution/` (visão R5) · `specs/014-issue-35-desktop-tauri-shell-local/` (shell + start/stop por PATH/venv) · `specs/020-issue-47-sessionid-align/` (sessionId UI↔agent) · ADR-0003, ADR-0007, ADR-0009 · AGENTS.md (sidecars com health, versão e encerramento coordenado) · `docs/desktop-shell/packaging.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Iniciar captura sem instalar o agent à mão (Priority: P1)

Um operador no Windows instala (ou executa o build) do shell desktop e inicia a captura de áudio a partir da interface, **sem** precisar ter instalado `assistant-hub-audio` no PATH nem criar um venv Python manualmente. O shell usa o binário do agent empacotado junto com a aplicação (sidecar).

**Why this priority**: É o valor de produto que diferencia “shell de desenvolvimento” (014) de “distribuição Desktop Lite” (002): sem sidecar, o operador ainda depende de bootstrap Python no host.

**Independent Test**: Em um ambiente onde `assistant-hub-audio` **não** está no PATH, mas o sidecar empacotado (ou fixture de teste equivalente) está presente, iniciar o agent pela UI/comando do shell e confirmar que o processo sobe com o `sessionId` ativo e o profile configurado.

**Acceptance Scenarios**:

1. **Given** o sidecar do agent está presente no pacote da aplicação e o agent não está no PATH do sistema, **When** o operador inicia o agent pela interface com uma sessão ativa, **Then** o shell inicia o processo a partir do binário do sidecar e reporta status “ativo” em modo de controle direto.
2. **Given** o sidecar está ausente e também não há binário no PATH, **When** o operador tenta iniciar o agent, **Then** o shell exibe falha específica de “binário não encontrado”, com orientação de como obter o sidecar ou instalar o agent em modo Developer — nunca uma mensagem genérica.
3. **Given** o operador está em modo Developer com o agent instalado no PATH e **sem** sidecar no pacote, **When** inicia o agent pelo shell, **Then** o comportamento atual (resolução via PATH) continua funcionando (sem regressão de 014/020).

---

### User Story 2 - Ver saúde e versão do sidecar (Priority: P1)

O operador (ou suporte) precisa saber se o agent supervisionado está saudável e qual versão está rodando, para diagnosticar incompatibilidade com o shell ou com o serviço de transcrição.

**Why this priority**: AGENTS.md exige health check e versão em sidecars; sem isso, “ativo” é ambíguo (processo zumbi, binário errado, versão divergente do monorepo).

**Independent Test**: Com o agent iniciado pelo shell a partir do sidecar (ou fixture), consultar o status exposto pelo shell e verificar campos de saúde e versão preenchidos de forma consistente; forçar ausência de versão e confirmar degradação explícita (não inventar número).

**Acceptance Scenarios**:

1. **Given** o agent foi iniciado pelo shell e o binário responde à consulta de versão, **When** o operador consulta o status do agent, **Then** vê a versão reportada pelo binário e indicação de saúde “saudável” enquanto o processo permanece em execução.
2. **Given** o processo do agent encerrou inesperadamente após o start, **When** o shell atualiza o status, **Then** a saúde passa a “não saudável”/parado e o handle gerenciado é limpo — sem deixar o operador acreditar que a captura continua.
3. **Given** o binário existe mas a consulta de versão falha, **When** o status é montado, **Then** a versão aparece como desconhecida (não inventada) e a falha de versão não impede o start se o processo em si estiver saudável.

---

### User Story 3 - Encerramento coordenado sem processos órfãos do sidecar (Priority: P1)

Quando o operador encerra o shell de forma normal, os processos do agent que o **próprio shell iniciou** (sidecar supervisionado) são encerrados de forma ordenada, para não deixar captura órfã consumindo microfone/loopback.

**Why this priority**: Critério de aceite da visão 002 (“sem deixar processos órfãos”) e requisito de encerramento coordenado em AGENTS.md. Processos iniciados **fora** do shell continuam sob política Guided (não matar processo alheio).

**Independent Test**: Iniciar o agent pelo shell (handle gerenciado), encerrar o shell de forma normal (ou simular o hook de shutdown nos testes), e confirmar que o processo do agent não permanece em execução; repetir com agent iniciado fora do shell e confirmar que o shell **não** o mata ao sair.

**Acceptance Scenarios**:

1. **Given** o shell iniciou o agent (modo direto / handle gerenciado), **When** o operador fecha o shell normalmente, **Then** o processo do agent é encerrado pelo supervisor antes (ou durante) o término do shell.
2. **Given** o agent foi iniciado fora do shell (modo Guided), **When** o operador fecha o shell, **Then** esse processo externo **não** é encerrado pelo shell.
3. **Given** o operador usa “parar agent” na interface com handle gerenciado, **When** a ação completa, **Then** o processo termina e o status passa a parado em modo direto, como já exigido em 014/020.

---

### User Story 4 - Documentar empacotamento do sidecar (Priority: P2)

Um desenvolvedor consegue, seguindo apenas a documentação do monorepo, gerar o artefato do agent esperado pelo bundler do shell e produzir um pacote de aplicação que inclui o sidecar — sem passos táticos não documentados.

**Why this priority**: Sem documentação reproduzível, o sidecar só existe na máquina de quem o criou; é o paralelo de US4 da 014, focado no binário de áudio.

**Independent Test**: Seguir o guia de packaging desta feature em host Windows de referência (ou CI Windows, quando existir) e obter o pacote com o sidecar referenciado; no WSL, validar a resolução e o supervisor com binário fake.

**Acceptance Scenarios**:

1. **Given** a documentação desta feature, **When** um desenvolvedor a segue no host Windows de referência, **Then** obtém o binário do agent no local esperado pelo shell/bundler.
2. **Given** o monorepo no modo Developer (WSL), **When** se rodam os testes automatizados desta feature, **Then** passam sem GPU, sem WASAPI real e sem instalador assinado (P10).

---

### Edge Cases

- Sidecar presente **e** agent no PATH: o shell preferirá o sidecar empacotado quando o empacotamento indicar distribuição “com sidecar”; em modo Developer sem sidecar no pacote, usa PATH. Se ambos existirem em build de produto, a prioridade é **sidecar do app** > override de config/env > PATH (nunca silenciar qual foi escolhido no status).
- Dois processos agent já em execução: manter a regra atual de “already running” — não iniciar um segundo.
- Shell crash / kill -9: best-effort; não exige watchdog de OS nesta fatia (fora de escopo: serviço Windows / restart automático).
- Profile path inválido: falha de start explícita (processo sai imediatamente), reutilizando taxonomia de erro já existente quando possível.
- `sessionId` vazio: não iniciar; reutilizar guards de 020/021.
- Versão do sidecar diverge do `VERSION` do monorepo: reportar ambas quando possível; **não** bloquear start só por divergência nesta fatia (aviso observável basta).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O shell MUST ser capaz de localizar o binário do agent de áudio segundo uma ordem de prioridade documentada: (1) binário sidecar empacotado com a aplicação, (2) caminho explícito de configuração/override, (3) PATH do sistema (modo Developer).
- **FR-002**: O shell MUST expor no status do agent qual origem de binário foi resolvida (sidecar / config / PATH / não encontrado), de forma observável pelo operador ou por testes.
- **FR-003**: Quando o start for solicitado e um binário válido for resolvido, o shell MUST iniciar `run` com o `sessionId` e o profile da sessão ativa, preservando o alinhamento de sessão de `specs/020-issue-47-sessionid-align/`.
- **FR-004**: O shell MUST obter e expor a versão do binário resolvido (via mecanismo de versão do próprio agent) quando disponível; se indisponível, MUST marcar versão como desconhecida sem inventar valor.
- **FR-005**: Enquanto o agent estiver sob handle gerenciado pelo shell, o status MUST refletir saúde com base na vida do processo (saudável se em execução; não saudável/parado se saiu).
- **FR-006**: No encerramento normal do shell, o supervisor MUST encerrar processos do agent que o shell iniciou (handle gerenciado) e MUST NOT encerrar processos do agent detectados apenas por enumeração (Guided/externos).
- **FR-007**: Falhas de resolução ou start MUST continuar tipadas de forma acionável (binário ausente, já em execução, saiu imediatamente, erro de SO), estendendo a taxonomia de 014 quando necessário (ex.: sidecar declarado mas arquivo faltando).
- **FR-008**: O modo Developer (agent via PATH/venv, WSL/Docker para STT/session-core) MUST continuar funcionando sem exigir o artefato de sidecar.
- **FR-009**: O projeto MUST documentar como gerar o artefato do agent para empacotamento e como o bundler do shell o referencia.
- **FR-010**: Esta feature MUST NOT empacotar o serviço de transcrição, o session-core JVM, modelos de STT/LLM, nem o provider-gateway — apenas o agent de áudio Windows como sidecar.
- **FR-011**: Esta feature MUST NOT implementar assinatura de código, auto-update, ícone de bandeja, tela de diagnóstico completa de GPU, nem armazenamento seguro de credenciais (permanecem em 002 / fatias futuras).
- **FR-012**: Testes automatizados MUST validar resolução de binário, health/versão e shutdown coordenado sem hardware WASAPI e sem GPU (P10).
- **FR-013**: Captura WASAPI e isolamento por endpoint MUST permanecer responsabilidade exclusiva do agent Python no Windows (ADR-0003/0007); o shell apenas supervisiona o processo.

### Key Entities

- **Audio agent sidecar**: artefato executável do `assistant-hub-audio` distribuído junto com o shell para uso em produto Desktop, distinto da instalação Developer via PATH/venv.
- **Binary resolution result**: caminho absoluto (ou identificador) do binário escolhido + origem (sidecar / config / PATH / missing).
- **Supervised agent lifecycle**: estado do processo gerenciado pelo shell (não iniciado, saudável, não saudável, parando, parado) + versão conhecida ou desconhecida.
- **Sidecar packaging recipe**: passos e locais de arquivo para produzir e embutir o sidecar no pacote do shell.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em cenário de produto (PATH sem o agent, sidecar presente), o operador inicia a captura a partir do shell com sucesso em menos de 30 segundos após ter sessão e profile válidos.
- **SC-002**: 100% dos starts bem-sucedidos pelo shell reportam a origem do binário usada (sidecar, config ou PATH), verificado por teste automatizado.
- **SC-003**: 100% dos processos iniciados pelo shell (handle gerenciado) são encerrados no shutdown normal do shell, verificado por teste automatizado com processo fake.
- **SC-004**: Processos do agent iniciados fora do shell **não** são encerrados pelo shutdown do shell, verificado por teste automatizado ou procedimento documentado.
- **SC-005**: Status de saúde reflete a saída inesperada do processo em no máximo um ciclo de atualização de status do shell (mesmo intervalo de polling já usado para o painel do agent).
- **SC-006**: Suíte automatizada desta feature passa em ambiente sem WASAPI/GPU (WSL ou CI Linux/Windows unit).
- **SC-007**: Documentação permite a um segundo desenvolvedor gerar o artefato do sidecar no host Windows de referência sem passos não escritos.

## Assumptions

- O shell Tauri de 014 já existe e controla o agent via start/stop com handle opcional; esta fatia **evolui** esse controle para resolução de sidecar + supervisor de saída, sem reescrever o domínio de sessão/transcript.
- “Health check” nesta fatia significa vida do processo + versão do binário; não inclui probe de microfone/WASAPI (isso permanece no `probe` do agent).
- Override de caminho por variável de ambiente ou config local do shell é aceitável e preferível a hardcode de path de usuário.
- Empacotamento real do `.exe` Windows do agent (PyInstaller ou equivalente) roda no host Windows; no WSL validamos lógica e contrato de paths com binários fake.
- Fechar o shell **passa a** encerrar o agent gerenciado (mudança consciente em relação à nota de 014 de que fechar o shell “não deve necessariamente” matar o agent): para sidecar de produto, o default seguro é não deixar captura órfã. Processos externos/Guided permanecem intocados.

## Out of Scope

- Sidecars de transcription-service, session-core ou provider-gateway.
- Auto-restart do agent após crash.
- Serviço Windows (SCM) ou início no login.
- Assinatura Authenticode / update channel.
- Microsoft Store.
- Empacotar runtimes Python completos além do necessário para o entrypoint do agent (detalhe de packaging no plan, não na UX).
