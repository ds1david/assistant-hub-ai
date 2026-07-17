# Assistant Hub AI

Plataforma modular para capturar, transcrever, contextualizar e consultar conversas em tempo real.

**Repositório oficial:** `https://github.com/ds1david/assistant-hub-ai.git`

## Ambiente oficial

- Workspace: Ubuntu 24.04 no WSL 2.
- IDE: VS Code conectado ao WSL.
- Desenvolvimento assistido: Claude Code executado dentro do WSL.
- Java, Maven e Gradle: SDKMAN no WSL.
- Docker: Docker Desktop integrado ao WSL, com GPU NVIDIA.
- Captura de áudio: processo Python nativo do Windows usando WASAPI.

Workspace esperado:

```text
/home/david/workspace/assistant-hub-ai
```

## Versão 0.1.6

Esta versão mantém o WSL como ponto único de inicialização e adiciona o planejamento formal de duas capacidades futuras:

- **Desktop Distribution:** executável Windows, instalador, sidecars e atualização assinada.
- **AI Provider Hub:** configuração de provedores, modelos, chaves próprias, NVIDIA NIM, Ollama e endpoints compatíveis.

O runtime atual continua igual:

- `scripts/wsl/start-assistant-hub.sh` sobe containers, aquece o Whisper e abre o agente Windows.
- `scripts/wsl/compose.sh` sempre usa `--env-file <raiz>/.env` e `--project-directory <raiz>`.
- `.env` é criado automaticamente a partir de `.env.example` com permissão `600`.
- A configuração é validada por `docker compose config --quiet` antes do build.
- Defaults GPU: `small`, `cuda`, `float16`.
- O agente inicia com log `INFO`.

## Clonar o repositório

No Ubuntu/WSL:

```bash
mkdir -p /home/david/workspace
cd /home/david/workspace
git clone https://github.com/ds1david/assistant-hub-ai.git
cd assistant-hub-ai
```

Caso você tenha extraído o ZIP antes de publicar no GitHub:

```bash
git init
git branch -M main
git remote add origin https://github.com/ds1david/assistant-hub-ai.git
git add .
git commit -m "chore: bootstrap Assistant Hub AI 0.1.6"
git push -u origin main
```

## Preparar Ubuntu/WSL com SDKMAN

```bash
cd /home/david/workspace/assistant-hub-ai
chmod +x scripts/bootstrap-wsl-ubuntu.sh scripts/wsl/*.sh
./scripts/bootstrap-wsl-ubuntu.sh
```

Valide:

```bash
sdk current
java -version
mvn -version
gradle -version
python3 --version
docker compose version
nvidia-smi
```

## Configuração do `.env`

Na primeira inicialização, `scripts/wsl/compose.sh` cria automaticamente `.env` a partir de `.env.example`.

Defaults principais:

```dotenv
WHISPER_MODEL=small
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
WHISPER_LANGUAGE=pt
LOG_LEVEL=INFO
```

O Compose não depende mais da descoberta implícita do `.env`. Todos os comandos passam explicitamente:

```text
--project-directory /home/david/workspace/assistant-hub-ai
--env-file /home/david/workspace/assistant-hub-ai/.env
```

Confira os valores efetivos antes de iniciar:

```bash
./scripts/wsl/compose.sh config | grep -A30 environment:
```

Altere `.env` e recrie os containers:

```bash
./scripts/wsl/start-assistant-hub.sh
```

## Inicialização principal — a partir do WSL

Execute dentro do Ubuntu:

```bash
cd /home/david/workspace/assistant-hub-ai
./scripts/wsl/start-assistant-hub.sh --reinstall-agent
```

Esse comando:

1. cria e valida `.env`;
2. encerra containers antigos;
3. recompila as imagens GPU;
4. executa o Compose em background;
5. aguarda o health check;
6. carrega o modelo Whisper;
7. abre um novo PowerShell do Windows;
8. inicia o agente WASAPI em foreground nesse PowerShell;
9. abre o dashboard.

Rebuild sem cache:

```bash
./scripts/wsl/start-assistant-hub.sh --reinstall-agent --no-cache
```

Sem rebuild:

```bash
./scripts/wsl/start-assistant-hub.sh --no-build
```

Outro perfil de áudio:

```bash
./scripts/wsl/start-assistant-hub.sh \
  --profile samples/audio-profiles/bluetooth-output-usb-mic.yaml
```

Somente containers, sem abrir agente Windows:

```bash
./scripts/wsl/start-assistant-hub.sh --no-agent
```

Encerrar tudo pelo WSL:

```bash
./scripts/wsl/stop-assistant-hub.sh
```

## Comandos Compose

Use o wrapper para garantir o carregamento correto do `.env`:

```bash
./scripts/wsl/compose.sh ps
./scripts/wsl/compose.sh logs -f transcription
./scripts/wsl/compose.sh config
./scripts/wsl/compose.sh down
```

Evite chamar diretamente `docker compose -f infra/compose/...`, pois nesse formato o Compose pode procurar o `.env` no diretório dos arquivos Compose em vez da raiz do repositório.

## Dashboard e health check

```text
http://localhost:8001
http://localhost:8001/health
```

## Qualidade de transcrição

O vocabulário customizado fica em:

```text
config/whisper-hotwords.txt
```

O modelo `small` privilegia latência. Para maior precisão, teste no `.env`:

```dotenv
WHISPER_MODEL=medium
```

Depois execute novamente o start; trocar o modelo não exige rebuild da imagem, mas exige recriar o container e carregar o novo modelo.

## Perfis de áudio

```text
samples/audio-profiles/default.yaml
samples/audio-profiles/conference-cam.yaml
samples/audio-profiles/bluetooth-output-usb-mic.yaml
```

Validação no PowerShell Windows:

```powershell
assistant-hub-audio probe --profile "\\wsl.localhost\Ubuntu-24.04\home\david\workspace\assistant-hub-ai\samples\audio-profiles\default.yaml"
```

## Features futuras aprovadas

### Executável e instalador

A release R5 prevê uma aplicação desktop Windows baseada em Tauri 2, com instalador NSIS, MSI opcional e o agente WASAPI empacotado como sidecar. O modo atual WSL/Docker continuará sendo a edição Developer.

Documentos:

- `specs/002-desktop-distribution/`
- `docs/adr/0009-desktop-executable-and-installer.md`
- `docs/architecture/desktop-distribution.md`

### AI Provider Hub

A release R6 prevê uma tela para cadastrar provedores, alterar endpoint, modelo, parâmetros, rotas e fallbacks. Chaves próprias serão referenciadas por `secretRef` e armazenadas fora da configuração.

Provedores planejados:

- Ollama local;
- NVIDIA NIM hospedado ou auto-hospedado;
- endpoint genérico OpenAI-compatible;
- OpenAI, Claude, Gemini e Grok;
- novos adaptadores por plugin.

A disponibilidade de endpoints gratuitos e suas cotas pode mudar conforme o provedor.

Exemplo e contrato:

- `samples/ai-providers/providers.example.yaml`
- `contracts/ai-provider-profile.v1.schema.json`
- `specs/003-ai-provider-hub/`
- `docs/security/provider-secrets.md`

## Desenvolvimento

```bash
code .
claude
mvn test
python3 -m compileall agents services
```

Consulte também `CLAUDE.md`, `AGENTS.md` e `docs/development/wsl-first.md`.

## Correção 0.1.6: caminhos do Docker Compose

O wrapper `scripts/wsl/compose.sh` define a raiz do repositório como
`--project-directory`. Por isso, os contextos do Compose também são relativos à
raiz:

```yaml
build:
  context: services/transcription-service
volumes:
  - ./config:/config:ro
```

Inicialize ou sincronize o `.env` explicitamente com:

```bash
./scripts/wsl/init-env.sh
```

Valide os caminhos antes do build:

```bash
./scripts/tests/test-compose-paths.sh
./scripts/wsl/compose.sh config
```

`WHISPER_LANGUAGE=pt-BR` é aceito como configuração amigável e normalizado
internamente para o código Whisper `pt`. O endpoint `/health` mostra o valor
efetivo.
