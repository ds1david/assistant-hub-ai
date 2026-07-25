# Fluxo mínimo (release) — Assistant Hub AI

Guia para um desenvolvedor **subir o stack completo** usando apenas a documentação do repositório.

**Aceite desta release** (issue #39 / SC-004): os **três pilares** devem estar no ar:

1. **WSL** — transcrição (Docker) + `session-core` saudáveis  
2. **Agent Windows** — `assistant-hub-audio` conectado ao STT  
3. **Desktop shell** — janela do app no ar e refletindo sessão/agent  

Configuração de **provedores de IA** é documentada como passo de ops (não substitui os três pilares).

Falta de host Windows, GPU ou WebView2 é **bloqueio de ambiente** — não declare o fluxo mínimo como OK.

Entrada: [README.md](../../README.md) → esta página.

Operação diária / pós-reboot (scripts, health checks, armadilhas): [docs/development/running.md](../development/running.md).

---

## Fronteira WSL vs Windows

| Onde | O quê |
|------|--------|
| **WSL (Linux)** | Git, Docker Compose / STT, Maven/`session-core`, testes de serviço, scripts `scripts/wsl/*` |
| **Windows nativo** | Agent WASAPI (`assistant-hub-audio`), shell desktop Tauri (`apps/desktop-shell`) |

Não capture áudio WASAPI de dentro do WSL. Não compartilhe venv Python entre Windows e Linux.

Detalhes de ambiente: [docs/development/wsl-first.md](../development/wsl-first.md).

---

## Pilar 1 — WSL (compose/STT + session-core)

### Pré-requisitos

- Ubuntu no WSL 2, Docker Desktop integrado, SDKMAN (Java 21, Maven)  
- Clone do repositório (workspace típico: `/home/david/workspace/assistant-hub-ai`)  
- GPU NVIDIA opcional para Whisper; sem GPU o fluxo de STT local pode ficar limitado (documente o bloqueio)

### Passos

```bash
cd /home/david/workspace/assistant-hub-ai
chmod +x scripts/bootstrap-wsl-ubuntu.sh scripts/wsl/*.sh
# bootstrap se ainda não rodou: ./scripts/bootstrap-wsl-ubuntu.sh
./scripts/wsl/init-env.sh          # cria .env a partir de .env.example (mode 600)
./scripts/wsl/start-assistant-hub.sh
# sobe STT + session-core (background, seed se necessário) + agent Windows
# ou suba serviços pontualmente via scripts/wsl/compose.sh
```

`session-core` sobe como container Compose (`assistant-hub-session-core`) junto com o STT. Standalone:

```bash
# Container só do core (STT já no ar)
./scripts/wsl/compose.sh up -d session-core
./scripts/wsl/stop-session-core.sh

# Debug JVM (CWD = raiz do monorepo — importa para data/session-core/)
./scripts/wsl/start-session-core.sh --seed-example
# ou: mvn -pl services/session-core -am spring-boot:run
```

Porta padrão: `http://localhost:8080` (`SESSION_CORE_PORT` / `--session-core-port`). Se a 8080 estiver tomada, use `8081` e ajuste `sessionCoreBaseUrl` no shell desktop.

### Critério “no ar”

| Check | Esperado |
|-------|----------|
| Compose / STT | Container de transcrição healthy ou endpoint WS documentado responde |
| `session-core` | Container `assistant-hub-session-core` + `GET http://localhost:8080/actuator/health` → `UP` |
| `.env` | Presente na raiz; **não** commitado |

Falhas comuns: Docker não no PATH do WSL; `.env` ausente; GPU/`nvidia-smi` indisponível; build Maven da imagem session-core lento na 1ª vez; CWD/volumes gerando `memory-hub.db` em path inesperado (arquivo local é **gitignored**).

Scripts: `scripts/wsl/compose.sh`, `scripts/wsl/start-assistant-hub.sh`, `scripts/wsl/init-env.sh`.

---

## Pilar 2 — Agent Windows conectado

### Pré-requisitos

- Windows 10/11 com Python nativo (não o do WSL)  
- Pacote `agents/windows-audio-agent` instalável (`pip install -e agents/windows-audio-agent` no host Windows)  
- Perfil de áudio em `samples/audio-profiles/`  
- STT alcançável a partir do Windows (tipicamente `ws://127.0.0.1:8001` — ver `.env` / README)

### Passos (PowerShell)

```powershell
# Ajuste o caminho WSL share se necessário
cd \\wsl.localhost\Ubuntu-24.04\home\david\workspace\assistant-hub-ai
python -m pip install -e agents\windows-audio-agent
assistant-hub-audio list-devices
assistant-hub-audio probe --profile samples\audio-profiles\default.yaml
assistant-hub-audio run --session teste --profile samples\audio-profiles\default.yaml
```

### Critério “no ar”

| Check | Esperado |
|-------|----------|
| CLI | `assistant-hub-audio --help` funciona |
| Processo | `assistant-hub-audio` / worker em execução |
| Conexão STT | Logs INFO sem erro permanente de WebSocket; chunks fluindo se houver áudio |

Falhas comuns: Python WSL em vez de Windows; firewall bloqueando localhost; perfil com `endpointId` inválido; STT ainda não no ar no WSL.

---

## Pilar 3 — Desktop shell no ar

### Pré-requisitos

- Windows com WebView2, Rust stable MSVC, Node LTS  
- Guia de packaging: [docs/desktop-shell/packaging.md](../desktop-shell/packaging.md)

### Passos (dev)

```powershell
cd apps\desktop-shell
npm install
# lib Rust (testável sem GUI):
cd src-tauri
cargo test
cd ..
# UI dev (requer toolchain Tauri Windows):
cargo tauri dev
# ou build/instalador conforme packaging.md
```

Configure `sessionCoreBaseUrl` (padrão `http://localhost:8080`) no config do app se necessário.

### sessionId único (UI ↔ agent ↔ STT)

Shell, agent WASAPI e STT devem usar o **mesmo** `sessionId`. Preferir **Iniciar / Reiniciar agent com sessão ativa** no painel do shell. **Selecionar sessão na lista não reconfigura** agent já em execução — se divergir, o shell mostra mismatch (e CTA de reinício em modo Direct). Detalhes e exemplo PowerShell: [docs/development/running.md](../development/running.md) (seção Sessão e Assistente).

### Critério “no ar”

| Check | Esperado |
|-------|----------|
| Janela | Shell abre (WebView2) |
| Sessão | Status de sessão/canais ou health do `session-core` refletido na UI |
| Agent | Painel do agent não fica permanentemente inconsistente com o processo real; **mesmo sessionId** da sessão ativa (sem banner de mismatch) |

Falhas comuns: WebView2 ausente; `session-core` down; build só no WSL sem GTK/WebKit (use Windows nativo para o binário Tauri); agent com outro `--session` que a UI.

---

## Provedores de IA (ops)

Não substitui os três pilares; necessário para exercitar o AI Provider Hub.

1. Copie o sample:

   ```bash
   cp samples/ai-providers/providers.example.yaml config/ai-providers.yaml
   ```

2. **Não commite** `config/ai-providers.yaml` (já no `.gitignore`).  
3. Segredos: [docs/security/provider-secrets.md](../security/provider-secrets.md) — use `secretRef`, nunca chave em claro no git.  
4. Contrato: `contracts/ai-provider-profile.v1.schema.json`.

### Critério

Perfil carrega no `session-core` / UI de provedores sem expor segredos em log.

---

## Checklist rápido de aceite (outro dev)

- [ ] Pilar 1: STT + session-core health  
- [ ] Pilar 2: agent Windows conectado  
- [ ] Pilar 3: desktop shell no ar  
- [ ] Provedores: config local gitignored documentada  
- [ ] Bloqueios de ambiente (se houver) registrados — **sem** declarar sucesso parcial como SC-004 OK  

Validação de release: `specs/016-issue-39-release-hardening/quickstart.md`.
