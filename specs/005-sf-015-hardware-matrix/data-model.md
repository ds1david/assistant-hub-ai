# Data Model: SF-015 — Matriz manual de hardware R1

Não há modelo de dados de software nesta feature — nenhuma classe, tabela ou schema é criado. As "entidades" abaixo são a estrutura conceitual do **documento de evidência**, usada para manter os três arquivos de `docs/validation/sf-015-*.md` consistentes entre si e com `sf-018-windows.md`.

## Cenário de hardware

Representa um agrupamento de dispositivo(s) físico(s) testado como unidade.

| Campo | Descrição | Obrigatório |
|-------|-----------|-------------|
| `nome` | Identificador do cenário (ex.: "conference cam", "Bluetooth output + USB mic", "microfone default") | Sim |
| `prioridade` | P1/P2/P3, herdado da spec (User Story 1/2/3) | Sim |
| `dispositivos` | Lista de Dispositivo WASAPI envolvidos | Sim, ≥1 |
| `casos` | Lista de casos executados (ver seção Casos) | Sim, ≥1 |
| `resultado` | PASS \| FAIL \| BLOCKED | Sim, valor único e final |
| `limitações` | Texto livre explicando BLOCKED ou ressalvas de um PASS parcial | Obrigatório se `resultado != PASS` sem ressalva |

**Regra de validação**: um Cenário só pode ter `resultado = PASS` se todos os seus Casos tiverem checkbox marcado; `resultado = BLOCKED` exige `limitações` preenchido (FR-008); `resultado = FAIL` exige descrição do sintoma observado.

## Dispositivo WASAPI

Representa um endpoint de áudio físico observado durante um cenário.

| Campo | Descrição |
|-------|-----------|
| `friendlyName` | Nome amigável exibido pelo Windows |
| `endpointId` | Identificador MMDevice, obtido via `list-devices --json` |
| `channelId` | Canal atribuído no perfil YAML usado no cenário |
| `sourceType` | `microphone` \| `system`/loopback, conforme perfil |
| `role` | Papel no cenário (ex.: "microfone", "render/loopback", "desabilitado — teste negativo") |

**Relacionamento**: um Cenário de hardware tem 1..N Dispositivo WASAPI; cada Dispositivo pertence a exatamente um Cenário (um mesmo dispositivo físico testado em dois cenários gera dois registros independentes, já que o objetivo é isolar resultado por cenário).

## Caso (dentro de um Cenário)

Espelha os casos já definidos no template `docs/validation/sf-018-windows.md`, reaproveitados pelos três cenários desta matriz:

1. `list-devices` — endpointId presente e correlacionado corretamente.
2. `probe` com `endpointId` — resolve o dispositivo correto.
3. `run` captura — evento v2 contém `endpointId`/`channelId`/`sourceType`; sem regressão de canal.
4. Reboot ou reenumeração — mesmo `endpointId` continua capturando o dispositivo correto mesmo com índice PortAudio diferente.
5. Hot-plug (parcial — SF-019 cobre o listener completo) — após replug, mesmo perfil/endpointId funciona ou falha de forma compreensível.
6. Endpoint desabilitado/inexistente — mensagem distinta, sem fallback silencioso (P7 / ADR-0011).
7. Nomes duplicados (quando aplicável, ex.: dois microfones USB idênticos) — WARNING de enumeration order documentado.

**Regra de validação**: nem todo Caso se aplica a todo Cenário (ex.: "nomes duplicados" só é relevante se o cenário tiver dispositivos com nome repetido) — casos não aplicáveis são marcados como "N/A" explicitamente, nunca deixados em branco.

## Registro de validação (arquivo Markdown)

O artefato final por Cenário, em `docs/validation/`. Estrutura fixa (mesma do template `sf-018-windows.md`): Ambiente → Dispositivos → Perfil usado → Casos → Segurança → Resultado.

**Estado/transição**: cada Registro nasce como template em branco (copiado do padrão SF-018) → em execução (casos sendo marcados) → concluído (`resultado` preenchido com PASS/FAIL/BLOCKED, não mais o placeholder). Não há transição de volta: um resultado só é re-aberto se uma regressão futura for encontrada, o que gera um novo registro/rodada, não uma edição silenciosa do PASS anterior.
