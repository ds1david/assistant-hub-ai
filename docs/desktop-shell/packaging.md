# Packaging do Assistant Hub AI — Shell Desktop (R5, issue #35)

Guia de build/instalação reproduzível do shell (`apps/desktop-shell/`) na máquina Windows de
referência. Cobre FR-011/SC-004 de `specs/014-issue-35-desktop-tauri-shell-local/spec.md`.

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

# 4. (Opcional, só na primeira vez) Gerar ícones a partir de uma imagem-fonte —
#    tauri.conf.json não traz ícones versionados; sem eles o bundle usa um ícone
#    genérico do Tauri.
# cargo tauri icon caminho/para/icone-fonte.png

# 5. Build de desenvolvimento (abre a janela do shell apontando para o Vite dev server)
cargo tauri dev

# 6. Build de produção — gera o instalador Windows (MSI e NSIS, conforme
#    src-tauri/tauri.conf.json § bundle.targets)
cargo tauri build
```

**Esperado no passo 6**: os instaladores aparecem em
`src-tauri/target/release/bundle/msi/*.msi` e `src-tauri/target/release/bundle/nsis/*.exe`.

## Configuração pós-instalação

Na primeira execução, o shell cria `shell-config.json` no diretório de config do app
(`%APPDATA%/ai.assistanthub.desktopshell/`, resolvido via `tauri::path::app_config_dir`), com
`sessionCoreBaseUrl` apontando por padrão para `http://localhost:8080`. Ajuste esse valor se o
`session-core` rodar em outra máquina/porta.

## Escopo desta fatia (R5) vs. `specs/002-desktop-distribution/`

- **Incluído aqui**: instalador MSI/NSIS básico, sem assinatura de código, sem canal de
  atualização automática (FR-011 — "packaging básico documentado").
- **Fora de escopo desta fatia** (ver `specs/002-desktop-distribution/`, "Edições previstas"):
  assinatura de instalador, atualização automática assinada, múltiplas edições
  (Developer/Desktop Lite/Desktop GPU), Microsoft Store.

## Solução de problemas

| Sintoma | Causa provável | Ação |
|---|---|---|
| `cargo tauri build` falha em "WebView2 not found" | Runtime do WebView2 ausente | Instalar o Evergreen Bootstrapper da Microsoft |
| Erro de linker (`link.exe` não encontrado) | Build Tools do C++ ausentes | Instalar o workload "Desktop development with C++" do Visual Studio Build Tools |
| Shell abre mas não mostra status de sessão | `session-core` não está acessível na URL configurada | Conferir `shell-config.json` e que `GET <url>/actuator/health` responde `UP` |
| Painel do agent sempre mostra "parado" mesmo com o agent rodando | Nome do processo diferente do esperado (`assistant-hub-audio`/`assistant-hub-audio.exe`) | Confirmar o nome real do executável instalado; ajustar `AGENT_PROCESS_NAMES` em `agent_control.rs` se necessário |
