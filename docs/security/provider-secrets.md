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

## Aplicação desktop

A aplicação deverá usar o armazenamento seguro do Windows. O arquivo de configuração guardará apenas um identificador lógico:

```yaml
secretRef: os:assistant-hub/nvidia/default
```

## Exportação

Exports incluem configurações, rotas e modelos, mas substituem qualquer referência local sensível por um placeholder explícito.
