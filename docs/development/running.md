# Como rodar o Assistant Hub AI

Guia operacional para subir o stack **depois de reiniciar o Windows** e no dia a dia.
Complementa o [fluxo mínimo de release](../release/min-flow.md) e o ambiente [WSL-first](wsl-first.md).

**Workspace típico (WSL):** `/home/david/workspace/assistant-hub-ai`

---

## Visão dos componentes

| # | Componente | Onde | Porta / sinal | Script principal |
|---|------------|------|---------------|------------------|
| 1 | Transcrição (Whisper) | WSL + Docker | `http://localhost:8001` | `scripts/wsl/start-assistant-hub.sh` |
| 2 | session-core (sessões + AI providers) | WSL + Docker | `http://localhost:8080` | incluso no hub (Compose); debug JVM: `start-session-core.sh` |
| 3 | Agent WASAPI | Windows nativo | WebSocket → `:8001` | `scripts/windows/run-audio-agent-foreground.ps1` |
| 4 | Desktop shell (opcional) | Windows nativo | UI Tauri | `cargo tauri dev --features gui` em `apps/desktop-shell` |

Ordem recomendada após reboot: **Docker Desktop → `start-assistant-hub.sh` (STT + session-core + agent) → shell (opcional)**.

O dashboard de STT no browser (`:8001`) **não** substitui o session-core. Salvar provedores de IA no shell **exige** o session-core em `:8080` (ou URL configurada). O hub sobe o **container** `assistant-hub-session-core` por padrão (`--no-session-core` para pular).

---

## Pré-requisitos após reboot

1. **Docker Desktop** aberto e com engine WSL 2 pronta (ícone estável na bandeja).
2. Distro WSL (ex.: `Ubuntu-24.04`) disponível (`wsl -l -v`).
3. No WSL: `sdk`/Java 21, Maven, `docker compose` no PATH (ver bootstrap em [wsl-first.md](wsl-first.md)).
4. No Windows (agent): Python 3.12 nativo + venv do agent (o script de run cria se faltar).
5. No Windows (shell, opcional): Node LTS, Rust MSVC, C++ Build Tools, WebView2 — ver [desktop-shell/packaging.md](../desktop-shell/packaging.md).

Não capture WASAPI de dentro do WSL. Não compartilhe venv Python entre Windows e Linux.

---

## Fluxo completo pós-reboot

### 1. Stack principal (WSL) — STT + session-core + agent

```bash
cd /home/david/workspace/assistant-hub-ai
./scripts/wsl/start-assistant-hub.sh --no-build
```

Isso sobe, nesta ordem:

1. containers **transcription** + **session-core** (Compose; seed de `config/ai-providers.yaml` se ausente);
2. health de STT (`:8001`) e session-core (`:8080`);
3. agent WASAPI em um **PowerShell do Windows** (salvo `--no-agent`);
4. browser no dashboard `http://localhost:8001` (salvo `--no-browser`).

| Situação | Comando / flag |
|----------|----------------|
| Dia a dia (imagens já buildadas) | `--no-build` |
| Rebuild + reinstalar agent | `--reinstall-agent` (sem `--no-build` se precisar recompilar) |
| Só containers, agent manual | `--no-agent` |
| Sem session-core (só STT/agent) | `--no-session-core` |
| Outra porta do session-core | `--session-core-port 8081` |
| Sem copiar sample de provedores | `--no-seed-example` |
| Outro perfil de áudio | `--profile samples/audio-profiles/<arquivo>.yaml` |

**Verificação:**

```bash
curl -sS http://127.0.0.1:8001/health
./scripts/wsl/compose.sh ps
curl -sS http://127.0.0.1:8080/actuator/health
# esperado: status UP
curl -sS http://127.0.0.1:8080/api/ai-providers
# esperado: [] ou lista JSON — NÃO "Erro interno inesperado"
```

### 2. session-core standalone (opcional)

**Docker (alinhado ao hub):**

```bash
./scripts/wsl/compose.sh up -d session-core
./scripts/wsl/compose.sh logs -f session-core
./scripts/wsl/stop-session-core.sh
```

Dentro do container o feed de STT é `ws://transcription:8001/ws/transcripts` (DNS Compose). Volumes: `data/session-core` → SQLite; `config/` → `ai-providers.yaml`. Provedores no host (ex. Ollama): `baseUrl` com `http://host.docker.internal:11434/v1` — não use `127.0.0.1` a partir do container.

**JVM (debug / hot reload Maven)** — use com hub em `--no-session-core` ou STT já no ar:

```bash
cd /home/david/workspace/assistant-hub-ai
./scripts/wsl/start-session-core.sh --seed-example
# background: --background · parar: ./scripts/wsl/stop-session-core.sh
```

- **CWD deve ser a raiz do monorepo** (`data/session-core/`, `config/ai-providers.yaml` são relativos).
- No host, o feed padrão é `ws://localhost:8001/ws/transcripts`.
- Se a porta **8080** estiver ocupada por **outro** app (ex.: `number-generator`), o script **aborta** e mostra `pid` / `main` / trecho do `cmd`.
- Outra porta: `--port 8081` (JVM) ou `SESSION_CORE_PORT=8081` / `--session-core-port 8081` (Compose) e aponte o shell (`sessionCoreBaseUrl`).

### 3. Agent Windows (se não abriu no passo 1)

No PowerShell **nativo** (parâmetros PowerShell: `-Session`, `-Profile` — **não** `--session`):

```powershell
cd \\wsl.localhost\Ubuntu-24.04\home\david\workspace\assistant-hub-ai

.\scripts\windows\run-audio-agent-foreground.ps1 `
  -Session teste `
  -Profile "\\wsl.localhost\Ubuntu-24.04\home\david\workspace\assistant-hub-ai\samples\audio-profiles\conference-cam-endpointid.yaml"
```

Deixe a janela aberta (foreground). `Ctrl+C` encerra.

**Perfis:**

| Perfil | Quando usar |
|--------|-------------|
| `samples/audio-profiles/default.yaml` | Microfone/saída padrão |
| `samples/audio-profiles/conference-cam-endpointid.yaml` | Conference cam FHD — **preferir** (evita `nameRegex` ambíguo) |
| `samples/audio-profiles/conference-cam.yaml` | Mesmo hardware por regex — pode falhar com *matched indexes: 1, 5, 9* |
| `samples/audio-profiles/bluetooth-output-usb-mic.yaml` | Bluetooth + USB |

Listar devices (venv do agent):

```powershell
& "$env:LOCALAPPDATA\AssistantHubAI\audio-agent-venv\Scripts\assistant-hub-audio.exe" list-devices
```

**Verificação nos logs:** canais com `endpoint_id=...` e **sem** `Endpoint resolution failed` / `ambiguous`.

### 4. Desktop shell (opcional)

O shell **não** empacota STT nem o agent. Só a UI (sessão, agent, provedores, **Assistente automático**).

Use clone em **disco Windows** (letra de unidade). Caminho UNC (`\\wsl.localhost\...`) quebra `npm`/`cmd`.

```powershell
cd C:\src\assistant-hub-ai
git pull
cd apps\desktop-shell
npm install   # só se necessário
cargo tauri dev --features gui
```

Instalador: `cargo tauri build --features gui` — artefatos em `src-tauri\target\release\bundle\nsis\` e `msi\`. Detalhes: [packaging.md](../desktop-shell/packaging.md).

**Sessão e Assistente (feature live-answer):**

1. No shell, **liste / crie / selecione** a sessão (não há auto-create silencioso). **Criar** torna a nova sessão **ativa** automaticamente; **clicar** um item da lista define a sessão ativa (id completo em «Sessão ativa»). Defaults de create: `title=Sessão local`, `profileId=interview-technical`.
2. **`GET /api/sessions` (list-sessions) só reflete o session-core** (tipicamente UUID). **Não** inventa entradas a partir do agent.
3. **Id só de caminho STT** no formato `session-YYYYMMDD-HHMMSS` (usado às vezes no agent) **não** faz a sessão aparecer sozinha na lista. Para feed/Assistente da UI, use o UUID da sessão do core (criar/selecionar na lista) e inicie o agent com **esse** id.
4. **Regra do sessionId único (issues #47 / #49):** shell (sessão ativa), agent WASAPI e STT **devem** usar o **mesmo** identificador. Transcript e Assistente só reagem a eventos da sessão ativa da UI.
5. **Preferir iniciar/reiniciar o agent pela UI** (painel Agent, modo Direct): o shell passa o UUID da sessão ativa — **não** gera um `session-YYYYMMDD-…` no lugar. Se houver **mismatch** (sessão do agent ≠ ativa), use **«Reiniciar agent com sessão ativa»** (sem diálogo extra).
6. **Selecionar outra sessão na lista NÃO reconfigura** um agent já em execução — só muda feed/Assistente; o banner de mismatch aparece até você reiniciar (UI) ou parar/iniciar manualmente.
7. Agent iniciado **fora** do shell (PowerShell): o shell **não** encerra o processo externo. Pare manualmente e rode com o UUID da UI, por exemplo:

```powershell
# UUID = «Sessão ativa» no shell (data-testid session-active-id) — NÃO use só session-2026… se a intenção é a sessão da lista
.\scripts\windows\run-audio-agent-foreground.ps1 `
  -Session <uuid-da-sessao-ativa> `
  -Profile samples\audio-profiles\<perfil>.yaml
# ou: assistant-hub-audio run --session <uuid-da-sessao-ativa> --profile <perfil.yaml>
```

8. Painel **Assistente**: automático off por default; origens default só **sistema**; modo **pergunta + contexto recente**. Rota: `live-answer` / `chat`. Disparo só em trechos **finais** reconhecidos como pergunta (partials **não** disparam — empty state «aguardando trecho final»).
9. Preferências do Assistente: `%APPDATA%\…\assistant-prefs.json` (por `sessionId`), sem segredos.

**Verificação:** janela abre; lista de sessões via `GET /api/sessions` (só session-core); clique/criar define «Sessão ativa» com UUID completo; agent e UI com o **mesmo** sessionId (sem banner de mismatch); salvar provedor **sem** HTTP 500; com automático on + final elegível → interação no Assistente (ou erro de provedor legível).

Config local: `%APPDATA%\ai.assistanthub.desktopshell\shell-config.json` (`sessionCoreBaseUrl`, padrão `http://localhost:8080`). Sample de rota `live-answer`: `samples/ai-providers/providers.example.yaml` (seed em `config/ai-providers.yaml` se o hub copiar o sample).

---

## Fluxo mínimo diário (2 passos)

```bash
# WSL — um terminal basta
cd /home/david/workspace/assistant-hub-ai
./scripts/wsl/start-assistant-hub.sh --no-build
```

- Browser STT: http://localhost:8001  
- session-core: http://localhost:8080 (container; `./scripts/wsl/stop-session-core.sh` ou `compose.sh stop session-core`)  
- Shell (opcional): `cargo tauri dev --features gui` em `C:\src\...\apps\desktop-shell`

Alternativa a partir do PowerShell Windows (sobe Compose + agent):

```powershell
& "\\wsl.localhost\Ubuntu-24.04\home\david\workspace\assistant-hub-ai\scripts\windows\start-assistant-hub.ps1"
```

O script Windows **não** sobe session-core — use o hub WSL, ou `start-session-core.sh` no WSL à parte.

---

## Checklist “está no ar”

| Check | Esperado |
|-------|----------|
| Docker / STT | `GET http://localhost:8001/health` ok |
| session-core | `GET http://localhost:8080/actuator/health` → `UP` |
| AI providers API | `GET http://localhost:8080/api/ai-providers` → JSON (não 500 de outro app) |
| Agent | Logs INFO; workers dos canais conectados ao WS |
| Shell (se usado) | Janela + status coerente com agent/session-core |

---

## Encerrar

| Componente | Ação |
|------------|------|
| Agent | `Ctrl+C` no PowerShell do agent (ou scripts `stop-audio-agent.ps1` / `stop-assistant-hub.ps1`) |
| session-core | `Ctrl+C` no terminal, ou `./scripts/wsl/stop-session-core.sh` se foi `--background` |
| STT / Compose + agent orquestrado | `./scripts/wsl/stop-assistant-hub.sh` |
| Shell | Fechar a janela |

---

## Provedores de IA (ops)

1. Com session-core no ar, use o painel do shell **ou** edite `config/ai-providers.yaml` (gitignored).
2. `--seed-example` copia `samples/ai-providers/providers.example.yaml`.
3. Segredos: apenas `secretRef` (`env:VAR` / `os:...`) — [provider-secrets.md](../security/provider-secrets.md).
4. Schema: `contracts/ai-provider-profile.v1.schema.json`.

Regras úteis no formulário:

| Campo | Regra |
|-------|--------|
| `id` | `^[a-z][a-z0-9-]{2,63}$` (ex.: `ollama-local`) |
| `baseUrl` | URI válida (ex.: `http://127.0.0.1:11434/v1`) |
| `capabilities` | enums do schema (`chat`, `streaming`, …) separados por vírgula |
| `authentication.mode=none` | deixe `secretRef` vazio |
| `mode=bearer` / `api-key` | `secretRef` obrigatório, ex. `env:NVIDIA_API_KEY` |

---

## Problemas comuns

| Sintoma | Causa | Ação |
|---------|-------|------|
| Save de provedor → `resposta HTTP inesperada: 500` | Outro Java na `:8080` (não é session-core) | `./scripts/wsl/start-session-core.sh` (mostra o ocupante); pare o outro app ou use `--port` |
| `Device selector ... is ambiguous; matched indexes: 1, 5, 9` | Mesmo mic em MME/DS/WASAPI com `nameRegex` | Perfil com `endpointId` (`conference-cam-endpointid.yaml`) |
| `Perfil de áudio não encontrado: teste` | Flags estilo bash no `.ps1` | Use `-Session` e `-Profile` |
| `npm` / UNC / `C:\Windows\package.json` | Projeto aberto via `\\wsl.localhost\...` | Clone ou `net use`/`subst` em `C:\...` |
| `requires the features: gui` / `OUT_DIR` / `icon.ico` | Toolchain Tauri incompleta ou código antigo | `git pull`; `cargo tauri dev --features gui`; ver [packaging.md](../desktop-shell/packaging.md) |
| Vite `EBUSY` em `src-tauri\target` | Watcher do Vite no Cargo target | `vite.config.ts` deve ignorar `**/src-tauri/**` |
| Compose sem GPU / health falha | Docker Desktop ou NVIDIA | Suba o Docker; `nvidia-smi`; logs: `./scripts/wsl/compose.sh logs -f transcription` |
| session-core grava DB no path errado | CWD fora da raiz do monorepo | Sempre `cd` na raiz antes de `mvn` / scripts |

---

## Referências

- [WSL-first](wsl-first.md)
- [Fluxo mínimo (release)](../release/min-flow.md)
- [Packaging do shell desktop](../desktop-shell/packaging.md)
- [Segredos de provedores](../security/provider-secrets.md)
- README na raiz do repositório
