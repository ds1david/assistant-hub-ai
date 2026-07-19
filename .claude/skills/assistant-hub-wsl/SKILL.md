---
name: assistant-hub-wsl
description: Regras WSL-first do Assistant Hub AI — onde rodar comandos, testes e o que nunca fazer no Linux.
---

# Assistant Hub — WSL-first

## Quando usar

Qualquer tarefa de desenvolvimento, CI local, Git, Claude Code, Java, Maven, Docker ou testes de serviço.

## Ler primeiro

- `.specify/memory/constitution.md`
- `AGENTS.md`
- `docs/adr/0005-wsl-first-development.md`

## Regras

1. Workspace no filesystem Linux do WSL (`/home/david/workspace/assistant-hub-ai`).
2. Claude Code, Git, SDKMAN, Java, Maven, Docker e pytest de serviço **só no WSL**.
3. Nunca tentar WASAPI, pycaw real ou captura de microfone dentro do WSL/container.
4. Não compartilhar `.venv` entre Windows e Linux.
5. Fronteira de rede padrão: `ws://127.0.0.1:8001`.

## Comandos úteis (WSL)

```bash
./scripts/wsl/spec-cycle.sh doctor
./scripts/release/check-version.sh
mvn test
PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests
PYTHONPATH=agents/windows-audio-agent/src pytest -q agents/windows-audio-agent/tests
python3 -m compileall services/transcription-service/app agents/windows-audio-agent/src
```

## Proibido

- `git push --force` em main
- merge automático
- commit de `.env`, venvs, WAV, `.specify/workflows/runs/`
