# Phase 0 Research: Desktop Tauri — shell local do Assistant Hub (R5)

Todas as incógnitas de `Technical Context` foram resolvidas por inspeção direta do código existente (`services/session-core`, `agents/windows-audio-agent`) e da visão já aprovada em `specs/002-desktop-distribution/`, sem exigir `[NEEDS CLARIFICATION]` na spec.

## 1. Shell framework

- **Decision**: Tauri 2, produzindo instalador Windows (MSI/NSIS).
- **Rationale**: Já é a decisão registrada em `specs/002-desktop-distribution/spec.md` ("A direção preferencial é Tauri 2 para produzir um executável leve e instaladores Windows MSI/NSIS") e reafirmada pela própria issue #35. Não há necessidade de reabrir essa escolha nesta fatia.
- **Alternatives considered**: Electron — mais pesado em runtime e binário, rejeitado desde a spec pai; não reconsiderado aqui.

## 2. Frontend stack (dentro do webview)

- **Decision**: TypeScript puro + Vite, sem framework de UI (React/Svelte/Vue).
- **Rationale**: O escopo do MVP é pequeno e bem delimitado (status de sessão/canais, feed de transcript, painel do agent) — três painéis, não um dashboard complexo. Introduzir um framework de UI agora é custo sem benefício comprovado nesta fatia, e vai contra o espírito de "core pequeno" do projeto.
- **Alternatives considered**: React — ecossistema maior e mais familiar, mas peso de dependência e complexidade de build não se justificam para 3 painéis; pode ser adotado em uma fase futura de `specs/002-desktop-distribution/` se a superfície de UI crescer (múltiplas edições, diagnóstico completo, etc.).

## 3. Transporte do feed de transcript

- **Decision**: Polling de `GET /api/sessions/{id}/events` (já existente em `SessionController`) a partir do processo Rust, em intervalo curto (ordem de 1–2s).
- **Rationale**: Inspecionado `services/session-core/src/main/java/ai/assistanthub/core/session/SessionController.java` — a única forma de leitura de eventos hoje é REST (`GET`). O único uso de WebSocket no `session-core` é `TranscriptFeedClient`, um **cliente de saída** que consome `/ws/transcripts` do `transcription-service` (fronteira "transcrição publica, session-core consome" — `specs/007-sf-021-session-core-events/`); não existe hoje um canal de push do `session-core` para clientes downstream como um shell desktop. Construir esse canal está fora do escopo desta issue (FR-010 proíbe duplicar/estender o domínio do `session-core` aqui).
- **Alternatives considered**: Adicionar SSE/WebSocket de broadcast no `session-core` para consumidores como o shell — rejeitado nesta fatia por estar fora do escopo da issue #35 (que é "shell local", não mudança de `session-core`); fica registrado como possível evolução futura de `specs/002-desktop-distribution/` caso o polling se mostre insuficiente em uso real.

## 4. Verificação de conectividade com o session-core

- **Decision**: Polling de `GET /actuator/health`.
- **Rationale**: `services/session-core/src/main/resources/application.yml` já expõe `management.endpoints.web.exposure.include: health,info` (Spring Boot Actuator) — nenhuma mudança no `session-core` é necessária. Um sinal de saúde explícito permite ao shell distinguir "serviço fora do ar" de "sessão não encontrada" (FR-009), o que uma falha genérica de `GET /api/sessions/{id}` não permitiria com a mesma clareza.
- **Alternatives considered**: Inferir conectividade só a partir da falha da própria chamada de sessão — rejeitado por ser ambíguo (poderia ser 404 de sessão inexistente ou serviço indisponível).

## 5. Detecção de status do agent Windows

- **Decision**: Enumeração de processos no lado Rust (crate `sysinfo`), casando pelo executável/linha de comando conhecidos do `assistant-hub-audio`.
- **Rationale**: Inspecionado `agents/windows-audio-agent/src/assistant_hub_audio/main.py` — o agent é uma CLI (`list-devices`, `probe`, `run`, `_worker`) sem nenhum endpoint de health/status/PID hoje. Modificar o agent para expor isso está fora do escopo desta issue ("shell local", não mudança do agent). Enumeração de processo é o único sinal disponível sem tocar `agents/windows-audio-agent`.
- **Alternatives considered**: Adicionar um arquivo de PID ou uma porta local de health check ao agent — rejeitado nesta fatia por exigir mudança em `agents/windows-audio-agent`, fora do escopo da issue #35; registrado como candidato a melhoria futura se a detecção por processo se mostrar frágil em uso real.

## 6. Controle de start/stop do agent Windows

- **Decision**: Controle direto (spawn/kill do processo `assistant-hub-audio run --session <id> --profile <perfil>`) quando o próprio shell iniciou o processo e mantém o handle; caso contrário (processo já rodando, iniciado fora do shell, ou finalização não segura), o shell mostra a instrução textual exata e reproduzível para o operador rodar/parar manualmente.
- **Rationale**: Atende ao critério de aceite da issue #35 ("Start/stop ou orientação clara do agent Windows") e a FR-007/FR-008 da spec, sem exigir mudança no agent. `run` já roda em foreground com log `INFO` por padrão (`AGENTS.md`), o que dá um sinal de prontidão observável no stdout capturado pelo processo filho.
- **Alternatives considered**: Sempre exigir CLI manual (sem controle direto) — rejeitado por não atender à metade "start/stop" do critério de aceite quando tecnicamente viável.

## 7. Onde roda o build/dev do shell

- **Decision**: Toolchain nativa Windows (Rust + Node + WebView2) para dev/build do shell; Git, specs e revisão de código continuam no WSL.
- **Rationale**: Segue o mesmo padrão já aceito para `agents/windows-audio-agent` ("Python nativo do Windows" — `AGENTS.md`/`CLAUDE.md`) e é consistente com P3 ("WSL-first, Windows quando necessário"): o alvo final (executável Windows + WebView2) é Windows-only, então o próprio build precisa da toolchain Windows. Cross-compilar Tauri 2 + WebView2 a partir do WSL/Linux não é um caminho maduro/suportado hoje.
- **Alternatives considered**: Cross-compilação a partir do WSL — rejeitada por fragilidade/imaturidade da toolchain para o alvo Windows+WebView2.

## 8. Empacotamento básico (FR-011)

- **Decision**: Usar o bundler nativo do Tauri 2 (MSI/NSIS) sem assinatura de código nem auto-update nesta fatia.
- **Rationale**: A issue #35 pede "packaging básico documentado", satisfeito por um instalador reproduzível e documentado; assinatura e auto-update assinado já pertencem ao escopo mais amplo de `specs/002-desktop-distribution/` ("Atualização automática assinada" nas Edições previstas), fora do R5 mínimo desta issue.
- **Alternatives considered**: Instalador assinado com canal de atualização — adiado explicitamente para `specs/002-desktop-distribution/`.

## 9. Armazenamento local de preferências do shell

- **Decision**: Um único arquivo JSON no diretório de config de app gerado pelo Tauri (URL base do `session-core`, estado de janela); nenhum segredo.
- **Rationale**: Não há necessidade de um banco embarcado — o volume de dados é mínimo (algumas chaves) e o shell não é dono de dado de domínio (sessão/eventos continuam vivendo só no Memory Hub do `session-core`, `specs/013-issue-29-memory-hub-persistence/`). AI Provider Hub, que exigiria tratamento de `secretRef` (`AGENTS.md`), está fora de escopo (FR-013).
- **Alternatives considered**: SQLite embarcado no shell — rejeitado por ser desproporcional ao volume de dados desta fatia.

## Resumo

Nenhum `[NEEDS CLARIFICATION]` permanece. Todas as decisões acima mantêm o shell como um cliente puro do `session-core`/Memory Hub já existentes e do agent Windows já existente, sem introduzir mudança de domínio em nenhum dos dois — consistente com FR-010 e com `AGENTS.md` ("o executável Windows será um shell, não um novo monólito de domínio").
