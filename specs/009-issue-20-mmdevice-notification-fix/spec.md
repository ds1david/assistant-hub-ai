# Feature Specification: Correção do provider real de notificação MMDevice (Issue #20)

**Feature Branch**: `009-issue-20-mmdevice-notification-fix`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Issue de bug (código — próximo ciclo SDD curto): SF-019: provider real quebra sem comtypes.gen.MMDeviceAPILib. Sintoma: `run --session ... --profile ...` → worker exit 1 em `HotplugListener.__init__`. Causa: `mmdevice_notifications.py` importava `IMMNotificationClient` de `comtypes.gen.MMDeviceAPILib`, módulo que pip/pycaw não geram; `GetModule(mmdevapi.dll)` falha (sem typelib). Direção de correção: definir `IMMNotificationClient` via comtypes manual (GUID + COMMETHOD), sem depender de gen; falha deve ser explícita e, se possível, não matar captura sem política clara; smoke documentado no quickstart Windows. Evidência: docs/validation/sf-019-windows.md (2026-07-22)."

## Clarifications

### Session 2026-07-22

- Q: Quando `provider.subscribe(...)` falha, o listener deve tentar se reinscrever depois, ou ficar permanentemente inerte pelo tempo de vida do processo do canal? → A: Degrade permanente para o processo do canal — uma única tentativa em `HotplugListener.__init__`, sem retry (mantém a implementação atual em `hotplug.py`).
- Q: O estado degradado (hot-plug desabilitado por falha de assinatura) deve ser visível só no log local do worker, ou também sinalizado para fora do processo (session-core/dashboard)? → A: Apenas log local — mesmo padrão já usado em `get_notification_provider`; sinalização cross-processo é fora de escopo desta correção retroativa.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Worker de captura sobrevive à inicialização do listener em Windows real (Priority: P1)

Um operador roda o agente de áudio (`run --session ... --profile ...`) em um host Windows real, com hot-plug habilitado (feature SF-019, `specs/006-sf-019-hotplug-listener/`). Hoje, o processo do canal morre (`exit 1`) assim que `HotplugListener.__init__` tenta assinar notificações do MMDevice, porque o código depende de um módulo (`comtypes.gen.MMDeviceAPILib`) que nunca é gerado (a DLL `mmdevapi.dll` não embute typelib). O operador precisa que o worker continue de pé e a captura funcione, com o hot-plug realmente ativo — não apenas em testes com fake provider.

**Why this priority**: É a quebra relatada na issue #20 e bloqueia o único caminho real (não simulado) da feature SF-019 em produção; sem isso, hot-plug nativo não existe fora dos testes.

**Independent Test**: Em um host Windows com o agente instalado, executar os passos "run + hot-plug" do quickstart (`specs/006-sf-019-hotplug-listener/quickstart.md`) e observar que o worker permanece ativo e captura áudio após a construção do `HotplugListener`, sem `ModuleNotFoundError`.

**Acceptance Scenarios**:

1. **Given** um host Windows com `pycaw`/`comtypes` instalados e sem typelib gerado para `mmdevapi.dll`, **When** o worker de canal instancia `HotplugListener` e chama `provider.subscribe(...)`, **Then** a assinatura de notificações é concluída com sucesso e o worker continua capturando áudio normalmente.
2. **Given** o mesmo host, **When** um dispositivo WASAPI é conectado ou removido durante a sessão, **Then** o evento de hot-plug é recebido e processado como já especificado em `specs/006-sf-019-hotplug-listener/spec.md` (sem regressão de comportamento).

---

### User Story 2 - Falha de assinatura degrada sem derrubar o canal (Priority: P2)

Se, mesmo com a definição manual de `IMMNotificationClient`, a assinatura de notificações falhar por outro motivo ambiental (ex.: permissão COM, versão de SO incompatível), o canal de captura não pode morrer silenciosamente nem propagar uma exceção não tratada até matar o supervisor. O comportamento esperado é: log de aviso explícito e listener inerte (hot-plug desabilitado apenas naquele canal), mantendo a captura de áudio ativa — mesma política já usada quando a própria construção do provider falha.

**Why this priority**: Preserva P6 (isolamento de endpoint — falha de um canal não pode silenciar o supervisor) e evita reintroduzir o mesmo tipo de crash-silencioso que a correção original resolve, mesmo em cenários não previstos.

**Independent Test**: Em teste automatizado (WSL, sem hardware), injetar uma falha em `provider.subscribe(...)` de um `FakeNotificationProvider`/mock e verificar que `HotplugListener.__init__` não propaga a exceção, loga aviso, e o restante da captura do canal continua funcionando.

**Acceptance Scenarios**:

1. **Given** um `NotificationProvider` cujo `subscribe(...)` levanta uma exceção, **When** `HotplugListener` é construído, **Then** a exceção é capturada, um aviso é logado, e o listener fica inerte (sem levantar exceção para o chamador).
2. **Given** o listener inerte por falha de assinatura, **When** a captura de áudio do canal continua rodando, **Then** não há impacto no fluxo de captura (leitura de stream, reconexão) além da ausência de eventos de hot-plug.

---

### User Story 3 - Evidência de validação manual em Windows real atualizada (Priority: P3)

Como mantenedor responsável por aprovar o fechamento da issue #20 dentro do ciclo SDD curto, preciso que a validação manual documentada em `docs/validation/sf-019-windows.md` reflita o resultado real da correção contra hardware/COM Windows — hoje a seção "run + hot-plug" está com o resultado antigo de FAIL e uma pendência explícita de revalidação.

**Why this priority**: Cumpre P10 (qualidade determinística — validação manual documentada com ambiente, commit, passos e resultado) e é o critério de saída do gate G3 (Validate) antes de PR/merge.

**Independent Test**: Repetir os passos 1–8 do quickstart Windows com a correção aplicada e atualizar `docs/validation/sf-019-windows.md` com o novo resultado (PASS ou, se ainda falhar, a nova causa raiz).

**Acceptance Scenarios**:

1. **Given** a correção aplicada em um host Windows real, **When** os passos do quickstart são reexecutados, **Then** o resultado (PASS/FAIL) e a data são registrados em `docs/validation/sf-019-windows.md`, substituindo a pendência atual.

---

### Edge Cases

- O que acontece em ambiente não-Windows (Linux/WSL), onde o `NullNotificationProvider` é usado? Nenhum impacto — a correção é isolada ao provider real Windows-only, importado de forma lazy.
- O que acontece se a definição manual de `IMMNotificationClient` (IID/assinaturas COM) divergir da versão do Windows SDK do host? Deve cair na mesma política de degrade explícito (User Story 2), não em crash silencioso ou trava do worker.
- O que acontece se `RegisterEndpointNotificationCallback` suceder mas o enumerator já tiver sido liberado/inválido por outro motivo? Mesma política de degrade de assinatura (não é um caso novo, é coberto pelo mesmo tratamento de exceção).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O provider real de notificação (Windows) MUST definir `IMMNotificationClient` sem depender de geração de typelib em runtime (`comtypes.client.GetModule`); a interface COM MUST ser declarada estaticamente (IID fixo do SDK + `comtypes.STDMETHOD`) em `mmdevice_notifications.py`.
- **FR-002**: Quando `provider.subscribe(...)` levantar qualquer exceção durante `HotplugListener.__init__`, o sistema MUST capturar a exceção, logar um aviso explícito no log local do worker (sem sinalização cross-processo nesta correção) e deixar o listener em estado inerte de forma permanente para o tempo de vida do processo do canal (sem retry de reinscrição), em vez de propagar a exceção e derrubar o worker do canal.
- **FR-003**: A política de degrade em caso de falha de assinatura MUST ser consistente com a política já existente para falha de construção do provider (`get_notification_provider`), preservando a mesma filosofia de falha explícita sem crash silencioso (P3/P10); nenhuma das duas políticas reintenta automaticamente.
- **FR-004**: A suíte de testes automatizados MUST incluir um teste de regressão comprovando que uma falha em `subscribe()` degrada sem propagar exceção (equivalente a `test_listener_subscribe_failure_degrades_without_raising`).
- **FR-005**: A correção MUST ser revalidada manualmente em host Windows real seguindo os passos "run + hot-plug" de `specs/006-sf-019-hotplug-listener/quickstart.md`, com o resultado (PASS/FAIL) registrado em `docs/validation/sf-019-windows.md`.
- **FR-006**: A correção MUST NOT introduzir nova dependência de runtime (ex.: `winrt`) além de `comtypes`/`pycaw` já usados pelo projeto.
- **FR-007**: O comportamento de hot-plug já especificado em `specs/006-sf-019-hotplug-listener/spec.md` (detecção de conexão/remoção, debounce, isolamento por canal) MUST permanecer inalterado para quem usa o provider real corrigido.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em host Windows real, iniciar `run` com hot-plug habilitado não resulta mais em encerramento do worker (`exit 1`) durante a construção do listener de notificações.
- **SC-002**: 100% da suíte automatizada de hot-plug/captura continua passando após a correção (suíte completa sem regressão).
- **SC-003**: Zero novas dependências externas de runtime adicionadas para detecção/assinatura de eventos de hot-plug.
- **SC-004**: `docs/validation/sf-019-windows.md` reflete um resultado final (PASS ou nova causa raiz documentada) para a seção "run + hot-plug", sem pendência de revalidação em aberto.

## Assumptions

- A correção é isolada ao caminho do provider real Windows (`mmdevice_notifications.py`/`hotplug.py`); os providers `Null`/`Fake` usados na suíte automatizada (WSL, sem hardware) não são afetados e continuam sendo a cobertura primária de testes (P10).
- O IID e as assinaturas de método de `IMMNotificationClient` usados na definição manual vêm do SDK público do Windows (`mmdeviceapi.h`) e são estáveis nas versões de Windows alvo do projeto.
- Esta spec formaliza, de forma retroativa e dentro do "próximo ciclo SDD curto" citado na issue #20, uma correção já aplicada na árvore de trabalho (`mmdevice_notifications.py`, `hotplug.py`, `test_hotplug.py`) — o objetivo do ciclo é fechar o gate de especificação (P1) sobre um código já diagnosticado e corrigido, não redesenhar a feature.
- O comportamento mais amplo de hot-plug (debounce, isolamento por canal, tradução de eventos) já está coberto por `specs/006-sf-019-hotplug-listener/` e está fora de escopo aqui — esta spec cobre apenas a correção de inicialização/assinatura do provider real e sua política de falha.

## Gate G1 — Aprovação retroativa

A constituição (P1) exige requisitos, critérios de aceite e fora de escopo em `spec.md` **antes** de código de domínio ser alterado, com gate humano de Spec. Nesta issue, o código (`mmdevice_notifications.py`, `hotplug.py`, `test_hotplug.py`) já havia sido corrigido na árvore de trabalho quando este ciclo de `/speckit-specify` começou (diagnóstico e correção no mesmo dia, dentro do "próximo ciclo SDD curto" da issue #20).

**Decisão do revisor humano (David Oliveira, 2026-07-22)**: esta spec, com as clarificações e o plano subsequentes, é aceita como o fechamento retroativo do gate G1 para esse código já aplicado — cobrindo exatamente o diff existente, sem ampliar escopo. Esta aprovação vale apenas para este ciclo específico (issue #20/SF-019); não estabelece uma exceção geral a P1 para futuros bug fixes, o que exigiria uma atualização explícita da constituição fora deste comando.
