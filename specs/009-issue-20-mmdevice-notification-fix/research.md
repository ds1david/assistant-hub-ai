# Research: Correção do provider real de notificação MMDevice (Issue #20)

## 1. Causa raiz e mecanismo de correção do `IMMNotificationClient`

**Decision**: `IMMNotificationClient` deixa de ser importado de `comtypes.gen.MMDeviceAPILib` (módulo
gerado sob demanda por `comtypes.client.GetModule` a partir de um typelib) e passa a ser declarado
estaticamente em `mmdevice_notifications.py`, com o IID fixo do Windows SDK (`mmdeviceapi.h`) e os
métodos COM via `comtypes.STDMETHOD`, na ordem exata da vtable da interface.

**Rationale**: `mmdevapi.dll` não embute typelib, então `GetModule('mmdevapi.dll')` falha em runtime real
(`OSError: [WinError -2147312566]`) e o import de `comtypes.gen.MMDeviceAPILib` nunca resolve
(`ModuleNotFoundError`), derrubando o worker em `HotplugListener.__init__` (evidência:
`docs/validation/sf-019-windows.md`, execução Windows 2026-07-22). `pycaw`/`comtypes` resolvem
`IMMDeviceEnumerator`/`IMMDevice` (já usados em `mmdevice.py`), mas não vendorizam
`IMMNotificationClient` — a premissa original de `specs/006-sf-019-hotplug-listener/research.md`
(seção 1) estava incompleta nesse ponto. Declarar a interface estaticamente remove por completo a
dependência de geração de typelib, em vez de tentar contornar sua ausência.

**Alternatives considered**:
- **Gerar/commitar um wrapper determinístico no install**: rejeitado — ainda dependeria de uma etapa de
  geração (`GetModule`) que falha pela mesma causa raiz (ausência de typelib na DLL); não resolve o
  problema, só adia.
- **Depender de uma lib de terceiros que já vendoriza `IMMNotificationClient`**: rejeitado — introduziria
  uma dependência de runtime nova (viola FR-006/P2) para resolver algo que `comtypes.STDMETHOD` já
  resolve com a infraestrutura COM já em uso.

Este é o mesmo research já registrado (com mais detalhe técnico da interface COM) em
`specs/006-sf-019-hotplug-listener/research.md` (seção "Correção (SF-019, validação Windows
2026-07-22)"); não é duplicado aqui além do necessário para o histórico desta feature.

## 2. Política de falha na assinatura (retry vs. degrade permanente)

**Decision**: falha em `provider.subscribe(...)` durante `HotplugListener.__init__` é capturada, logada
como aviso e deixa o listener permanentemente inerte para o tempo de vida do processo do canal — sem
retry de reinscrição (Clarifications 2026-07-22, Q1).

**Rationale**: mantém a implementação já existente em `hotplug.py` (uma única tentativa, sem laço de
retry) e a mesma filosofia de degrade já usada em `get_notification_provider` para falha de construção
do provider — consistente com P3/P10 (falha explícita, sem crash silencioso, sem complexidade nova de
retry/backoff que o escopo desta correção de bug não pede).

**Alternatives considered**:
- **Retry periódico dentro do mesmo processo**: rejeitado — adicionaria estado (temporizador, contador
  de tentativas) e um novo modo de falha (retry indefinido) para um cenário sem evidência de ser
  transitório; fora do escopo de uma correção pontual de bug.
- **Retry único após atraso fixo**: rejeitado pelo mesmo motivo, com complexidade adicional
  desproporcional ao benefício não demonstrado.

## 3. Escopo de observabilidade do estado degradado

**Decision**: o estado degradado (hot-plug desabilitado por falha de assinatura) é visível apenas via
log local de warning no processo do worker — nenhuma sinalização cross-processo (session-core,
dashboard) é adicionada por esta correção (Clarifications 2026-07-22, Q2).

**Rationale**: replica o padrão já estabelecido em `get_notification_provider` (mesmo nível de log,
mesmo alcance) e mantém o escopo da correção limitado ao bug relatado na issue #20; expor esse estado a
sistemas externos seria uma feature de observabilidade nova, não uma correção de bug.

**Alternatives considered**:
- **Sinal visível no session-core/dashboard**: rejeitado para esta correção — ampliaria o escopo para
  uma feature de observabilidade cross-processo, exigindo novo contrato de evento (P4) fora do que a
  issue #20 pede.
- **Métrica/contador estruturado local**: rejeitado pelo mesmo motivo de escopo; pode ser proposto como
  feature futura independente, se necessário.
