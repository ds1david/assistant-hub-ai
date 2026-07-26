# Data Model: R5 — Audio Agent sidecar

## BinarySource (enum)

| Valor | Significado |
|-------|-------------|
| `sidecar` | Resolvido a partir do binário empacotado com o app |
| `config` | Override env `ASSISTANT_HUB_AUDIO_BIN` ou config do shell |
| `path` | Encontrado no PATH do processo |
| `missing` | Nenhum binário utilizável |

## BinaryResolution

| Campo | Tipo | Regras |
|-------|------|--------|
| `path` | string? | Caminho absoluto ou nome resolvível; null se missing |
| `source` | BinarySource | Obrigatório |
| `version` | string? | Resultado de `--version`; null se desconhecida ou missing |

**Invariantes**:
- Se `source == missing` então `path` e `version` são null.
- Nunca inventar `version` a partir de `VERSION` do monorepo no status do agent (pode-se **comparar** e avisar no futuro; não nesta fatia como bloqueio).

## SupervisedAgentState

| Campo | Tipo | Regras |
|-------|------|--------|
| `running` | bool | Processo detectado ou handle vivo |
| `healthy` | bool | `running &&` (se managed: child não exited; se Guided: running) |
| `controlMode` | `direct` \| `guided` | Igual 014/020 |
| `binary` | BinaryResolution | Última resolução usada no start ou refresh |
| `agentSessionId` | string? | 020 |
| `agentSessionSource` | enum 020 | |
| `lastError` | string? | |

### Transições (handle gerenciado)

```text
Stopped --start success--> Healthy
Healthy --process exit--> Unhealthy/Stopped (handle cleared)
Healthy --stop/shutdown--> Stopped
Stopped --start fail--> Stopped + lastError
```

## ShellConfig (extensão aditiva)

| Campo | Tipo | Default | Notas |
|-------|------|---------|-------|
| `sessionCoreBaseUrl` | string | (existente) | |
| `audioAgentBin` | string? | null | Override local; mesma semântica que env |

Env `ASSISTANT_HUB_AUDIO_BIN` tem precedência sobre o campo de config na etapa “config” da resolução (documentar em quickstart).

## Packaging layout (lógico)

```text
apps/desktop-shell/src-tauri/
  binaries/
    assistant-hub-audio          # dev placeholder / CI fake
    assistant-hub-audio-x86_64-pc-windows-msvc.exe  # build Windows (Tauri externalBin)
```

Nomes exatos seguem convenção Tauri 2 `externalBin` (ver contracts).
