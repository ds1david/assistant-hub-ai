# Contract: Agent sidecar — shell status & packaging

**Feature**: 025-r5-audio-agent-sidecar  
**Consumers**: `apps/desktop-shell` (Rust + TS)  
**Compatibility**: aditivo sobre `AgentStatus` de 014/020

## 1. `AgentStatus` (Tauri command `get_agent_status` / `start_agent`)

Campos existentes preservados (`running`, `controlMode`, `guidanceCommand`, `lastError`, `agentSessionId`, `agentSessionSource`).

### Campos novos (obrigatórios no JSON)

| Campo JSON | Tipo | Descrição |
|------------|------|-----------|
| `binaryPath` | `string \| null` | Caminho/nome resolvido |
| `binarySource` | `"sidecar" \| "config" \| "path" \| "missing"` | Origem da resolução |
| `agentVersion` | `string \| null` | Parse de `--version` |
| `healthy` | `boolean` | Ver data-model |

### Exemplo

```json
{
  "running": true,
  "controlMode": "direct",
  "guidanceCommand": "assistant-hub-audio run --session <uuid> --profile <path>",
  "lastError": null,
  "agentSessionId": "11111111-1111-1111-1111-111111111111",
  "agentSessionSource": "managed",
  "binaryPath": "C:\\Program Files\\Assistant Hub AI\\assistant-hub-audio.exe",
  "binarySource": "sidecar",
  "agentVersion": "0.2.0",
  "healthy": true
}
```

## 2. Resolução de binário (comportamento)

Ordem fixa (FR-001):

1. Sidecar path (Tauri `externalBin` / path ao lado do executável do shell)
2. `ASSISTANT_HUB_AUDIO_BIN` se setada e arquivo existe
3. `shell-config.json` → `audioAgentBin` se setado e existe
4. `which`/`PATH` lookup de `assistant-hub-audio` (+ `.exe` no Windows)
5. `missing`

## 3. Shutdown

- Evento de saída **normal** do processo shell: `stop` em handle gerenciado.
- Processos só detectados por nome: **não** recebem kill.

## 4. Packaging (Tauri)

`tauri.conf.json`:

```json
{
  "bundle": {
    "externalBin": ["binaries/assistant-hub-audio"]
  }
}
```

No build Windows, o artefato deve existir como  
`binaries/assistant-hub-audio-<target-triple>.exe` conforme documentação Tauri 2.

## 5. CLI do agent (já existente)

```text
assistant-hub-audio --version
→ imprime versão e exit 0
```

Usado apenas para preencher `agentVersion`; não é health de áudio.
