# Research: #64 Secure credentials

## R1 — Where secrets live

**Decision**: Desktop OS store (Windows Credential Manager via `keyring` crate). Not SQLite, not YAML.

**Rationale**: Aligns with provider-secrets.md `os:`; P9; OS encryption at rest.

## R2 — Who resolves `os:`

**Decision**: **Shell resolves** `os:` when calling session-core invoke/test endpoints that currently expect the core to resolve `env:`. Options evaluated:

| Option | Pros | Cons |
|--------|------|------|
| A. Shell sets process env before call | Simple | Racy multi-provider; env visible in process |
| B. Core accepts ephemeral secret header | Flexible | New API surface; must never log |
| C. Core reads Windows store from JVM | Bad | Core often on WSL — no access |

**Chosen for v1**: **B-lite** — extend Tauri `invoke_ai_provider` / `test_connection` path: Rust side loads secret from store if `secretRef` starts with `os:`, and passes to session-core via existing auth resolution **or** temporary override field that is redacted in logs. If core API cannot accept override without schema change, use documented approach: shell writes to a **user-only** ephemeral env for that process (session-core sibling) — prefer additive optional field on invoke DTO `secretOverride` **never logged** (plan implement validates).

Minimal path if core change is heavy: store + set `secretRef` still `env:` but shell manages a local `.env` outside repo — **rejected** (docs require `os:`).

## R3 — logical id

**Decision**: `os:assistant-hub/providers/{providerId}`

## R4 — Linux CI

**Decision**: `MemorySecureSecretStore` behind feature/cfg; OS store on Windows targets.
