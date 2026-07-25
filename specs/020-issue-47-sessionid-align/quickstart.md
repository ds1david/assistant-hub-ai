# Quickstart validation: sessionId UI↔agent alignment

**Feature**: `specs/020-issue-47-sessionid-align`  
**Date**: 2026-07-25

Validação determinística no WSL + roteiro manual Windows. Contratos: [session-align-shell.md](./contracts/session-align-shell.md). Modelo: [data-model.md](./data-model.md).

## Prerequisites

- Repo em WSL: `/home/david/workspace/assistant-hub-ai`
- Node + npm para vitest do shell
- Rust toolchain para `cargo test` da lib `desktop_shell` (sem feature `gui`)
- (Manual Windows) stack STT + session-core + shell + agent conforme `docs/development/running.md`

## Automated (WSL) — gate padrão

```bash
cd /home/david/workspace/assistant-hub-ai/apps/desktop-shell
npm test -- --run
# ou: npx vitest run

cd src-tauri
cargo test
```

### Expected coverage (post-implement)

| Area | Checks |
|------|--------|
| Rust `parse_session_from_cmd` | `--session UUID` → Some; missing → None; `--session=` form if supported |
| Rust resolution priority | cmdline wins over managed; managed when no cmdline; unknown when neither |
| Vitest `resolveAlignment` | matched / mismatched / stopped / unknown / no active |
| Vitest agent panel | mismatch banner + restart CTA when Direct+mismatch; no banner when aligned or stopped |
| Vitest agent panel | Guided + running: manual stop hint, no force-kill callback |
| Vitest empty kinds | precedence FR-010 (mismatch > prefs > empty feed > awaiting final > no eligible) |
| Vitest / wiring | start callback receives **active** session id |
| Vitest assistant-auto | Final elegível + system + auto on still creates turn (019 regression) |

## Manual Windows — alinhamento ponta a ponta

1. Subir STT + session-core (`./scripts/wsl/start-assistant-hub.sh --no-build` ou fluxo documentado).
2. Abrir shell desktop (`cargo tauri dev --features gui` em path Windows).
3. **Criar/selecionar** sessão; copiar UUID exibido como sessão ativa.
4. **Iniciar agent pela UI** (Direct) → sessão do agent = UUID ativo; **sem** banner mismatch.
5. **Trocar** sessão na lista (criar outra) **sem** reiniciar agent → banner mismatch + CTA reiniciar.
6. Clicar **Reiniciar agent com sessão ativa** (sem confirm) → banner some; agent no novo UUID.
7. (Opcional Guided) Parar agent; iniciar no PowerShell com **outro** `-Session` / `--session` → shell mostra mismatch se cmdline legível; **não** mata o processo; orientação manual + comando com UUID da UI.
8. Com ids alinhados, automático on, origem system: falar / injetar áudio; se só partials no feed → empty **aguardando trecho final**; se Final pergunta elegível → interação no Assistente (ou erro de provedor legível).

### Pass criteria (manual)

- [ ] Start UI usa sessão ativa  
- [ ] Mismatch visível quando ids divergem (cmdline ou managed)  
- [ ] Select não reinicia sozinho  
- [ ] CTA restart realinha em Direct  
- [ ] Guided sem force-kill  
- [ ] Empty states diagnósticos (não só “Nenhuma interação ainda”)  
- [ ] Docs `running.md` / `min-flow.md` citam regra do sessionId único e “select ≠ reconfig agent”

## Failure diagnosis

| Symptom | Check |
|---------|--------|
| Feed vazio no shell, STT dashboard tem texto | sessionId agent ≠ sessão ativa → mismatch banner? |
| Banner não aparece com agent externo | cmdline sem `--session` legível → source unknown; use Direct start or fix CLI |
| Assistente vazio com partials | empty kind `awaiting_final`; wait for Final or check STT finals path |
| Assistente vazio com Final “ok” | not a question / origin off → `no_eligible_question` or prefs |
| Start fails AlreadyRunning | stop external agent manually; then Direct start |

## Out of scope for this quickstart

- Proving GPU Whisper quality  
- Multi-agent  
- Changing transcript contracts  
