# Data Model: 026

## CircuitState (enum)

`CLOSED` | `OPEN` | `HALF_OPEN`

## ProviderCircuitSnapshot

| Campo | Tipo |
|-------|------|
| providerId | string |
| state | CircuitState |
| consecutiveFailures | int |
| openUntilEpochMs | long? (null se não OPEN) |

## CircuitBreakerConfig (serviço)

| Campo | Default |
|-------|---------|
| failureThreshold | 5 |
| openDurationMs | 30000 |

## Stream events (SSE data)

**chunk**: `{ "text": string }`  
**done** / **error**: espelha campos de `InvocationResult` (success, providerId, model, output, errorType, message, latencyMs, sourceType, …)
