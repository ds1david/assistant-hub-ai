# Contrato: `sourceType` em resultado de invocação (issue #40)

Extensão aditiva do contrato REST/Tauri documentado em  
`specs/015-issue-37-ai-provider-hub/contracts/ai-provider-api.md`.  
Formalidade: código Java como fonte de verdade em runtime; este arquivo é a referência de design para tasks/implement e para revisores (SC-004 / FR-007).

## Princípios

1. **Entrada** da invocação **não** aceita `sourceType` do chamador.  
2. **Saída** de `InvocationResult` **pode** incluir `sourceType` (`null`/omitido quando N/A).  
3. Vocabulário canônico = contrato transcript v2: `microphone` \| `system`.  
4. Resolução **server-side** a partir de eventos da sessão (`HubEvent.correlation`).

## REST — `POST /api/ai-providers/invoke`

### Request (inalterado quanto a origem)

```json
{
  "sessionId": "string (obrigatório)",
  "channelId": "string | omitido | null",
  "route": "string (obrigatório)",
  "capability": "string (obrigatório)",
  "input": "string (obrigatório)"
}
```

- **Proibido** no contrato de entrada: campo `sourceType` como fonte de verdade.  
  (Se um cliente enviar campos extras, o servidor **não** os usa para origem.)

### Response `200` — `InvocationResult` (campo aditivo)

| Campo | Tipo | Notas |
|-------|------|-------|
| …campos 015… | | inalterados |
| `sourceType` | `string \| null` | Presente com valor canônico se `channelId` foi resolvido; `null` se invocação sem canal |

Exemplo (canal microfone):

```json
{
  "providerId": "fake-1",
  "model": "fake-model",
  "capability": "chat",
  "sessionId": "…",
  "channelId": "mic-1",
  "sourceType": "microphone",
  "success": true,
  "errorType": null,
  "output": "…",
  "message": null,
  "latencyMs": 12,
  "occurredAt": "2026-07-25T12:00:00Z"
}
```

Exemplo (sem canal):

```json
{
  "providerId": "fake-1",
  "capability": "chat",
  "sessionId": "…",
  "channelId": null,
  "sourceType": null,
  "success": true,
  "latencyMs": 10,
  "occurredAt": "…"
}
```

### Erros novos / estendidos (pré-provedor)

| HTTP | Condição | Corpo (ilustrativo) |
|------|----------|---------------------|
| `422` | `channelId` presente e `sessionId` não é UUID válido | `{ "error": "…" }` |
| `422` | `channelId` presente e origem não resolvível (sem eventos / sem sourceType no canal / sessão sem eventos) | `{ "error": "…" }` |
| `422` | origem no canal fora de `{microphone, system}` | `{ "error": "…" }` |
| `422` | eventos do mesmo canal com origens distintas | `{ "error": "…" }` |

Erros 015 existentes permanecem: `404` rota (e sessão se já mapeado), `422` type sem adaptador, etc.

**Fallback de rota**: **não** roda quando a falha é de origem de canal (request nem chega ao loop de provedores com sucesso de resolução).

### Fora deste contrato

- `POST /api/ai-providers/{id}/test` — **sem** `sourceType` (ConnectionTestResult inalterado).  
- Mutações de provedor — inalteradas.

## Tauri / TypeScript (espelho aditivo)

| Camada | Mudança |
|--------|---------|
| `InvocationResult` (Rust) | campo opcional `source_type` / wire `sourceType` |
| `InvocationResult` (TS) | `sourceType?: string \| null` |
| `invoke_ai_provider` args | **sem** `sourceType` de entrada |
| `InvokeRequest` Rust | inalterado (só `sessionId`, `channelId?`, `route`, `capability`, `input`) |

## Log estruturado (observabilidade)

Linha `ai-provider-invocation` **deve** incluir `sourceType=` com o valor resolvido ou `null` quando N/A.  
**Não** logar: `output`, `message`, segredos, áudio.

## Compatibilidade

- **Aditiva** na resposta: clientes antigos que ignoram campos novos continuam válidos.  
- **Comportamental** para requests que enviam `channelId` sem eventos de origem na sessão: passam a receber **422** em vez de invoke “cego”. Documentar no changelog da fatia; testes que usavam `channelId` sem fixture de eventos devem ser atualizados (research Decision 6).

## Critério de revisão humana (SC-004)

Em ≤10 minutos, um revisor deve conseguir confirmar:

1. Este documento + testes automatizados listados no [quickstart.md](../quickstart.md).  
2. Resultado com `sourceType` canônico quando há canal + eventos.  
3. `null` sem canal; 422 nos três casos de falha de origem.  
4. Débito #40 tratável como resolvido no tracking de release.
