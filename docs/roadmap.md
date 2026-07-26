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

**P0 (issue #68 / specs/033):** contrato `visual.frame.v1`, ingestão session-core com consentimento + OCR stub + PII mask, painel shell.

**P1 (issue #77):** captura real (DXGI) + OCR de produção (Tesseract/remoto policy); mantém consentimento e PII mask do P0.

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

---

## Residual backlog (pós-#61, 2026-07-26)

Estado real no monorepo vs visão R3–R6. Epic: [#63](https://github.com/ds1david/assistant-hub-ai/issues/63).

| Ordem | Issue | Fatia | Release |
|------:|-------|--------|---------|
| 1 | [#64](https://github.com/ds1david/assistant-hub-ai/issues/64) | Secure credential store (Windows DPAPI / OS keyring) | 002 + 003 |
| 2 | [#65](https://github.com/ds1david/assistant-hub-ai/issues/65) | Memory Hub R3.2 — busca, decisões, referências | R3 | **P0 done (030)** |
| 3 | [#66](https://github.com/ds1david/assistant-hub-ai/issues/66) | Release hardening — checksums, CI packaging, install | 002 / R5 |
| 4 | [#67](https://github.com/ds1david/assistant-hub-ai/issues/67) | Painel de diagnóstico unificado | 002 / R5 |
| 5 | [#68](https://github.com/ds1david/assistant-hub-ai/issues/68) | Visual Context (spec first) | R4 |

### Já entregue (não reabrir como “faltando tudo”)

| Área | Fatias |
|------|--------|
| R3.1 persistência | #29 / `specs/013-issue-29-memory-hub-persistence/` |
| R5 shell + sidecar | #35 / 014, #? / 025 |
| R6 hub core | #37 / 015, 017, 026, 027 |
| Live-answer entrevista | #61 / 028 |

### Próximo a implementar

- **#65 P0** entregue em `specs/030-issue-65-r3-memory-intelligence/` (busca + heurística + painel Memory). P1 embeddings/cite ainda abertos.


Começar por **#64** (desbloqueia 002 e 003 de uma vez), depois #65…#68 na ordem da tabela.
