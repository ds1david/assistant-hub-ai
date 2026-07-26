# Contract: model discovery + token usage

## `GET /api/ai-providers/{id}/models`

**200**:

```json
{
  "providerId": "ollama-local",
  "models": [
    { "id": "qwen3:8b", "ownedBy": "library" }
  ]
}
```

**404** provider missing · **422** type unsupported · **error body** on upstream failure (tipado via message + opcional errorType no corpo de falha).

On failure of discovery:

```json
{
  "providerId": "...",
  "success": false,
  "errorType": "TIMEOUT",
  "message": "...",
  "models": []
}
```

Prefer always 200 with `ModelsDiscoveryResult` containing success flag for consistency with ConnectionTestResult — simpler for clients.

## `InvocationResult` additive fields

| Field | Type | Notes |
|-------|------|-------|
| `promptTokens` | int \| null | from provider `usage` |
| `completionTokens` | int \| null | |
| `totalTokens` | int \| null | |

`estimatedCostUsd` **not** added this slice (FR-006).
