# Research: Captura de áudio por processo (WASAPI loopback por app, SF-020)

## 1. API Windows para loopback de áudio por processo

**Decision**: usar `ActivateAudioInterfaceAsync` (declarado manualmente via `comtypes`, sem depender de
geração de typelib — mesmo padrão de `mmdevice_notifications.py`/SF-019) com
`AUDIOCLIENT_ACTIVATION_PARAMS` (`ActivationType = AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK`,
`TargetProcessId = <pid resolvido>`, `ProcessLoopbackMode = PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE`
por padrão) para obter um `IAudioClient` escopado ao processo alvo (e sua árvore de processos-filho),
depois consumido via `IAudioCaptureClient` como qualquer captura loopback WASAPI já existente.

**Rationale**: é a API pública documentada pela Microsoft para este propósito exato — nenhuma outra rota
suportada existe. `INCLUDE_TARGET_PROCESS_TREE` (em vez de excluir a árvore) é o modo certo por padrão
porque muitos aplicativos relevantes (ex.: navegadores) renderizam áudio a partir de processos-filho
(ex.: processo de renderer de uma aba), não do processo principal — selecionar só o PID exato sem a
árvore perderia áudio real de "o aplicativo" como o operador o entende. `PyAudioWPatch`/`pycaw`
(dependências já existentes) não expõem esta API — nenhuma library Python madura e mantida a expõe hoje
(bibliotecas de terceiros existem — ex. ProcTap, ProcessAudioCapture — mas nenhuma é dependência atual
do projeto); declarar manualmente via `comtypes` segue a mesma decisão arquitetural já validada em
SF-019 (P2 — core independente de fornecedores, sem SDK de terceiros novo).

**Requisito de versão do Windows**: `ActivateAudioInterfaceAsync`/`AUDIOCLIENT_ACTIVATION_PARAMS` exige
no mínimo Windows 10 build 20348 (Windows 10 21H2/Windows Server 2022) para o modo
`INCLUDE_TARGET_PROCESS_TREE`; builds mais antigas (a partir de 19041/2004) suportam a ativação básica
por processo mas sem controle de árvore. Isso é uma versão mínima mais recente que a já exigida por
SF-018/SF-019 (que não têm requisito de build específico documentado) — resolve a Assumption
correspondente de `spec.md`.

**Alternatives considered**:
- **Bibliotecas de terceiros (ProcTap, ProcessAudioCapture)**: rejeitado — adicionaria dependência
  externa nova para algo que a API pública do Windows já permite declarar manualmente, mesma decisão de
  SF-019/FR-006 (daquela spec) de não introduzir SDK de terceiros.
- **`PROCESS_LOOPBACK_MODE_EXCLUDE_TARGET_PROCESS_TREE`** (capturar tudo exceto o processo): rejeitado —
  é o modo inverso, usado para "silenciar meu próprio app na gravação da tela", não para "capturar só
  este app", que é exatamente o que a issue #19 pede.
- **`GetMixFormat`/`Initialize` sem `ActivateAudioInterfaceAsync`** (tentar abrir o processo como um
  device comum): rejeitado — não existe; a ativação por processo é obrigatoriamente assíncrona via
  `ActivateAudioInterfaceAsync` com um `IActivateAudioInterfaceCompletionHandler` (nova interface COM a
  implementar manualmente, mesmo padrão de `IMMNotificationClient`).

Fontes: [ActivateAudioInterfaceAsync function (mmdeviceapi.h) — Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nf-mmdeviceapi-activateaudiointerfaceasync), [AUDIOCLIENT_ACTIVATION_PARAMS — Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/api/audioclientactivationparams/ns-audioclientactivationparams-audioclient_activation_params), [PROCESS_LOOPBACK_MODE — Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/api/audioclientactivationparams/ne-audioclientactivationparams-process_loopback_mode), [Application loopback audio capture sample — Microsoft Learn](https://learn.microsoft.com/en-us/samples/microsoft/windows-classic-samples/applicationloopbackaudio-sample/).

## 2. Caminho de captura separado de `PyAudioWPatch`

**Decision**: canais por processo MUST usar um caminho de captura inteiramente novo e isolado
(módulo Windows-only, import lazy — ex. `process_capture.py`, mesmo padrão de `mmdevice_notifications.py`),
que não reaproveita `audio.open()`/`stream.read()` de `PyAudioWPatch` — o `IAudioClient` obtido via
`ActivateAudioInterfaceAsync` é consumido diretamente via `IAudioCaptureClient` (buffers PCM lidos por
COM, não pela API do PyAudio).

**Rationale**: `PyAudioWPatch`/PortAudio não sabem ativar um `IAudioClient` escopado a processo — o
objeto retornado por `ActivateAudioInterfaceAsync` não tem um "índice de device PortAudio"
correspondente (não aparece em `audio.get_device_info_generator()`). Forçar isso através do PyAudio
exigiria um wrapper/patch da própria biblioteca; manter os dois caminhos de captura separados
(dispositivo via PyAudioWPatch, processo via COM manual) é mais simples e não arrisca quebrar o caminho
de dispositivo já validado (FR-007).

**Alternatives considered**:
- **Fazer `PyAudioWPatch` reconhecer um device virtual por processo**: rejeitado — exigiria modificar ou
  fazer fork da dependência de terceiros; fora de escopo e de controle do projeto.
- **Unificar os dois caminhos atrás de uma única abstração de "stream" desde já**: rejeitado por agora —
  prematuro; `capture.py` já isola a diferença por `channel.selector` tendo um tipo de seletor
  (`process_id`/`process_name`) — a ramificação para o caminho certo de captura acontece no worker,
  análogo a como `hotplug.py`/`mmdevice_notifications.py` já se mantêm separados por responsabilidade.

## 3. Resolução de processo por PID ou nome

**Decision**: usar `psutil` (já dependência transitiva via `pycaw>=20240210`, confirmada instalada no
venv Windows real do projeto) para enumerar processos (`psutil.process_iter(["pid", "name", "username"])`)
e resolver o seletor. **Correção de escopo**: `pycaw` é declarado em `pyproject.toml` com marcador
`sys_platform == 'win32'`, então hoje `psutil` só entra na árvore de dependências em Windows — como
`process_resolver.py` é deliberadamente multiplataforma (testável em WSL, research.md/plan.md), `psutil`
MUST passar a ser uma dependência direta e sem marcador de plataforma em `pyproject.toml` (não apenas
transitiva), para que a suíte automatizada consiga instalá-la e importá-la em WSL/CI. Isso não muda a
escolha da biblioteca em si (`psutil` continua sendo a mesma, já em uso pelo `pycaw`), só formaliza sua
declaração — tratado como task de Setup em `tasks.md`.
- Por PID: `psutil.Process(pid)` — existe e está rodando, ou falha (FR-005).
- Por nome: filtrar processos cujo `name()` corresponda (case-insensitive) ao nome configurado; exatamente
  um resultado resolve, zero ou mais de um falha explicitamente (FR-005, mesma política de ambiguidade de
  `nameRegex` em `endpoints.py`).
- Restrição de usuário (FR-011, Clarifications): comparar `psutil.Process(pid).username()` do processo
  alvo com o usuário do processo atual (`psutil.Process().username()`); processos de outro usuário ou
  marcados como processo de sistema (sem `username()` resolvível, ou SID de sistema) MUST falhar
  explicitamente na resolução, nunca silenciosamente ignorar a checagem.

**Rationale**: `psutil` já está presente no ambiente Windows real do agente (instalado transitivamente),
então não introduz nenhuma dependência nova (mesma disciplina de FR-006 de SF-019, mesmo não sendo um
requisito explícito desta spec) — e é multiplataforma, o que permite testar a lógica de resolução (não a
captura de áudio em si) inteiramente em WSL com processos reais do próprio processo de teste, sem fakes
para essa parte específica.

**Alternatives considered**:
- **`os`/`ctypes` diretos (`OpenProcess`, `EnumProcesses` via `psapi.dll`)**: rejeitado — reimplementaria
  em baixo nível o que `psutil` já oferece de forma testável e já presente no ambiente.
- **Resolver só por nome, sem suporte a PID**: rejeitado — a issue #19 pede explicitamente as duas formas
  de seleção (PID ou nome).

## 4. Re-seguimento automático por nome após restart (FR-012)

**Decision**: o worker do canal por processo, ao detectar que o PID atual saiu da lista de processos
vivos (`psutil.pid_exists(pid)` retorna `False`, ou a sessão de áudio ativada falha porque o processo já
não existe), MUST, se o canal foi configurado por **nome**, tentar re-resolver o nome imediatamente (mesma
regra de unicidade de FR-005): uma única nova correspondência retoma a captura no novo PID; zero ou mais
de uma correspondência é tratado como falha explícita (mesmo caminho de `EndpointResolutionError`
permanente já usado para o caso "nunca existiu", adaptado ao domínio de processo). Para canais
selecionados por **PID**, nenhuma re-resolução é tentada — a saída do processo é sempre uma falha
terminal para aquele canal (FR-006).

**Rationale**: reaproveita a mesma filosofia arquitetural já validada em `capture_channel`/SF-019 (loop
com backoff, distinção entre falha permanente vs. transitória, sem introduzir uma máquina de estados
nova) — a diferença de comportamento entre seleção por PID e por nome é uma condição no mesmo ponto de
decisão que hoje já existe (`except EndpointResolutionError`), não uma arquitetura paralela.

**Alternatives considered**:
- **Reaproveitar literalmente `ChannelHotplugSignal`/`HotplugListener` (SF-019) para eventos de
  processo**: rejeitado — aquele mecanismo é acoplado a notificações COM de dispositivo MMDevice
  (`IMMNotificationClient`), que não emite eventos de ciclo de vida de processo; a detecção de saída de
  processo usa `psutil`, um mecanismo de poll simples, mais barato de implementar corretamente aqui do
  que forçar reaproveitamento de uma abstração de notificação nativa que não se aplica a este domínio.

## 5. Metadados de transcrição v2 (FR-003) — decisão final de schema

**Decision**: **nenhuma mudança de schema é necessária.** Canais por processo populam
`transcript-event.v2` com `sourceType: "system"` (mesma categoria de captura de renderização/loopback já
usada por canais `kind="loopback"`) e `device.index: null`, `device.endpointId: null`,
`device.name: "<nome ou PID legível do processo>"` (ex.: `"chrome.exe (pid 8842)"`) — todos os três já são
tipos aceitos pelo schema atual (`index`/`endpointId` já são `["integer"/"string", "null"]`, `name` é
`["string", "null"]`). Nenhum campo novo (`processId`/`processName`) é adicionado ao objeto `device`.

**Rationale**: resolve a favor da opção mais simples a Assumption de `spec.md` que deixava em aberto
"novo valor de enum vs. campo adicional" — na prática, nenhum dos dois é necessário. Evita qualquer
mudança em `contracts/transcript-event.v2.schema.json` (arquivo compartilhado, P4), evitando o overhead
de governança de contrato (testes de contrato, samples, possível ADR) para uma feature cujo próprio
critério de aceite já diz "metadados v2 preservados" — preservado literalmente, não estendido. Ver
`contracts/README.md` desta feature.

**Alternatives considered**:
- **Adicionar `processId`/`processName` opcionais em `device`**: rejeitado por agora — daria aos
  consumidores (dashboard) um campo estruturado em vez de um texto livre em `device.name`, mas exigiria
  mudança no contrato compartilhado (`additionalProperties: false` no objeto `device` de
  `transcript-event.v2.schema.json`) sem necessidade comprovada por esta issue; pode ser proposto como
  melhoria futura independente, com seu próprio ciclo de spec/PR, se um consumidor real precisar do campo
  estruturado.
- **Novo valor de `sourceType` (ex. `"process"`)**: rejeitado — mudaria um enum já `required` e
  consumido por `session-core`/dashboard (risco de quebra em validadores estritos que não conhecem o
  valor novo), sem necessidade: "system" já descreve corretamente uma captura de renderização de áudio,
  processo incluso.
