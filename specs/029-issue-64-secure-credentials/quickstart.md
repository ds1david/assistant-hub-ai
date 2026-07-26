# Quickstart: Secure credentials (#64)

## Automated (WSL/CI)

```bash
cd apps/desktop-shell && npm test -- --run
cd apps/desktop-shell/src-tauri && cargo test secure_store
# session-core env secrets regression
mvn -pl services/session-core -am test -Dtest='*Secret*'
```

## Manual Windows

1. Build/run shell (`cargo tauri dev --features gui` no host Windows).
2. Providers: add provider, mode bearer, paste API key, save.
3. Confirm `secretRef` shows `os:assistant-hub/providers/…`.
4. Confirm no key in `%APPDATA%\…` provider files / yaml.
5. Test connection → OK or typed provider error.
6. Live-answer invoke works without `$env:API_KEY`.
7. Delete secret → test fails with missing secret (safe message).

## Developer env fallback

```bash
export OPENAI_API_KEY=...
# secretRef: env:OPENAI_API_KEY
```
