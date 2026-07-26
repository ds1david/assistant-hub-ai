# Segredos de provedores de IA

## Regras

- nunca versionar chaves;
- nunca salvar chaves no YAML de provedores;
- nunca incluir chaves em logs, exceptions, métricas ou exports;
- usar `secretRef` para indicar onde a credencial será resolvida;
- permitir rotação sem alterar o perfil de conversa.

## Desenvolvimento no WSL

Use variáveis de ambiente ou um arquivo `.env.local` ignorado pelo Git:

```bash
export NVIDIA_API_KEY='...'
export OPENAI_API_KEY='...'
```

Referência:

```yaml
secretRef: env:NVIDIA_API_KEY
```

## Aplicação desktop (issue #64)

O shell Tauri usa o **cofre do SO** no Windows (`keyring` / Credential Manager) e um store em memória em outros hosts (para dev; preferir `env:` no WSL).

Formato canônico:

```yaml
secretRef: os:assistant-hub/providers/<providerId>
```

### Fluxo no shell

1. No formulário de provedores, cole a API key no campo **password** (não fica no state da UI após salvar).
2. O shell grava no store (`secret_store_put`) e persiste só o `secretRef` `os:…` no perfil do hub.
3. Em **test connection** / **invoke** / **live-answer**, o shell carrega os valores `os:` e envia `secretOverrides` no body da chamada ao session-core **somente para aquela requisição** (nunca logado no core).
4. Preview mascarado: primeiros caracteres + reticências + sufixo (sem valor completo no webview).
5. Ao remover o provedor, o secret correspondente é apagado do store.

### WSL Developer

Continue usando:

```yaml
secretRef: env:OPENAI_API_KEY
```

com a variável exportada no ambiente do `session-core`.

## Exportação

Exports incluem configurações, rotas e modelos, mas substituem qualquer referência local sensível por um placeholder explícito. O valor do store OS **nunca** entra no export.
