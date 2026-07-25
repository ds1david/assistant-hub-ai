# Fluxo mínimo (release) — Assistant Hub AI

Guia para um desenvolvedor **subir o stack completo** usando apenas a documentação do repositório.

**Aceite desta release** (issue #39 / SC-004): os **três pilares** devem estar no ar:

1. **WSL** — transcrição (Docker) + `session-core` saudáveis  
2. **Agent Windows** — `assistant-hub-audio` conectado ao STT  
3. **Desktop shell** — janela do app no ar e refletindo sessão/agent  

Configuração de **provedores de IA** é documentada como passo de ops (não substitui os três pilares).

Falta de host Windows, GPU ou WebView2 é **bloqueio de ambiente** — não declare o fluxo mínimo como OK.

Entrada: [README.md](../../README.md) → esta página.

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
# ou suba serviços pontualmente via scripts/wsl/compose.sh
```

`session-core` (Memory Hub / API de sessão):

```bash
# a partir da raiz do monorepo (CWD importa para data/session-core/)
mvn -pl services/session-core -am spring-boot:run
# ou o comando de start documentado no módulo, se preferir jar
```

Porta padrão típica do `session-core`: `http://localhost:8080` (confirme em `services/session-core` / config).

### Critério “no ar”

| Check | Esperado |
|-------|----------|
| Compose / STT | Container de transcrição healthy ou endpoint WS documentado responde |
| `session-core` | `GET http://localhost:8080/actuator/health` (ou URL documentada) → `UP` |
| `.env` | Presente na raiz; **não** commitado |

Falhas comuns: Docker não no PATH do WSL; `.env` ausente; GPU/`nvidia-smi` indisponível; CWD errado gerando `memory-hub.db` em path inesperado (arquivo local é **gitignored**).

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

### Critério “no ar”

| Check | Esperado |
|-------|----------|
| Janela | Shell abre (WebView2) |
| Sessão | Status de sessão/canais ou health do `session-core` refletido na UI |
| Agent | Painel do agent não fica permanentemente inconsistente com o processo real (ver packaging troubleshooting) |

Falhas comuns: WebView2 ausente; `session-core` down; build só no WSL sem GTK/WebKit (use Windows nativo para o binário Tauri).

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
