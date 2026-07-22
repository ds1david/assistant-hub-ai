# Contratos — SF-020 (delta)

O contrato autoritativo vive em `contracts/` na raiz do monorepo (P4). Esta feature **não altera**
nenhum schema.

## `contracts/transcript-event.v2.schema.json` (inalterado)

Canais por processo produzem eventos `transcript.partial.v2`/`transcript.final.v2` usando exatamente os
campos já existentes e já anuláveis do objeto `device`:

- `device.index`: `null` (não há índice PortAudio para uma ativação `ActivateAudioInterfaceAsync`
  escopada a processo).
- `device.name`: string legível identificando o processo alvo (ex.: `"chrome.exe (pid 8842)"`).
- `device.endpointId`: `null` (não há `endpointId` MMDevice — a captura é escopada a processo, não a
  endpoint físico).
- `sourceType` (nível superior, já `required`): `"system"` — mesma categoria já usada por canais
  `kind="loopback"` de dispositivo; captura por processo é uma variação de captura de renderização, não
  uma categoria nova.

Nenhum campo novo (`processId`/`processName`) é adicionado ao objeto `device`. Decisão e alternativas
rejeitadas: `research.md` §5.

## Por que nenhuma mudança de contrato

- O próprio critério de aceite da issue #19 diz "metadados v2 (`channelId`, `sourceType`, `device`)
  preservados" — preservado, não estendido.
- `device` tem `additionalProperties: false`; adicionar campos exigiria uma mudança de schema real (P4:
  compatibilidade documentada, testes de contrato, atualização de samples). Evitável aqui porque os
  campos já existentes e anuláveis já cobrem o caso de uso sem perda de informação essencial (o texto
  livre em `device.name` já identifica o processo para um humano lendo a transcrição/dashboard).
- Se um consumidor futuro precisar de `processId`/`processName` estruturados (em vez de texto livre em
  `device.name`), isso é uma extensão de contrato independente, com seu próprio ciclo de spec/PR — não
  bloqueia nem faz parte desta feature.

## Nenhum endpoint/CLI novo

Esta feature não expõe nenhuma interface externa nova (API, CLI) — `process_id`/`process_name` são
apenas dois campos novos no seletor `device` já existente dentro do YAML de perfil (`profiles/*.yaml`),
consumido só internamente pelo agente.
