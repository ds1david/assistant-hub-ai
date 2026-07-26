# Validação manual — R5 Audio Agent sidecar (025)

Template de evidência (P10). Preencher no host Windows de referência.

## Ambiente

| Campo | Valor |
|-------|--------|
| Data | _YYYY-MM-DD_ |
| Commit | |
| Branch | |
| Windows build | |
| Shell build | `cargo tauri build --features gui` / instalador |
| Sidecar gerado com | `build-audio-agent-sidecar.ps1` / `-UsePyInstaller` |
| Agent `--version` | |
| PATH sem agent? | sim / não |

## Casos

### 1. Start com sidecar (PATH limpo)

- [ ] `binarySource` = `sidecar`
- [ ] `agentVersion` preenchida
- [ ] `healthy` = true enquanto captura roda
- [ ] `sessionId` alinhado à UI (020)

### 2. Binário ausente

- [ ] Mensagem acionável (sidecar/PATH/config), não genérica

### 3. Shutdown coordenado

- [ ] Agent iniciado pelo shell some do Task Manager ao fechar o shell
- [ ] Agent iniciado **fora** do shell permanece após fechar o shell

### 4. Developer PATH

- [ ] Sem sidecar no pacote, agent no PATH → `binarySource=path`, start OK

## Resultado

- Resultado: PASS / FAIL / PARCIAL
- Limitações:
- Logs (sem áudio bruto / tokens):
