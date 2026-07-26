# Quickstart: R5 — Audio Agent sidecar

## 1. Testes automatizados (WSL / qualquer host com Rust)

```bash
cd apps/desktop-shell/src-tauri
cargo test sidecar -- --nocapture
cargo test agent_control -- --nocapture

cd ../
npx vitest run tests/agent-panel.test.ts 2>/dev/null || npx vitest run
```

**Esperado**: resolução sidecar/config/path/missing; start com fake bin; shutdown gerenciado mata child; Guided não mata externo.

## 2. Override de binário (Developer)

```bash
export ASSISTANT_HUB_AUDIO_BIN=/caminho/para/assistant-hub-audio
# ou em shell-config.json: "audioAgentBin": "C:\\...\\assistant-hub-audio.exe"
```

Iniciar agent pelo shell com sessão ativa; status deve mostrar `binarySource: "config"`.

## 3. Empacotar sidecar no Windows (referência)

Ver `docs/desktop-shell/packaging.md` § sidecar.

Resumo:

```powershell
# No host Windows, a partir da raiz do monorepo:
.\scripts\windows\build-audio-agent-sidecar.ps1
# Copia/gera para apps\desktop-shell\src-tauri\binaries\

cd apps\desktop-shell
cargo tauri build --features gui
```

## 4. Validação manual Windows (produto)

Registrar em `docs/validation/r5-audio-agent-sidecar.md`:

1. PATH sem `assistant-hub-audio`
2. Shell instalado/buildado com sidecar
3. Start pela UI → captura sobe
4. Status: `binarySource=sidecar`, versão preenchida, `healthy=true`
5. Fechar shell → processo agent some do Task Manager
6. Agent iniciado manualmente (Guided) → fechar shell **não** mata o agent

## 5. Regressão Developer

Com venv + PATH (scripts WSL/Windows atuais), start pelo shell sem sidecar no pacote → `binarySource=path` e fluxo 014/020 intacto.
