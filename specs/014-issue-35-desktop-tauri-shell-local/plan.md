# Implementation Plan: Desktop Tauri — shell local do Assistant Hub (R5)

**Branch**: `014-issue-35-desktop-tauri-shell-local` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-issue-35-desktop-tauri-shell-local/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Hoje operar uma sessão do Assistant Hub AI exige CLI: consultar `GET /api/sessions/{id}` e `GET /api/sessions/{id}/events` do `session-core` na mão, e iniciar `assistant-hub-audio run` manualmente no Windows. Esta feature introduz um shell desktop Windows (Tauri 2) que consome — sem alterar — a API REST já existente do `session-core` (`specs/007-sf-021-session-core-events/`, `specs/013-issue-29-memory-hub-persistence/`) para mostrar status de sessão/canais e um feed de transcript ao vivo (por polling, preservando `channelId`/`sourceType`/`label`), e que dá visibilidade e controle (direto ou orientado) sobre o processo `assistant-hub-audio` do agent Windows. É estritamente um shell: nenhuma lógica de domínio de sessão/persistência/STT é duplicada ou movida para o cliente; AI Provider Hub e sync multi-device permanecem fora de escopo.

## Technical Context

**Language/Version**: Rust 1.75+ (núcleo Tauri 2) + TypeScript 5 (webview, via Vite) — pacote novo, fora dos módulos Maven (`services/session-core`) e Python (`agents/windows-audio-agent`, `services/transcription-service`) já existentes.

**Primary Dependencies**: `tauri` 2.x (shell + empacotador Windows MSI/NSIS, decisão já registrada em `specs/002-desktop-distribution/`); `sysinfo` (crate Rust) para detectar o processo do agent Windows quando ele não foi iniciado pelo próprio shell; cliente HTTP do lado Rust (`reqwest` ou o plugin HTTP do Tauri) para consumir a API REST do `session-core` — toda chamada de rede sai do processo Rust via comando Tauri, nunca diretamente do webview (evita expor a URL do `session-core` e problemas de CORS/CSP). Frontend em TypeScript puro + Vite, sem framework de UI (React/Svelte) nesta fatia — ver `research.md` para a justificativa. Nenhuma dependência nova toca SDK de provedor de IA (P2) nem WASAPI/COM diretamente (isso continua exclusivo do agent).

**Storage**: O shell não é dono de nenhum dado de sessão/evento — consome o `session-core`/Memory Hub como estão. Persiste localmente apenas preferências próprias (URL base do `session-core`, estado de janela) em um arquivo JSON no diretório de config do app gerado pelo Tauri; nenhum segredo é armazenado (AI Provider Hub, que exigiria `secretRef`, está fora de escopo — FR-013).

**Testing**: `cargo test` para a camada Rust (detecção/start/stop do agent com um executável fake, parsing/polling da API do `session-core` contra um servidor HTTP fake local); `vitest` para a lógica do frontend (agrupamento/ordenação do feed por canal, renderização de status) usando fixtures de `ConversationSession`/`HubEvent` no mesmo formato hoje devolvido por `SessionController`. Validação manual na máquina Windows de referência documentada em `docs/validation/` (SC-001/SC-004), sem depender de GPU nem hardware de áudio físico nos testes automatizados (P10/SC-006).

**Target Platform**: Windows 10/11 x64 com WebView2 (mesmo alvo do agent Windows, ADR-0003). Dev/build do shell roda com toolchain nativa Windows (Rust + Node/WebView2), seguindo o mesmo padrão já estabelecido para `agents/windows-audio-agent` (Python nativo do Windows); Git, specs e revisão de código continuam no WSL como hoje (P3) — o build só precisa de Windows porque o alvo final (executável + WebView2) é Windows.

**Project Type**: Novo aplicativo desktop em `apps/desktop-shell/` (Tauri 2); nenhum serviço/módulo existente é modificado.

**Performance Goals**: Novo trecho do feed de transcript visível em até ~2s após o evento já estar disponível via `GET /api/sessions/{id}/events` (polling); status de sessão/canais e do agent Windows atualizado em até ~5s — sem SLA numérico novo definido pela issue além do que já é razoável para uma UI de operação.

**Constraints**: Preservar `channelId`/`sourceType`/`label` no feed sem misturar canais (FR-002/FR-004/P5); não duplicar nem reimplementar a API/domínio do `session-core` (FR-010); não introduzir AI Provider Hub (FR-013) nem sync multi-device/cloud (FR-014); fechar a janela do shell não mata `session-core` nem o agent Windows por padrão (edge case da spec); testes automatizados sem GPU/hardware físico (P10/SC-006); modo Developer (WSL/Docker) continua funcionando sem regressão (FR-012/SC-005).

**Scale/Scope**: Uma janela, uma sessão em foco por vez (MVP); três chamadas HTTP consumidas do `session-core` (`GET /api/sessions/{id}`, `GET /api/sessions/{id}/events`, `GET /actuator/health`) e controle/orientação de um único processo local (`assistant-hub-audio`); empacotamento básico via bundler do próprio Tauri, sem assinatura nem auto-update (deferidos a `specs/002-desktop-distribution/`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|---|---|
| P1 — Especificação antes de código | PASS. `spec.md` cobre requisitos, critérios de aceite e fora de escopo, validado pelo checklist de qualidade; gate humano G1 (Spec) segue pendente de confirmação explícita antes do Implement. |
| P2 — Core independente de fornecedores | PASS. Nenhum SDK de STT/LLM/provedor de IA é importado pelo shell; FR-013 exclui explicitamente AI Provider Hub desta feature. |
| P3 — WSL-first, Windows quando necessário | PASS com atenção. O shell é um caso legítimo de "Windows quando necessário" (executável + WebView2 são Windows-only), no mesmo padrão já aceito para o agent de áudio; Git/specs/revisão continuam no WSL; o shell não faz captura WASAPI/COM diretamente. |
| P4 — Contratos versionados | PASS. Nenhum contrato novo ou alterado — o shell consome `contracts/transcript-event.v2.schema.json` (indiretamente, via `HubEvent`) e a API REST já publicada do `session-core` exatamente como estão (FR-010); nenhum `contracts/` novo é gerado nesta fase. |
| P5 — Separação por canal e origem | PASS — é objetivo central de US1/US2 (FR-002/FR-004): o shell exibe e agrupa por `channelId`/`sourceType`/`label`, sem misturar canais antes de renderizar. |
| P6 — Isolamento de endpoint de áudio | N/A. O shell não faz captura; isolamento por processo por endpoint WASAPI continua sendo responsabilidade exclusiva do `windows-audio-agent` (ADR-0007), não tocado por esta feature. |
| P7 — Identidade de dispositivo | N/A. O shell não seleciona nem resolve dispositivo — apenas inicia/orienta o agent já configurado por perfil; a prioridade `endpointId` > `index` > `default` (ADR-0011) permanece decisão interna do agent. |
| P8 — Automação com autorização | PASS. Nenhum merge, force-push ou fechamento de issue automatizado é proposto por este plano. |
| P9 — Privacidade por padrão | PASS com atenção. O shell não deve logar texto de transcript nem tokens; a config local (URL do `session-core`, estado de janela) não contém segredos, e nenhum campo de AI Provider Hub é tocado (FR-013). Logs do shell (Rust/frontend) devem redigir qualquer dado potencialmente sensível, consistente com `AGENTS.md`. |
| P10 — Qualidade determinística | PASS. Testes automatizados usam um executável fake para o agent e um servidor HTTP fake para o `session-core` — nenhuma dependência de GPU, hardware de áudio real ou serviço remoto (SC-006); validação manual na máquina Windows de referência é registrada em `docs/validation/` (P10/SC-001/SC-004). |

Nenhuma violação exige entrada em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/014-issue-35-desktop-tauri-shell-local/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Não gerado nesta fase — sem contrato novo/alterado (ver Structure Decision)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/desktop-shell/
├── src-tauri/                            # núcleo Rust (Tauri 2)
│   ├── Cargo.toml
│   ├── tauri.conf.json                   # empacotamento Windows (MSI/NSIS), sem assinatura/auto-update
│   ├── src/
│   │   ├── main.rs
│   │   ├── session_core_client.rs        # GET /api/sessions/{id}, /events, /actuator/health (polling)
│   │   ├── agent_control.rs              # spawn/kill assistant-hub-audio run; detecção via sysinfo
│   │   │                                  # quando o processo foi iniciado fora do shell
│   │   └── config.rs                     # preferências locais (URL do session-core, janela) — sem segredos
│   └── tests/
│       ├── agent_control_tests.rs        # US3 — start/stop com processo fake; detecção de processo externo
│       └── session_core_client_tests.rs  # US1/US2 — parsing/polling contra servidor HTTP fake local
├── src/                                   # frontend (TypeScript + Vite, sem framework de UI)
│   ├── main.ts
│   ├── session-status.ts                 # US1 — status de sessão/canais
│   ├── transcript-feed.ts                # US2 — feed agrupado/ordenado por channelId
│   ├── agent-panel.ts                    # US3 — status e ação sobre o agent Windows
│   └── api-client.ts                     # chama comandos Tauri (invoke); nunca fetch direto no webview
├── tests/
│   └── transcript-feed.test.ts           # vitest — ordem cronológica e não mistura de canal (SC-002)
├── package.json
└── vite.config.ts

docs/desktop-shell/
└── packaging.md                          # US4 — passos reproduzíveis de build/instalação no Windows
                                            # de referência (FR-011)
```

**Structure Decision**: Novo top-level `apps/desktop-shell/` (Tauri 2), ao lado de `agents/`, `packages/` e `services/` já existentes — nenhum módulo Maven ou pacote Python é modificado. Toda chamada de rede ao `session-core` e todo controle de processo do agent Windows ficam no processo Rust (comandos Tauri), nunca no webview, para não expor a URL do `session-core` ao conteúdo web e evitar problemas de CORS/CSP. O frontend fica deliberadamente sem framework de UI nesta fatia — escopo pequeno (3 painéis: sessão/canais, feed, agent) não justifica o custo de uma dependência de framework agora; pode ser revisitado em uma fase futura de `specs/002-desktop-distribution/` se a complexidade de UI crescer. Nenhum `contracts/` novo é gerado: o shell é puramente um cliente do que já está publicado (`transcript-event.v2` via `HubEvent`, API REST do `session-core`).

## Complexity Tracking

*Não se aplica — nenhuma violação de Constitution Check identificada.*
