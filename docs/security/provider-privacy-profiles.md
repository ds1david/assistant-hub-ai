# Políticas de privacidade por perfil (R6 — recorte)

Complementa [provider-secrets.md](./provider-secrets.md). Estado em 2026-07-26:

## O que já existe

- Segredos só via `secretRef` (env no Developer); nunca no YAML commitado.
- Logs de invocação: `providerId`, modelo, capability, session/channel ids, latência, tokens totais — **sem** prompt/output.
- Perfis de conversa (`samples/profiles/`) definem persona/comportamento; **não** ainda um flag formal `allowRemoteTranscript: false`.

## Política recomendada (operacional)

| Dado | Local (Ollama) | Remoto (OpenAI/NIM/xAI) |
|------|----------------|-------------------------|
| Transcript / prompt | Preferir para treino e dados sensíveis | Só com consentimento do operador |
| Chaves | N/A ou env local | `secretRef` + vault/OS store (fatia futura) |
| Retenção | Memory Hub local (issue #29) | Conforme política do provedor externo |

## Próximo passo de produto

Campo declarativo no perfil de **conversa** (não só de provedor), por exemplo:

```yaml
privacy:
  allowRemoteProviders: false
  redactPiiBeforeRemote: true
```

Fora do escopo de 027; rastreado em `specs/003-ai-provider-hub/tasks.md`.
