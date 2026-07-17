# Roadmap

## R0 — Foundation Pack

- visão, ADRs, contratos e monorepo;
- SDK Java inicial;
- perfis de exemplo;
- documentação para Codex e Claude Code.

## R1 — Streaming Foundation

- desenvolvimento WSL-first com VS Code e Claude Code;
- agente de captura nativo no Windows;
- perfis multicanal para microfones, conference cams e Bluetooth;
- gravação WAV por canal;
- streaming PCM por WebSocket com `channelId` e metadados do dispositivo;
- transcrição incremental;
- dashboard dinâmico e métricas de latência;
- identidade persistente por endpoint MMDevice e hot-plug como endurecimento do R1;
- API de sessões mínima.

## R2 — Conversation Intelligence

- captura opcional por processo/aplicativo no Windows;
- detector de turno e fim de pergunta;
- consolidação de segmentos e remoção de duplicatas;
- classificação do tipo de fala;
- primeiro plugin de provedor LLM;
- perfis de entrevista e refinamento;
- sugestões em tópicos, não leitura automática integral.

## R3 — Memory Hub

- persistência de sessões;
- indexação semântica;
- busca temporal e por participante;
- decisões, ações e compromissos;
- respostas com referências à sessão original.

## R4 — Visual Context

- captura de tela plugável;
- OCR e descrição de interface;
- associação de frames com trechos da conversa;
- políticas de mascaramento de informações sensíveis.

## R5 — Desktop Distribution

- shell Tauri 2;
- executável Windows e ícone de bandeja;
- agente WASAPI empacotado como sidecar;
- instalador NSIS e MSI opcional;
- diagnóstico de dependências e GPU;
- atualização assinada;
- edição Lite sem WSL obrigatório;
- modo Developer WSL/Docker preservado.

## R6 — AI Provider Hub

- registro de provedores e modelos;
- configuração completa pela interface;
- chaves próprias em armazenamento seguro;
- Ollama e endpoints OpenAI-compatible;
- presets para NVIDIA NIM hosted e self-hosted;
- OpenAI, Claude, Gemini, Grok e adaptadores futuros;
- roteamento por tarefa, perfil e persona;
- fallback, circuit breaker, métricas e limites;
- políticas locais/remotas de privacidade.

## R7 — Ecosystem

- SDK estável;
- catálogo de plugins;
- integrações com calendários, arquivos e sistemas de trabalho;
- execução distribuída e observabilidade avançada;
- publicação opcional na Microsoft Store.
