# Implementation Plan: Secure credential store (#64)

**Branch**: `feature/issue-64-secure-credential-store`  
**Issue**: [#64](https://github.com/ds1david/assistant-hub-ai/issues/64)  
**Spec**: `specs/029-issue-64-secure-credentials/spec.md`  
**Date**: 2026-07-26

## Summary

Adicionar `SecureSecretStore` no desktop-shell (Tauri/Rust) com backend OS keyring/DPAPI no Windows e fake in-memory em testes. UI de provedores grava `secretRef: os:…` e o valor só no store. Resolução: shell preenche o secret no momento do invoke/test **sem** logar; session-core mantém `env:` para Developer. Atualizar `provider-secrets.md`.

## Technical Context

**Language**: Rust (Tauri commands), TypeScript (UI), Java session-core (sem mudança obrigatória se shell inject)

**Dependencies**: keyring crate ou `windows` DPAPI; hub providers API existente

**Testing**: Vitest (UI, não vaza secret); cargo unit com mock store; session-core tests de env inalterados

**Constraints**: P9; P2 (core sem vendor); CI Linux sem Credential Manager real

## Constitution Check

| P | Status |
|---|--------|
| P1 | Pass — spec 029 |
| P2 | Pass — store no shell, não acopla LLM |
| P3 | Pass — OS store no Windows host; WSL usa env |
| P9 | Pass — FR-006 |
| P10 | Pass — fake store em CI |

## Design decisions

| ID | Decision |
|----|----------|
| R1 | Abstração `SecureSecretStore` + impl OS + Memory |
| R2 | `secretRef` format `os:assistant-hub/providers/<providerId>` |
| R3 | Shell resolve `os:` no client path de test/invoke; core keeps `env:` |
| R4 | No plaintext key in provider JSON from core |

## Project structure

```text
apps/desktop-shell/src-tauri/src/
  secure_store.rs          # trait + memory + os
  secrets_commands.rs      # Tauri put/get/delete/list
apps/desktop-shell/src/
  api-client.ts            # wrappers
  ai-provider-panel.ts     # password field → store + secretRef
docs/security/provider-secrets.md
specs/029-issue-64-secure-credentials/
```

## Delivery

1. Store + commands + tests  
2. UI wire  
3. Invoke/test path resolve  
4. Docs + 002/003 task checkmarks when done  
