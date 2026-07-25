# Quickstart de validação: `sourceType` em InvocationResult

**Feature**: `specs/017-issue-40-invocation-sourcetype`  
**Objetivo**: provar o contrato de origem no resultado de invocação sem GPU/hardware (P10).

## Pré-requisitos

- WSL com SDKMAN: Java 21 + Maven (`sdk current`).  
- Branch/feature desta spec aplicada no `session-core` (e espelho desktop se validar tipos).  
- Nenhuma GPU, agente Windows ou provedor remoto obrigatório — usar provedor **fake** do hub.

## Documentos de referência

- [spec.md](./spec.md) — FR/SC e clarificações  
- [data-model.md](./data-model.md) — regras de preenchimento  
- [contracts/invocation-result-sourcetype.md](./contracts/invocation-result-sourcetype.md) — API  

## 1. Testes automatizados (caminho principal)

Na raiz do monorepo (WSL):

```bash
cd services/session-core
mvn test
```

**Esperado**: suite verde, incluindo cenários novos/atualizados de origem:

| Cenário | Esperado |
|---------|----------|
| Canal `mic-1` + evento `sourceType=microphone` + invoke sucesso | `InvocationResult.sourceType == "microphone"`; `sessionId` = UUID real da sessão |
| Canal `sys-1` + evento `system` | `sourceType == "system"` |
| Invoke com falha de provedor (timeout/fake fail) **após** origem resolvida | `success=false` **e** `sourceType` ainda canônico |
| Invoke **sem** `channelId` | `sourceType == null` (ou ausente) e invoke pode ter sucesso; `sessionId` pode ser string não-UUID |
| `channelId` + `sessionId` não-UUID | HTTP 422 / `ChannelOriginUnresolvedException` — **sem** chamada de provedor |
| `channelId` sem eventos na sessão | HTTP 422 / exceção de origem — **sem** chamada de provedor |
| Eventos do mesmo canal com `microphone` e `system` | 422 conflito |
| Evento com origem não canônica (ex.: `"other"`) | 422 |
| Dois canais na mesma sessão, invokes sequenciais/concorrentes | cada resultado com a origem do **seu** canal |
| Log de invocação (T032 / SC-006) | linha `ai-provider-invocation` contém o **mesmo** `sourceType` do resultado; sem canal, não inventa origem |

Filtro útil após implementação (nome ilustrativo):

```bash
mvn test -Dtest='*Origin*,*Invocation*,*SourceType*'
```

## 2. Validação manual mínima da API (opcional)

Com `session-core` no ar, perfil com provedor fake e rota de chat:

1. Criar sessão e **anexar/ingest** ao menos um evento de transcript (ou HubEvent) com `correlation.channelId` + `sourceType=microphone`.  
2. `POST /api/ai-providers/invoke` com `sessionId`, `channelId` do passo 1, rota, `capability=chat`, `input` qualquer.  
3. Verificar JSON de resposta: `"sourceType":"microphone"`.  
4. Repetir invoke **sem** `channelId` → `"sourceType": null`.  
5. Invoke com `channelId` inexistente nos eventos → **422**.

Não é necessário desktop nem agent Windows para fechar SC-001–SC-003.

## 3. Desktop (opcional, não bloqueia o débito)

Se tipos forem atualizados:

```bash
cd apps/desktop-shell && npm test
cd apps/desktop-shell/src-tauri && cargo test
```

**Esperado**: tipos compilam com `sourceType` opcional no resultado; nenhum comando Tauri exige `sourceType` na entrada.

## 4. Tracking do débito (FR-009 / SC-004)

Checklist do revisor (~10 min):

- [ ] Contrato feature-local lido  
- [ ] `mvn test` em `session-core` verde com cenários da tabela  
- [ ] Issue #40 pronta para fechar/comentar como resolvida (ação humana)  
- [ ] Nota de débito `InvocationResult-sourceType` marcada resolvida no próximo changelog/checklist de release (não inventar tag nesta fatia)

## Fora deste quickstart

- Validação Windows WASAPI / SF-020  
- Provedor OpenAI real / NIM  
- Bump Vite (#41)  
- Tag SemVer de produto  
