# Phase 0 Research: Tornar `default_microphone()` WASAPI-aware

Nenhum marcador `NEEDS CLARIFICATION` restou na spec ou no Technical Context do plano — as três decisões abaixo consolidam a pesquisa feita diretamente no código e na documentação já existente do repositório (não há tecnologia nova a avaliar).

## Decisão 1 — Como resolver o default de entrada dentro do host API WASAPI

- **Decision**: usar `audio.get_host_api_info_by_type(pyaudio.paWASAPI)["defaultInputDevice"]` para obter o índice do dispositivo default de entrada dentro do host API WASAPI, e então `audio.get_device_info_by_index(...)` para os metadados completos — o mesmo par de chamadas que `default_loopback()` já usa para `defaultOutputDevice` (`devices.py:76-78`).
- **Rationale**: `default_loopback()` já resolve exatamente este problema (mesma classe de bug) para o lado de saída/loopback, está em produção e é o padrão de referência citado na própria issue e em `docs/validation/sf-015-default-mic.md`. Reaproveitar o padrão minimiza risco de regressão e mantém as duas funções simétricas — mais fácil de revisar e manter.
- **Alternatives considered**:
  - Continuar usando `pyaudio.get_default_input_device_info()` e filtrar/validar depois se o `hostApi` retornado é WASAPI, levantando erro caso não seja — rejeitado porque isso ainda depende do PortAudio escolher "o" default global primeiro (que pode nem existir se o default global for outro host API), em vez de perguntar diretamente ao host API WASAPI qual é o seu próprio default; a etapa extra de validação pós-hoc não elimina o caso em que o WASAPI tem um default de entrada válido mas ele não é o "default global" do PortAudio (exatamente o cenário reproduzido na SF-015: index 9 WASAPI vs index 1 MME).
  - Usar `pycaw` diretamente (a mesma biblioteca MMDevice usada por `endpoints.py`) para obter o default device MMDevice e depois correlacionar com o índice PortAudio — rejeitado por introduzir um caminho de resolução paralelo ao de `default_loopback()`, quebrando a simetria entre microfone e loopback sem ganho adicional (o resultado final passa pela mesma correlação `correlate_devices()` de qualquer forma).

## Decisão 2 — Comportamento quando não há default WASAPI de entrada válido

- **Decision**: levantar `RuntimeError` com mensagem explícita (ex.: `"Default WASAPI input device was not found"`), no mesmo estilo da exceção já lançada por `default_loopback()` quando o loopback correspondente não é encontrado (`devices.py:86`, `raise RuntimeError("Default WASAPI loopback device was not found")`).
- **Rationale**: consistência com o padrão de erro já estabelecido na mesma família de funções; cumpre P7 (nenhum fallback silencioso quando a identidade de dispositivo esperada — aqui, "default dentro do WASAPI" — não resolve) e P10 (falha diagnosticável, sem crash silencioso). O chamador (`resolve_device()`) já propaga exceções de resolução sem tratamento especial, então nenhuma mudança adicional é necessária na cadeia de chamada.
- **Alternatives considered**:
  - Fazer fallback automático para o default global do PortAudio (comportamento atual) — rejeitado, é exatamente o bug que está sendo corrigido.
  - Devolver `None`/dispositivo vazio e deixar o chamador decidir — rejeitado, quebraria o contrato de retorno de `default_microphone()` (hoje sempre `dict[str, Any]`) e obrigaria mudanças em `resolve_device()`/`resolve_profile()` fora do escopo declarado (FR-004, FR-006).

## Decisão 3 — Estratégia de teste automatizado (sem hardware)

- **Decision**: criar `tests/test_devices.py` com um objeto fake de `pyaudio.PyAudio` que implementa `get_host_api_info_by_type`, `get_device_info_by_index` e `get_device_info_generator`, no mesmo espírito do `_FakePyAudioModule`/`_FakeAudio` já usados em `tests/test_capture_channel.py:59-68`. Dois casos principais: (a) host API WASAPI com `defaultInputDevice` válido → devolve o dispositivo esperado com `hostApi` == índice WASAPI simulado; (b) host API WASAPI sem `defaultInputDevice` (ou ausente) → `RuntimeError` da Decisão 2.
- **Rationale**: `pytest` já é o framework do projeto (P10 — determinístico, sem GPU/hardware); reaproveitar o padrão de fake já validado em `test_capture_channel.py` evita inventar uma nova convenção de mock e mantém os testes legíveis para quem já conhece a suíte.
- **Alternatives considered**: usar `unittest.mock.MagicMock` genérico sem uma classe fake dedicada — rejeitado, os testes existentes do projeto preferem classes fake explícitas e tipadas (ver `_FakeAudio`, `FakeEndpointProvider`, `FakeAudio`) por serem mais fáceis de ler e depurar do que asserts de `Mock.call_args`.

## Contexto reaproveitado (não é nova pesquisa)

Já documentado e verificado durante o `/speckit-specify`, apenas listado aqui para rastreabilidade:

- Causa raiz e reprodução real: `docs/validation/sf-015-default-mic.md` (2026-07-20), reproduzida 2x.
- Regra de prioridade de identidade de dispositivo: ADR-0011 (`endpointId > index > default`, sem fallback silencioso).
- Filtro de correlação por host API WASAPI: `endpoints.py:116` (`correlate_devices()`), inalterado por esta correção.
