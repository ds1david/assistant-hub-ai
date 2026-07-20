# Research — SF-018 MMDevice endpoint identity

Registro retrospectivo das decisões técnicas do piloto. Nenhum NEEDS CLARIFICATION permanece na spec ou no plano.

## D1 — Fonte de identidade estável do dispositivo

- **Decision**: MMDevice endpoint ID do Windows (`IMMDevice::GetId`), exposto ao usuário como `device.endpointId`.
- **Rationale**: é o identificador que o próprio Windows usa para persistir preferências de dispositivo; sobrevive a reboot, hot-plug e reconexão Bluetooth; único por endpoint mesmo com nomes amigáveis duplicados.
- **Alternatives considered**:
  - *Índice PortAudio* — é exatamente o problema: volátil a cada reenumeração.
  - *FriendlyName/regex* — ambíguo com dispositivos duplicados e sujeito a renomeação por driver/idioma.
  - *Container ID / device instance path (SetupAPI)* — mais estável em reinstalação de driver, porém não mapeia 1:1 para endpoints de áudio (um hardware pode expor vários endpoints) e exigiria outra camada de correlação.

## D2 — Biblioteca de acesso a MMDevice

- **Decision**: `pycaw` (sobre `comtypes`), com marker `sys_platform == 'win32'` e import tardio dentro do provider.
- **Rationale**: já embala a enumeração MMDevice/COM necessária; o marker + import tardio garantem que Linux/CI nunca carregam dependência win32 (P3, P10).
- **Alternatives considered**:
  - *comtypes puro* — mais controle, muito mais código COM manual para o mesmo resultado.
  - *pywin32* — dependência maior e API menos direta para endpoints de áudio.
  - *Chamar PowerShell/registry* — frágil, dependente de idioma/versão do Windows.

## D3 — Ponte endpoint ↔ dispositivo de captura

- **Decision**: correlação estrutural em lógica pura (`endpoints.correlate_devices`): host API WASAPI, direção de fluxo, FriendlyName e ordem de enumeração como desempate; WARNING em nomes duplicados.
- **Rationale**: PortAudio não expõe o endpoint ID; a correlação estrutural é o único caminho sem patch nativo. Mantida em função pura para ser testável com fakes em CI Linux.
- **Alternatives considered**:
  - *Patch no PortAudio/PyAudioWPatch para expor IMMDevice* — invasivo, custo de manutenção de fork.
  - *Casar apenas por nome* — quebra com duplicados; a ordem de enumeração como desempate reduz a ambiguidade e é determinística por reenumeração.
- **Limite reconhecido**: heurística, não garantia absoluta — documentado na spec (Assumptions) e nos riscos do plano.

## D4 — Semântica de falha de resolução

- **Decision**: quatro erros distintos (endpoint inexistente; inativo; fluxo incompatível; ativo sem correlação), todos fatais para o canal, com sugestão de `list-devices --json`; nenhum fallback para `index`/`nameRegex`/`default`.
- **Rationale**: fallback silencioso reproduziria o defeito original (capturar o dispositivo errado sem erro); constituição P7 proíbe. Erros distintos tornam o diagnóstico acionável.
- **Alternatives considered**:
  - *Fallback com WARNING* — rejeitado: WARNING passa despercebido em serviço headless; risco de transcrever a fonte errada.
  - *Erro único genérico* — rejeitado: operador não distingue "ID errado no YAML" de "dispositivo desligado".

## D5 — Loopback

- **Decision**: canais de loopback resolvem pelo endpoint de render (`eRender`) original; o dispositivo virtual `[Loopback]` do PyAudioWPatch é correlacionado ao render correspondente.
- **Rationale**: o usuário pensa em "capturar o que sai na caixa X" — a identidade estável pertence ao endpoint de render, não ao dispositivo virtual de captura criado pelo WASAPI loopback.
- **Alternatives considered**: exigir que o usuário descubra o ID do dispositivo virtual — rejeitado por não ser estável nem descobrível via ferramentas padrão do Windows.

## D6 — Transporte do endpointId no contrato

- **Decision**: campo aditivo opcional/anulável `device.endpointId` no `transcript-event.v2` + query param `endpointId` no WebSocket de áudio; sem bump para v3.
- **Rationale**: P4 pede compatibilidade aditiva; consumidores antigos ignoram o campo; produtores sem endpoint (Linux, perfis legados) omitem/enviam null.
- **Alternatives considered**: *schema v3* — rejeitado: custo de migração de todos os consumidores para um único campo opcional.

## D7 — Convivência de seletores no perfil

- **Decision**: `endpointId` pode coexistir com `index` no YAML; prioridade `endpointId` > `index` > `default`/`nameRegex`; combinações inválidas rejeitadas na validação do perfil.
- **Rationale**: permite um único perfil servir agentes novos e antigos durante a transição (agentes antigos ignoram a chave desconhecida).
- **Alternatives considered**: exclusividade mútua dos seletores — rejeitada: forçaria perfis separados por versão de agente durante o rollout.

## D8 — Estratégia de teste sem hardware

- **Decision**: protocolo de provider com `NullEndpointProvider` (não-Windows) e fakes em teste; lógica de correlação/resolução pura testada em pytest no Linux; validação com hardware real apenas manual e documentada.
- **Rationale**: P10 exige testes determinísticos sem hardware; a fronteira COM fica fina e o restante é 100% testável em CI.
- **Alternatives considered**: CI self-hosted Windows com áudio — rejeitado nesta fase: custo/flakiness altos; smoke de import/CLI cobre a regressão de empacotamento.
