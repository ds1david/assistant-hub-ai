# Feature Specification: SF-015 — Matriz manual de hardware R1

**Feature Branch**: `feature/sf-015-sf-015-matriz-manual-de-hardware-r1`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "SF-015 — Matriz manual de hardware R1: validar captura multicanal em conference cam, Bluetooth e microfone USB, sem regressão de channelId/sourceType, e fechar retroativamente a lacuna de evidência da SF-018 (docs/validation/sf-018-windows.md ainda é template em branco)."

## User Scenarios & Testing *(mandatory)*

<!--
  Esta feature é validação manual, não código. Cada "user story" abaixo é um
  cenário de hardware real executado no Windows contra o windows-audio-agent,
  cujo resultado é a evidência gravada em docs/validation/.
-->

### User Story 1 - Cenário conference cam (Priority: P1)

Como responsável pela estabilidade do R1, executo a captura multicanal com uma conference cam (microfone + saída/loopback do mesmo dispositivo) usando o `windows-audio-agent`, para confirmar que `channelId`, `sourceType` e `endpointId` permanecem corretos e sem vazamento de eco entre canal local e remoto.

**Why this priority**: É o hardware mais comum em chamadas reais e o cenário onde loopback e microfone competem pelo mesmo dispositivo físico — maior risco de regressão de canal.

**Independent Test**: Pode ser testado isoladamente conectando uma conference cam, rodando `list-devices`, `probe` e `run` com um perfil dedicado, e registrando o resultado em `docs/validation/`. Não depende dos outros cenários.

**Acceptance Scenarios**:

1. **Given** uma conference cam conectada e reconhecida pelo Windows, **When** executo `assistant-hub-audio run` com perfil apontando para o `endpointId` da conference cam, **Then** o evento v2 emitido preserva `endpointId`, `channelId` e `sourceType` corretos para microfone e loopback.
2. **Given** a mesma sessão em andamento, **When** falo frases de referência simultaneamente ao áudio remoto reproduzido pela conference cam, **Then** a supressão de eco no feed de transcrição evita duplicação óbvia da fala remota no canal local, e a limitação (se houver) é documentada.

---

### User Story 2 - Cenário Bluetooth output + microfone USB (Priority: P2)

Como responsável pela estabilidade do R1, executo a captura com saída de áudio Bluetooth e um microfone USB dedicado como dispositivos separados, para confirmar que a correlação por `endpointId` não se confunde entre dispositivos de fabricantes/tecnologias diferentes.

**Why this priority**: Cobre o caso de dispositivos heterogêneos (protocolos diferentes) e nomes potencialmente duplicados/genéricos, que é o cenário de maior risco de erro de enumeração citado no ADR de identidade de dispositivo.

**Independent Test**: Pode ser testado isoladamente parelhando um dispositivo Bluetooth de saída e conectando um microfone USB, rodando a mesma sequência de comandos e registrando resultado próprio.

**Acceptance Scenarios**:

1. **Given** um dispositivo de saída Bluetooth pareado e um microfone USB conectado, **When** rodo `list-devices --json`, **Then** ambos aparecem com `endpointId` distintos e corretamente correlacionados ao dispositivo WASAPI certo.
2. **Given** a sessão de captura rodando com esse par de dispositivos, **When** ocorre reconexão do Bluetooth durante a sessão, **Then** o comportamento (sucesso ou falha) é compreensível e documentado, sem fallback silencioso para outro dispositivo.

---

### User Story 3 - Cenário microfone default + fechamento retroativo da SF-018 (Priority: P1)

Como responsável pela estabilidade do R1, executo o cenário de microfone default (sem seleção explícita de dispositivo) e, no mesmo ciclo de testes, preencho as evidências pendentes da SF-018 (`docs/validation/sf-018-windows.md`), já que os mesmos comandos (`list-devices`, `probe`, `run`, reboot/reenumeração, hot-plug parcial, endpoint desabilitado) cobrem os dois objetivos.

**Why this priority**: É o caminho mais simples (sem hardware especial) e é o gate que faltava para considerar a SF-018 evidenciada — bloqueia o checkpoint pós SF-018 enquanto não for feito.

**Independent Test**: Pode ser testado isoladamente sem hardware adicional, usando o microfone default do notebook/desktop, e resulta tanto no cenário 3 desta matriz quanto no preenchimento do resultado da SF-018.

**Acceptance Scenarios**:

1. **Given** nenhum perfil de dispositivo explícito configurado, **When** rodo `assistant-hub-audio run` sem `--profile` apontando dispositivo específico, **Then** o sistema captura o microfone default do Windows e preserva `endpointId`/`channelId`/`sourceType` no evento v2.
2. **Given** os casos de teste do template `docs/validation/sf-018-windows.md` (list-devices, probe, run, reboot/reenumeração, hot-plug parcial, endpoint desabilitado, segurança), **When** executo cada caso, **Then** cada checkbox do template é marcado e o campo `Resultado` é preenchido com PASS, FAIL ou BLOCKED (não mais o placeholder).

---

### Edge Cases

- O que acontece quando um dispositivo listado em um cenário desaparece (é desconectado) no meio da sessão de captura?
- Como o sistema se comporta quando dois dispositivos têm o mesmo nome amigável (ex.: dois microfones USB idênticos)?
- O que acontece quando o `endpointId` configurado no perfil não corresponde a nenhum dispositivo presente no momento do `run`?
- Como o sistema reage a um dispositivo Bluetooth que demora para reconectar após queda de sinal durante a captura?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A matriz de validação MUST documentar pelo menos três cenários de hardware: conference cam, Bluetooth output + microfone USB, e microfone default.
- **FR-002**: Cada cenário MUST registrar `endpointId`, `channelId` e `sourceType` observados para cada dispositivo envolvido, confirmando ausência de regressão em relação aos contratos definidos nas SF-016, SF-017 e SF-018.
- **FR-003**: Cada cenário MUST ter um resultado explícito e único — PASS, FAIL ou BLOCKED — nunca deixado como placeholder ou em branco.
- **FR-004**: Cada cenário MUST registrar latência percebida e presença/ausência de vazamento de eco entre canais.
- **FR-005**: Cada cenário MUST incluir ao menos uma frase de referência falada e sua transcrição observada, associada ao canal correto, para validar a correlação dispositivo → canal.
- **FR-006**: A execução da matriz MUST reaproveitar os mesmos casos de teste para preencher retroativamente `docs/validation/sf-018-windows.md`, deixando seu campo de resultado como PASS, FAIL ou BLOCKED (não mais o template em branco).
- **FR-007**: A validação MUST ser executada manualmente em hardware Windows real; a matriz MUST NOT depender de automação de hardware físico no CI.
- **FR-008**: Quando um cenário não puder ser executado por falta do hardware específico, o resultado MUST ser registrado como BLOCKED com a limitação explicada, em vez de omitido.

### Key Entities

- **Cenário de hardware**: um agrupamento de dispositivo(s) físico(s) (ex.: conference cam) e o conjunto de casos de teste executados contra ele; possui um resultado final (PASS/FAIL/BLOCKED).
- **Registro de validação**: a entrada em `docs/validation/` (arquivo por cenário ou seção da matriz) contendo ambiente, dispositivos, casos, frases de referência e resultado.
- **Dispositivo WASAPI**: um endpoint de áudio identificado por `endpointId`, correlacionado a um `channelId`/`sourceType` no evento v2 emitido pelo agente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Os três cenários mínimos (conference cam, Bluetooth output + USB mic, microfone default) têm resultado PASS, FAIL ou BLOCKED registrado ao final de uma única sessão de testes manuais.
- **SC-002**: 100% dos dispositivos testados nos três cenários preservam `endpointId`, `channelId` e `sourceType` corretos, sem nenhum fallback silencioso para outro dispositivo.
- **SC-003**: `docs/validation/sf-018-windows.md` deixa de conter o placeholder `PASS | FAIL | BLOCKED` e passa a ter um resultado único e definitivo, com todos os checkboxes do template marcados ou justificados como não aplicáveis.
- **SC-004**: Nenhuma regressão de supressão de eco é observada nos três cenários sem que a limitação correspondente esteja explicitamente documentada. (Noise gate fica fora do escopo desta matriz de hardware — é validado por perfil, não por identidade de dispositivo.)

## Assumptions

- O executor dos testes tem acesso físico a pelo menos uma conference cam, um par Bluetooth output + microfone USB, e um microfone default — todos em ambiente Windows real (conforme ADR-0003/ADR-0005).
- Caso algum hardware específico não esteja disponível no momento da execução, o cenário correspondente é registrado como BLOCKED com a limitação explicada, em vez de bloquear a matriz inteira.
- Esta feature não introduz código de produção; eventual script de apoio à validação (se necessário) fica fora do escopo de release e não requer testes automatizados no CI.
- Os contratos de `channelId`/`sourceType`/`endpointId` já estabelecidos nas SF-016, SF-017 e SF-018 são a referência de "sem regressão" usada nesta validação, e não serão redefinidos aqui.
