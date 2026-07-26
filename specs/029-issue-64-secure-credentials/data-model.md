# Data Model: Secure credentials (#64)

## SecureSecretRecord (OS store entry)

| Field | Notes |
|-------|--------|
| `logicalId` | e.g. `assistant-hub/providers/{providerId}` |
| `secretRef` | `os:{logicalId}` |
| `value` | only in OS store; never in app config files |

## Provider authentication (unchanged shape)

| Field | Notes |
|-------|--------|
| `mode` | none / bearer / api-key |
| `secretRef` | `env:VAR` or `os:…` or null |

## SecureSecretStore (port)

```text
put(logicalId, value) -> Result
get(logicalId) -> Option<SecretString>
delete(logicalId) -> Result
list_ids() -> Vec<String>   // no values
```

## Implementations

- `MemorySecureSecretStore` — tests / optional Linux dev
- `OsSecureSecretStore` — keyring service name `assistant-hub-ai`
