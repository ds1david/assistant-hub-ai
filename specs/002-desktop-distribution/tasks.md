# Tarefas — Desktop Distribution

Visão R5 completa. Fatia entregue: `specs/014-issue-35-desktop-tauri-shell-local/` (shell Tauri 2 local + packaging básico MSI/NSIS documentado). Itens abaixo marcam o que a visão ainda exige além da fatia 014.

- [x] ADR final da tecnologia de desktop e instalador. (`docs/adr/0009-desktop-executable-and-installer.md`)
- [x] Criar esqueleto Tauri 2. (`apps/desktop-shell/` — issue #35 / specs/014)
- [x] Definir diretórios de aplicação, cache, sessões e logs. (config Tauri `app_config_dir` / shell-config; ver `docs/desktop-shell/packaging.md`)
- [x] Empacotar agente WASAPI como sidecar. (`specs/025-r5-audio-agent-sidecar/` — externalBin + script Windows + resolução runtime; artefato real validado no host Windows)
- [x] Implementar supervisor de sidecars. (025 — health/versão + shutdown do agent gerenciado; ainda só o audio agent, não STT/JVM)
- [x] Criar tela de diagnóstico. (painel Diagnóstico unificado #67 / specs/032 — P0 core/STT/agent; devices GPU P1)
- [x] Implementar armazenamento seguro de credenciais. (`os:` + keyring no shell / #64 / specs/029)
- [x] Gerar instalador NSIS por usuário. (targets em `tauri.conf.json`; build real exige host Windows — validação residual 014 T033)
- [x] Gerar MSI opcional. (idem)
- [x] Criar workflow de release Windows. (`desktop-release.yml` + runbook; smoke lib permanece no CI) → **[#66](https://github.com/ds1david/assistant-hub-ai/issues/66)** / specs/031
- [x] Adicionar checksums e preparação para assinatura. (`checksum-artifacts.sh`, `SHA256SUMS`, `code-signing.md`) → **[#66](https://github.com/ds1david/assistant-hub-ai/issues/66)**
- [x] Testar instalação, upgrade, rollback e remoção. (checklist em `docs/validation/r5-desktop-install-checklist.md` — evidência manual Windows residual do operador) → **[#66](https://github.com/ds1david/assistant-hub-ai/issues/66)**
- [x] Documentar migração do modo Developer para Desktop. (`docs/desktop-shell/packaging.md`, `docs/development/running.md`, escopo 014 vs 002)

## Notas de higiene (2026-07-26)

Marcações `[x]` acima refletem o recorte já no monorepo (ADR + shell + conf de bundle + docs).
Não inventam PASS de instalador assinado, sidecar WASAPI, tray icon ou update automático —
esses continuam abertos para fatias futuras de R5.

**Epic residual:** [#63](https://github.com/ds1david/assistant-hub-ai/issues/63).
