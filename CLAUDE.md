# Assistant Hub AI — contexto para Claude Code

Leia primeiro:

1. `AGENTS.md`
2. `docs/vision.md`
3. `docs/adr/0003-windows-host-audio-agent.md`
4. `docs/adr/0005-wsl-first-development.md`
5. `docs/adr/0007-isolated-windows-audio-workers.md`
6. `docs/adr/0008-transcript-echo-suppression.md`
7. `specs/001-streaming-foundation/`

Ambiente:

- Git, Claude Code, Java, Maven, Gradle, Docker e testes de serviço rodam no WSL;
- Java, Maven e Gradle são gerenciados por SDKMAN; não adicione instalação via `apt`;
- o agente em `agents/windows-audio-agent` é executado com Python nativo do Windows;
- não tente capturar WASAPI dentro do WSL ou de container Linux;
- não compartilhe virtualenv entre Windows e Linux;
- preserve `channelId`, `sourceType` e metadados do dispositivo ponta a ponta.

Regras de áudio:

- preserve um subprocesso isolado por endpoint WASAPI;
- não compartilhe uma instância PyAudio entre canais;
- `run` permanece em foreground e usa `INFO` por padrão;
- noise gate é configurável por perfil;
- supressão de eco é feita no feed de transcrição e não deve ser descrita como AEC acústico completo;
- mudanças no algoritmo de eco exigem testes para fala duplicada e fala local legítima.

Antes de codificar, declare arquivos afetados e critérios de aceite. Depois, execute os testes relevantes e apresente o diff resumido.

Features futuras aprovadas:

- `specs/002-desktop-distribution/`: executável e instalador Windows mantendo o modo WSL Developer;
- `specs/003-ai-provider-hub/`: configuração de Ollama, NVIDIA NIM, chaves próprias e demais provedores.

Ao trabalhar nessas features, leia também ADR-0009, ADR-0010, o schema `contracts/ai-provider-profile.v1.schema.json` e `docs/security/provider-secrets.md`.
