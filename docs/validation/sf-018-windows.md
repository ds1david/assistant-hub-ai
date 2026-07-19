# Validação manual SF-018 — MMDevice endpoint ID

## Ambiente

- Data:
- Commit testado:
- Branch:
- Windows (build):
- Python (Windows):
- Versão do agente (`assistant-hub-audio` / pyproject):
- WSL / serviço de transcrição (se usado):

## Dispositivos

| Papel | Friendly name | endpointId | Notas |
|-------|---------------|------------|-------|
| Microfone | | | |
| Render / loopback | | | |
| Bluetooth (se houver) | | | |
| Desabilitado (teste negativo) | | | |

## Perfil usado

- Path:
- Seletores (endpointId / index / regex):

## Casos

### 1. list-devices

```powershell
assistant-hub-audio list-devices --json
```

- [ ] endpointId presente nos dispositivos WASAPI correlacionados
- [ ] devices não-WASAPI sem correlação forçada

### 2. probe com endpointId

```powershell
assistant-hub-audio probe --profile "<path-do-perfil>"
```

- [ ] resolve o dispositivo correto
- [ ] log mostra endpoint_id

### 3. run captura

```powershell
assistant-hub-audio run --session sf018 --profile "<path-do-perfil>"
```

- [ ] stream abre no índice atual correto
- [ ] evento v2 contém endpointId
- [ ] dashboard/feed sem regressão de canal

### 4. Reboot ou reenumeração

- Índice PortAudio antes:
- Índice depois:
- [ ] mesmo endpointId continua capturando o dispositivo correto

### 5. Hot-plug (parcial; SF-019 cobre listener)

- [ ] após replug, novo run com mesmo perfil/endpointId funciona
- [ ] falha compreensível se endpoint sumiu

### 6. Endpoint desabilitado / inexistente

- [ ] mensagem distinta para desabilitado/unplugged
- [ ] mensagem distinta para ID desconhecido com alternativas
- [ ] sem fallback silencioso para outro device

### 7. Bluetooth / nomes duplicados (se aplicável)

- [ ] WARNING de enumeration order quando nomes duplicados
- [ ] comportamento documentado

## Segurança

- [ ] logs sem segredo / token / áudio bruto

## Resultado

- Resultado: PASS | FAIL | BLOCKED
- Evidências/anexos:
- Limitações:
