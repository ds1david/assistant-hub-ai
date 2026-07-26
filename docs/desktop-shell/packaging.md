# Packaging do Assistant Hub AI — Shell Desktop (R5, issue #35)

Guia de build/instalação reproduzível do shell (`apps/desktop-shell/`) na máquina Windows de
referência. Cobre FR-011/SC-004 de `specs/014-issue-35-desktop-tauri-shell-local/spec.md`.

Para subir o **stack completo** (STT, session-core, agent) junto com o shell, veja
[docs/development/running.md](../development/running.md).

**Importante**: o núcleo Tauri (`apps/desktop-shell/src-tauri/`, binário `desktop-shell`, feature
Cargo `gui`) depende de WebView2 e só é buildado/executado de verdade na máquina Windows de
referência — não compila em WSL/Linux sem uma stack GTK/WebKit completa (ver
`specs/014-issue-35-desktop-tauri-shell-local/research.md`, Decisão 7). A lógica de negócio
(`config`, `session_core_client`, `agent_control`) é uma lib Rust separada, sem dependência do
`tauri`, e por isso é testável com `cargo test` em qualquer ambiente com Rust — inclusive WSL,
onde a suíte já roda como parte do desenvolvimento deste shell.

## Pré-requisitos na máquina Windows de referência

- Windows 10/11 x64 com WebView2 Runtime instalado (já vem por padrão em Windows atualizados;
  senão, baixar o "Evergreen Bootstrapper" da Microsoft).
- [Rust](https://rustup.rs) (toolchain `stable-x86_64-pc-windows-msvc`) — inclui `cargo`.
- [Node.js](https://nodejs.org) LTS (inclui `npm`).
- Microsoft C++ Build Tools (Visual Studio Build Tools, workload "Desktop development with C++")
  — exigido pelo linker do Rust no Windows.
- [Tauri CLI](https://tauri.app): `cargo install tauri-cli --version "^2"` (ou `npm i -D
  @tauri-apps/cli` dentro de `apps/desktop-shell/`).

## Passos de build (do zero)

```powershell
# 1. Obter o código (Git já configurado, mesmo repositório usado no WSL)
git clone <url-do-repositorio>
cd assistant-hub-ai/apps/desktop-shell

# 2. Instalar dependências do frontend
npm install

# 3. Rodar a suíte de testes da lib Rust (não exige GUI, roda igual ao WSL)
cd src-tauri
cargo test
cd ..

# 4. Ícones: placeholders versionados em src-tauri/icons/ (inclui icon.ico exigido
#    pelo tauri-build no Windows). Para branding real, gere a partir de uma fonte:
# cargo tauri icon caminho/para/icone-fonte.png

# 5. Build de desenvolvimento (abre a janela do shell apontando para o Vite dev server).
#    A feature Cargo `gui` é obrigatória: o binário Tauri usa `required-features = ["gui"]`
#    para permitir `cargo test` da lib no WSL sem WebView2/GTK.
#    Use um caminho com letra de unidade (C:\...), não UNC (\\wsl.localhost\...).
cargo tauri dev --features gui

# 6. Build de produção — gera o instalador Windows (MSI e NSIS, conforme
#    src-tauri/tauri.conf.json § bundle.targets)
cargo tauri build --features gui
```

**Esperado no passo 6**: os instaladores aparecem em
`src-tauri/target/release/bundle/msi/*.msi` e `src-tauri/target/release/bundle/nsis/*.exe`.

## Release hardening (issue #66)

| Peça | Onde |
|------|------|
| Runbook local (build + `SHA256SUMS`) | `scripts/windows/release-desktop-shell.ps1` |
| Stub do sidecar só para CI/packaging | `scripts/windows/ensure-sidecar-stub.ps1` (produção: `build-audio-agent-sidecar.ps1`) |
| Checksums multiplataforma | `scripts/release/checksum-artifacts.sh` |
| CI Windows packaging | `.github/workflows/desktop-release.yml` (`workflow_dispatch` / tags `v*`) |
| Code signing (prep, sem cert no git) | [code-signing.md](./code-signing.md) |
| Checklist install/upgrade/uninstall | [docs/validation/r5-desktop-install-checklist.md](../validation/r5-desktop-install-checklist.md) |

```powershell
# Release local com agent real
.\scripts\windows\build-audio-agent-sidecar.ps1
.\scripts\windows\release-desktop-shell.ps1 -UseRealSidecar
# Artefatos + SHA256SUMS em dist\desktop-release\
```

## Configuração pós-instalação

Na primeira execução, o shell cria `shell-config.json` no diretório de config do app
(`%APPDATA%/ai.assistanthub.desktopshell/`, resolvido via `tauri::path::app_config_dir`), com
`sessionCoreBaseUrl` apontando por padrão para `http://localhost:8080`. Ajuste esse valor se o
`session-core` rodar em outra máquina/porta.

## Sidecar do agent WASAPI (R5 / specs/025)

O shell declara `bundle.externalBin: ["binaries/assistant-hub-audio"]` em
`apps/desktop-shell/src-tauri/tauri.conf.json`. No build Windows, o Tauri 2 espera o
artefato:

```text
apps/desktop-shell/src-tauri/binaries/assistant-hub-audio-x86_64-pc-windows-msvc.exe
```

### Gerar o artefato (host Windows)

```powershell
# Na raiz do monorepo (PowerShell nativo, não WSL):
.\scripts\windows\build-audio-agent-sidecar.ps1
# Opcional one-file (quando as deps nativas permitirem):
.\scripts\windows\build-audio-agent-sidecar.ps1 -UsePyInstaller
```

O script instala o agent no venv padrão (`%LOCALAPPDATA%\AssistantHubAI\audio-agent-venv`),
copia o launcher (ou o exe do PyInstaller) para `binaries/` e roda `--version`.

### Resolução em runtime (FR-001)

Ordem: **sidecar empacotado** → env `ASSISTANT_HUB_AUDIO_BIN` → `shell-config.json`
`audioAgentBin` → PATH. O painel do agent mostra `binarySource` / versão / path.

### Shutdown coordenado (FR-006)

Ao sair do shell, apenas o agent **iniciado pelo shell** (handle gerenciado) é encerrado.
Processos iniciados fora do shell (modo Guided) **não** são mortos — pare-os manualmente.

### Developer sem sidecar

Se `binaries/` não tiver o exe e o agent estiver no PATH (venv), o shell continua
funcionando com `binarySource=path` (modo 014).

## Escopo desta fatia (R5) vs. `specs/002-desktop-distribution/`

- **Incluído (014 + 025)**: shell Tauri, packaging MSI/NSIS básico, sidecar do
  `assistant-hub-audio` + supervisor de start/stop/shutdown, docs.
- **Fora de escopo** (ver `specs/002-desktop-distribution/`):
  assinatura de instalador, atualização automática assinada, sidecars de STT/JVM/provider-gateway,
  ícone de bandeja, diagnóstico GPU completo, Microsoft Store.

## Solução de problemas

| Sintoma | Causa provável | Ação |
|---|---|---|
| `OUT_DIR env var is not set` / `generate_context!` | `build.rs` ausente ou `tauri-build` não listado em `[build-dependencies]` | Confirmar `src-tauri/build.rs` chama `tauri_build::build()` |
| `requires the features: gui` | `cargo tauri` sem `--features gui` | Passar `--features gui` (ou `"features": ["gui"]` em `tauri.conf.json` § build) |
| `EBUSY` / Vite morre no `beforeDevCommand` | Vite assistindo `src-tauri/target` | `vite.config.ts` deve ignorar `**/src-tauri/**` no `server.watch` |
| UNC path / `C:\Windows\package.json` | Projeto aberto via `\\wsl.localhost\...` | Clonar ou mapear para letra de unidade (`C:\...`) |
| `cargo tauri build` falha em "WebView2 not found" | Runtime do WebView2 ausente | Instalar o Evergreen Bootstrapper da Microsoft |
| Erro de linker (`link.exe` não encontrado) | Build Tools do C++ ausentes | Instalar o workload "Desktop development with C++" do Visual Studio Build Tools |
| Shell abre mas não mostra status de sessão | `session-core` não está acessível na URL configurada | Conferir `shell-config.json` e que `GET <url>/actuator/health` responde `UP` |
| Painel do agent sempre mostra "parado" mesmo com o agent rodando | Nome do processo diferente do esperado (`assistant-hub-audio`/`assistant-hub-audio.exe`) | Confirmar o nome real do executável instalado; ajustar `AGENT_PROCESS_NAMES` em `agent_control.rs` se necessário |
