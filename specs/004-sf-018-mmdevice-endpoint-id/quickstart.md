# Quickstart de validação — SF-018 MMDevice endpoint identity

Guia para provar a feature ponta a ponta. Detalhes de contrato em [contracts/README.md](contracts/README.md); entidades e regras em [data-model.md](data-model.md); roteiro completo de evidência em `docs/validation/sf-018-windows.md`.

## 1. Testes automatizados (WSL/Linux — sem hardware)

Pré-requisito: Python 3.11+ com `pytest` (SDKMAN não gerencia Python; use o ambiente do repo).

```bash
cd /home/david/workspace/assistant-hub-ai
python -m compileall agents/windows-audio-agent/src
PYTHONPATH=agents/windows-audio-agent/src pytest -q agents/windows-audio-agent/tests
```

**Esperado**: suíte verde, incluindo `test_endpoints.py` (correlação + 4 erros de resolução), `test_profiles.py` (round-trip `endpointId`+`index`, prioridade, combinações inválidas) e `test_capture.py` (query `endpointId` no WebSocket). Nenhum teste toca hardware ou importa `pycaw` (fora do Windows vale o `NullEndpointProvider`).

## 2. Validação manual no Windows (Python nativo — nunca no WSL)

Pré-requisito: `python -m pip install -e agents/windows-audio-agent` no Python do Windows.

### 2.1 Descobrir o endpointId

```powershell
assistant-hub-audio list-devices --json
```

**Esperado**: cada dispositivo WASAPI traz `endpointId` correlacionado; dispositivos `[Loopback]` apontam para o endpoint render original.

### 2.2 Perfil com endpointId + probe

```yaml
channels:
  - id: mic
    sourceType: microphone
    device:
      endpointId: "{0.0.1.00000000}.{...}"   # copiado do list-devices
```

```powershell
assistant-hub-audio probe --profile perfil.yaml
```

**Esperado**: canal resolve para o índice PortAudio **atual** do endpoint.

### 2.3 Captura e propagação no evento

```powershell
assistant-hub-audio run --session sf018-validacao --profile perfil.yaml
```

**Esperado**: stream abre no dispositivo do endpoint; conexão WebSocket inclui `endpointId` na query; eventos `transcript-event.v2` do canal trazem `device.endpointId`.

### 2.4 Estabilidade (cenários da spec — SC-001)

Repetir 2.2/2.3 após: reboot; hot-plug USB; conectar/desconectar Bluetooth. **Esperado**: mesmo dispositivo físico capturado, ainda que o índice numérico mude.

### 2.5 Falhas explícitas (SC-002)

| Cenário | Como provocar | Mensagem esperada |
|---------|---------------|-------------------|
| Inexistente | `endpointId` inventado no YAML | "endpoint não encontrado" + sugestão `list-devices --json` |
| Inativo | desabilitar o dispositivo no Windows | erro distinto indicando endpoint inativo |
| Fluxo incompatível | endpoint render em canal `microphone` (sem loopback) | erro distinto de fluxo |
| Sem correlação | endpoint ativo não enumerável via WASAPI | erro distinto de correlação |

**Esperado**: quatro mensagens distintas; **nenhum** fallback para `index`/`nameRegex`/`default`.

### 2.6 Compatibilidade legada (SC-003)

Rodar `probe`/`run` com um perfil antigo (só `index`/`nameRegex`/`default`) sem alteração. **Esperado**: comportamento idêntico ao anterior; perfil com `endpointId`+`index` funciona em agente novo (prioriza endpoint) e antigo (ignora a chave).

## 3. Registro da evidência

Preencher `docs/validation/sf-018-windows.md` com data, commit, build do Windows, dispositivos e resultado de cada caso (PASS/FAIL) — exigência da constituição P10 e critério SC-006.
