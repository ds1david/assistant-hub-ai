# Research: Correção de aridade do callback COM e de `notpresent` fatal (SF-019, Issue #22)

## 1. Causa raiz do Bug A (aridade do callback `IMMNotificationClient`)

**Decision**: os métodos `IMMNotificationClient_On*` em `_NotificationClient(COMObject)`
(`mmdevice_notifications.py`) devem aceitar um parâmetro `this` explícito como segundo argumento
posicional — ex.: `def IMMNotificationClient_OnDeviceStateChanged(self, this, device_id, new_state) -> None:`
— sem usá-lo, apenas absorvendo-o. Nenhuma mudança na declaração da interface (`STDMETHOD`, IID) é
necessária.

**Rationale**: inspecionei o código-fonte do pacote `comtypes` instalado (`comtypes/_vtbl.py`,
função `hack()`, linhas ~120-131): quando os métodos de uma interface são declarados via `STDMETHOD`
(como já é o caso de `IMMNotificationClient`, decisão de `specs/009-issue-20-mmdevice-notification-fix/`),
`paramflags` fica `None` — `STDMETHOD` não carrega anotações de direção `[in]`/`[out]` como
`COMMETHOD` carrega. Com `paramflags is None`, `hack()` retorna sempre o caminho `catch_errors`
(`call_with_this`), que invoca o método Python com os argumentos brutos da vtable **incluindo o
ponteiro `this`** como primeiro argumento — nunca removendo-o, diferente do caminho `call_without_this`
(usado só quando há `paramflags`, isto é, quando a interface é declarada via `COMMETHOD`).

Isso explica exatamente o `TypeError` relatado na issue #22: o método atual
`IMMNotificationClient_OnDeviceStateChanged(self, device_id, new_state)` aceita 3 argumentos
posicionais (`self` + 2), mas é chamado com 4 (`self` implícito do bind + `this` + `device_id` +
`new_state`).

Confirmação direta no próprio pacote `comtypes` (não é uma hipótese isolada): `comtypes/server/__init__.py`
declara `IClassFactory` também via `STDMETHOD` (mesmo padrão desta correção), e o teste oficial do
pacote (`comtypes/test/test_comobject.py::Test_CustomImplementation`) implementa essa interface
exatamente assim — `def CreateInstance(self, this, punkOuter, riid, ppv):`,
`def LockServer(self, this, fLock):` — confirmando que "aceitar `this` sem usá-lo" é o padrão
idiomático de comtypes para interfaces declaradas via `STDMETHOD`, não um workaround ad-hoc.

**Alternatives considered**:
- **Trocar `STDMETHOD` por `COMMETHOD` com `paramflags` explícitos** (`[\"in\"]` por argumento):
  tecnicamente viável — `hack()` usaria `call_without_this` e os métodos já escritos (sem `this`)
  funcionariam sem alteração de assinatura. Rejeitado como escopo desta correção pontual: exigiria
  reescrever toda `_build_notification_client_interface()` (5 métodos, incluindo o tipo auxiliar
  `_PROPERTYKEY` de `OnPropertyValueChanged`) e o `STDMETHOD` já foi a decisão explícita e testada de
  FR-001/`specs/009-.../research.md` — trocar a base de declaração agora ampliaria o diff e o risco sem
  necessidade, quando adicionar um parâmetro `this` a 5 métodos resolve o mesmo problema com uma mudança
  mínima e localizada.
- **Envolver cada callback com um wrapper genérico que descarta o primeiro argumento**: rejeitado —
  esconde a convenção de chamada real do comtypes atrás de indireção desnecessária; aceitar `this`
  explicitamente é mais direto e é o padrão que o próprio comtypes usa em seus testes.

## 2. Defesa em profundidade contra exceção não tratada no callback (FR-002)

**Decision**: cada método `IMMNotificationClient_On*` deve capturar qualquer exceção interna
(incluindo, mas não só, o próprio `TypeError` de aridade caso reapareça por regressão futura), logar um
aviso e retornar sem propagar — mesma filosofia de degrade explícito já usada em
`HotplugListener.__init__`/`subscribe()` (`specs/009-issue-20-mmdevice-notification-fix/`).

**Rationale**: `catch_errors`/`call_with_this` (`_vtbl.py`, visto na pesquisa acima) já converte a
maioria das exceções em `HRESULT` de erro antes de vazar para o runtime COM — mas isso é uma rede de
segurança da biblioteca `comtypes`, não uma garantia da spec sobre o comportamento do nosso domínio.
Adicionar `try/except` explícito no próprio callback torna o requisito FR-002 verificável por teste
unitário direto (sem depender de simular o dispatch COM completo), consistente com P3/P10.

**Alternatives considered**:
- **Confiar apenas na rede de segurança do `comtypes`**: rejeitado — não é testável isoladamente sem
  hardware/COM real, e a spec exige que a defesa contra exceção não tratada seja uma propriedade do
  nosso código, não apenas um efeito colateral de uma biblioteca externa.

## 3. Distinguir `notpresent` transitório de falha de configuração permanente (Bug B, FR-004/FR-005)

**Decision**: `capture_channel` passa a rastrear um flag interno `resolved_at_least_once: bool` (inicia
em `False`). Ao capturar `EndpointResolutionError`: se `resolved_at_least_once` for `True` (o canal já
capturou com sucesso ao menos uma vez antes), a falha é tratada como transitória — log de aviso e
`_retry_after_wait()` (mesmo caminho já usado por `EndpointRemovedError`), preservando o
`endpointId` configurado. Se `resolved_at_least_once` for `False` (nunca resolveu, ainda no primeiro
`_capture_once`), mantém o comportamento fatal/permanente atual (fail-fast de SF-018, FR-005).
`resolved_at_least_once` é setado para `True` via um callback `on_resolved` passado a `_capture_once`,
invocado logo após `resolve_device(...)` suceder — **não** no retorno de `_capture_once` inteira. O
laço de leitura de stream dentro de `_capture_once` só retorna sem exceção quando `stop_event` é
sinalizado (shutdown limpo); em um unplug real, a exceção nasce dentro do próprio loop de leitura e
nunca alcança um retorno normal. Marcar o sucesso apenas no retorno completo (tentativa inicial deste
fix, corrigida após revalidação manual Windows expor o problema — ver
`docs/validation/sf-019-windows.md`) deixava `resolved_at_least_once` sempre `False` em qualquer sessão
real que capturasse por mais de uma leitura antes do unplug, fazendo o Bug B parecer corrigido nos
testes (que simulavam retorno limpo) mas não no runtime real.

**Rationale**: o sintoma da issue #22 ("Endpoint ID '...' exists but is notpresent... failed
permanently... not retrying") ocorre justamente porque a falha de resolução por `notpresent` chega
fora da janela de `woke_on_arrival` (que só cobre a tentativa imediatamente após uma notificação de
chegada) — ou seja, o mecanismo existente de FR-003/spec 006 já cobre "falhou de novo logo após um
arrival", mas não cobre "o stream falhou primeiro, e só na nova tentativa de resolução descobrimos que
o dispositivo está notpresent, sem ter recebido nenhum arrival ainda". Rastrear "já resolveu alguma
vez" é uma condição mais simples e robusta que inspecionar a string de estado (`"notpresent"`)
diretamente no texto da exceção — não depende de correspondência de mensagem de erro e continua
correto mesmo se `resolve_device`/`find_device_for_endpoint` mudar o texto da exceção no futuro.

**Alternatives considered**:
- **Inspecionar se a mensagem/causa de `EndpointResolutionError` menciona `notpresent`**: rejeitado —
  acopla o comportamento a um texto de erro específico (frágil), quando o sinal real que importa é
  "isso já funcionou antes, então não é um erro de configuração".
- **Tratar toda `EndpointResolutionError` como não-fatal (sempre retry)**: rejeitado — quebraria o
  fail-fast de SF-018 (P7 — sem fallback silencioso) para um `endpointId` que nunca existiu desde o
  startup; FR-005 exige preservar esse comportamento sem regressão.
- **Marcar `resolved_at_least_once = True` no retorno normal de `_capture_once`** (tentativa inicial):
  rejeitado após revalidação manual Windows mostrar que o Bug B persistia em runtime real, apesar da
  suíte automatizada (que simula retorno limpo) passar — `_capture_once` só retorna sem exceção no
  shutdown por `stop_event`, nunca "depois de capturar bem-sucedidamente por um tempo". Substituído pelo
  callback `on_resolved`, invocado no ponto certo (logo após `resolve_device` suceder).
- **Usar um contador de tentativas em vez de um booleano**: rejeitado — desnecessariamente complexo
  para o que a spec pede; o requisito é binário (já resolveu uma vez ou não), não um limite de
  tentativas.

## 4. Auditoria de aridade dos demais callbacks (`OnDefaultDeviceChanged`, `OnPropertyValueChanged`)

**Decision**: aplicar o mesmo parâmetro `this` explícito também a `OnDefaultDeviceChanged` e
`OnPropertyValueChanged`, mesmo hoje usando `*_args` (que, por aceitar aridade variável, não quebra
com o argumento extra, mas mascara a mesma causa raiz).

**Rationale**: consistência entre os 5 métodos da interface (FR-001) e clareza — `*_args` esconde
silenciosamente que `this` está sendo passado; nomeá-lo explicitamente documenta a convenção real de
chamada para quem ler o código depois, coerente com o Edge Case já registrado na spec.

**Alternatives considered**:
- **Deixar `*_args` como está, já que não quebra**: rejeitado — a spec já identifica isso como um Edge
  Case a auditar; deixar inconsistente entre métodos da mesma interface aumenta a chance de um erro
  similar ao Bug A ser reintroduzido no futuro se alguém tentar dar nomes explícitos aos parâmetros
  desses dois métodos sem saber da convenção `this`.
