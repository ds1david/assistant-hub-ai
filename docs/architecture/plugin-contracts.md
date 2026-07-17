# Contratos de plugins

## Dependências

```text
plugin implementation -> plugin-sdk -> JDK
session-core -> plugin-sdk
plugin-sdk -X-> session-core
```

## Ciclo de vida

1. descoberta;
2. validação do descritor e compatibilidade;
3. registro;
4. `start(context)`;
5. consumo/publicação de eventos;
6. `stop()`.

## Compatibilidade

O descritor contém:

- `id` estável;
- versão do plugin;
- versão mínima do SDK;
- capacidades fornecidas;
- permissões requeridas;
- configuração esperada.

## Eventos

Todo evento deve ter:

- identificador único;
- sessão;
- tipo versionado;
- origem;
- horário de ocorrência;
- horário de ingestão;
- payload JSON compatível;
- metadados de correlação.

Tipos iniciais:

- `audio.chunk.received.v1`;
- `transcript.partial.v1`;
- `transcript.final.v1`;
- `session.started.v1`;
- `session.ended.v1`;
- `latency.measured.v1`.
