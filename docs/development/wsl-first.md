# Desenvolvimento WSL-first

## Divisão de responsabilidades

### Ubuntu 24.04 no WSL 2

- Git e workspace em `/home/david/workspace/assistant-hub-ai`;
- VS Code Server;
- Claude Code;
- SDKMAN;
- Java, Maven e Gradle;
- Docker Compose;
- serviços Python e Java.

### Windows

- VS Code como cliente gráfico;
- Docker Desktop;
- Python 3.12 nativo;
- agente WASAPI;
- conference cam, Bluetooth, microfones e saídas físicas.

Não compartilhe ambientes virtuais Python entre Windows e WSL.

## SDKMAN

Dependências Linux básicas:

```bash
sudo apt update
sudo apt install -y build-essential ca-certificates curl git gh jq make unzip zip \
  python3 python3-venv python3-pip
```

Bootstrap do projeto:

```bash
cd /home/david/workspace/assistant-hub-ai
./scripts/bootstrap-wsl-ubuntu.sh
```

O script preserva instalações existentes e usa `sdk install` somente quando `java`, `mvn` ou `gradle` não forem encontrados.

## Docker e GPU

No Docker Desktop, habilite:

```text
Settings > General > Use the WSL 2 based engine
Settings > Resources > WSL Integration > Ubuntu-24.04
```

Valide no WSL:

```bash
docker version
docker compose version
nvidia-smi
```

Os defaults do projeto são:

```dotenv
WHISPER_MODEL=small
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

## Fluxo diário automatizado

No PowerShell do Windows:

```powershell
& "\\wsl.localhost\Ubuntu-24.04\home\david\workspace\assistant-hub-ai\scripts\windows\start-assistant-hub.ps1" `
  -ReinstallAgent
```

Esse comando recompila e inicia o Compose no WSL e abre um segundo PowerShell com o agente em foreground e log `INFO`.

## Fluxo diário manual

WSL:

```bash
cd /home/david/workspace/assistant-hub-ai
./scripts/wsl/rebuild-and-start.sh
code .
claude
```

Windows:

```powershell
$Repo = "\\wsl.localhost\Ubuntu-24.04\home\david\workspace\assistant-hub-ai"
& "$Repo\scripts\windows\run-audio-agent-foreground.ps1" `
  -Session teste-001 `
  -Profile "$Repo\samples\audio-profiles\default.yaml" `
  -LogLevel INFO
```

## Eco e vazamento de saída

A conference cam pode captar fisicamente os próprios alto-falantes. O projeto usa:

- `noiseGateDb` por canal no Windows;
- deduplicação textual no serviço de transcrição;
- hotwords e prompt inicial para melhorar termos pouco frequentes.

Essa estratégia não é AEC acústico completo. O WAV do microfone ainda pode conter o áudio remoto.

## Inicialização oficial desde a versão 0.1.4

O ponto de entrada é executado dentro do WSL:

```bash
./scripts/wsl/start-assistant-hub.sh --reinstall-agent
```

Para comandos Compose, use sempre:

```bash
./scripts/wsl/compose.sh <comando>
```

Esse wrapper passa explicitamente o `.env` da raiz e evita a resolução incorreta do arquivo em `infra/compose`.
