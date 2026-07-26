# Contract: circuit breaker + invoke stream

## REST aditivo (session-core)

| Método | Path | Descrição |
|--------|------|-----------|
| `POST` | `/api/ai-providers/invoke` | **Existente** — agora respeita breaker |
| `POST` | `/api/ai-providers/invoke/stream` | **Novo** — SSE, mesmo body de invoke |
| `GET` | `/api/ai-providers/circuit-status` | **Novo** — lista snapshots de breaker |

### Body invoke / invoke/stream

Igual 015/017:

```json
{
  "sessionId": "uuid-or-opaque",
  "channelId": "optional",
  "route": "chat-route",
  "capability": "chat",
  "input": "texto"
}
```

### SSE

```
event: chunk
data: {"text":"Olá"}

event: chunk
data: {"text":" mundo"}

event: done
data: {"providerId":"fake-1","success":true,"output":"Olá mundo",...}
```

Em falha terminal:

```
event: error
data: {"providerId":"...","success":false,"errorType":"CIRCUIT_OPEN",...}
```

### `InvocationErrorType` aditivo

`CIRCUIT_OPEN` — provedor não chamado porque o circuito está aberto (ou último erro da cadeia por esse motivo).

## Compatibilidade

- Clientes síncronos existentes: sem mudança de path; possível novo `errorType`.
- Schema YAML de provedores: inalterado.
