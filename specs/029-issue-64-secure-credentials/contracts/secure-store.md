# Contract: Secure secret store (#64)

## secretRef schemes

| Scheme | Example | Resolver |
|--------|---------|----------|
| `env:` | `env:OPENAI_API_KEY` | session-core `EnvSecretResolver` |
| `os:` | `os:assistant-hub/providers/openai-main` | desktop-shell `SecureSecretStore` |

## Tauri commands (proposed)

```text
secret_store_put { logicalId: string, value: string } -> ()
secret_store_delete { logicalId: string } -> ()
secret_store_list_ids -> string[]
secret_store_has { logicalId: string } -> bool
// NO secret_store_get exposed to frontend JS (value never crosses to webview)
```

Put may be called only from trusted Rust when saving provider form (password field → put → set secretRef on provider → clear field).

## Provider save flow

1. User enters key in password input (not bound to persistent state after save).
2. Shell: `put(logicalId, value)` then `saveAiProvider` with `secretRef: os:…`.
3. Response/config never includes value.

## Invoke/test flow

1. Load provider; if secretRef starts with `os:`, Rust loads value in process.
2. Call session-core with resolution strategy from research R2 (no log of value).
3. Drop value from memory ASAP.

## Errors

| Code / message (safe) | When |
|-----------------------|------|
| SECRET_NOT_FOUND | os: id missing |
| SECRET_STORE_UNAVAILABLE | OS backend error |
| AUTHENTICATION | provider rejects key (existing) |
