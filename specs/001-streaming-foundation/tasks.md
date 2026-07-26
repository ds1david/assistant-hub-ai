# Tarefas — Streaming Foundation

- [x] SF-001 Criar monorepo, visão e ADRs.
- [x] SF-002 Criar serviço FastAPI e health check.
- [x] SF-003 Implementar WebSocket de áudio.
- [x] SF-004 Integrar faster-whisper com janela sobreposta.
- [x] SF-005 Criar dashboard de transcrição.
- [x] SF-006 Criar agente Windows com microfone e WASAPI loopback.
- [x] SF-007 Adicionar gravação WAV opcional.
- [x] SF-008 Adicionar endpoint de transcrição de arquivo.
- [x] SF-009 Documentar desenvolvimento WSL-first e adicionar `CLAUDE.md`.
- [x] SF-010 Adicionar perfis multicanal de áudio.
- [x] SF-011 Adicionar `list-devices --json` e `probe`.
- [x] SF-012 Publicar eventos de transcrição v2 com dispositivo e `channelId`.
- [x] SF-013 Tornar o dashboard dinâmico por canal.
- [x] SF-014 Adicionar testes de contrato end-to-end com áudio sintético.
- [x] SF-015 Executar matriz manual com conference cam, Bluetooth e microfone USB. (PASS parcial — Bluetooth/USB BLOCKED por falta de hardware; reboot/hot-plug/endpoint desabilitado pendentes como follow-up; ver docs/validation/ e `specs/005-sf-015-hardware-matrix/`)
- [x] SF-016 Medir p50/p95 por canal via registry em memória e `GET /v1/sessions/{sessionId}/metrics`.
- [x] SF-017 Consolidar texto e reduzir duplicações.
- [x] SF-018 Implementar identidade persistente com MMDevice endpoint ID. (`specs/004-sf-018-mmdevice-endpoint-id/` — código done; validação manual residual em docs/validation/sf-018-windows.md)
- [x] SF-019 Implementar listener de hot-plug nativo. (`specs/006-sf-019-hotplug-listener/` + fixes `009-issue-20`, `010-sf-019-callback-notpresent-fix` — código done; revalidação manual Windows residual T033/T010/T017)
- [x] SF-020 Avaliar plugin de captura por processo/aplicativo. (`specs/009-sf-020-process-capture/` — implementação done; validação manual Windows residual T024)
- [x] SF-021 Publicar eventos v2 no session-core. (`specs/007-sf-021-session-core-events/` — implementação + convergence T021/T022 done)
- [x] SF-022 Ajustar tamanho de janela com base nas métricas p50/p95 coletadas na SF-016. (`specs/008-sf-022-adaptive-window/` — 19/19 done)

## Notas de higiene (2026-07-26)

Itens SF-019–SF-022 estavam abertos nesta umbrella enquanto as fatias filhas já entregavam o código.
Esta atualização alinha o checklist ao estado real do monorepo. Evidência de hardware Windows e
gates de PR/tag continuam rastreados nas specs filhas e em `docs/validation/` / `docs/release/`.
