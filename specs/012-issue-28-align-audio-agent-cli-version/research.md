# Research: Alinhar VERSION reportada pelo CLI do audio-agent (Issue #28)

Nenhum item da Technical Context ficou marcado como `NEEDS CLARIFICATION` — o escopo é pequeno e as
decisões abaixo resolvem as únicas questões técnicas em aberto deixadas pela spec (Assumptions:
"mecanismo concreto de sincronização... é uma decisão técnica de implementação... detalhado em
`plan.md`").

## Decisão 1 — Onde fica a única constante hardcoded dentro do pacote

**Decision**: `assistant_hub_audio/__init__.py:__version__` passa a ser a única string de versão mantida
manualmente dentro do código do pacote. `main.py` importa esse valor (`from . import __version__` /
`from assistant_hub_audio import __version__`) em vez de declarar `VERSION = "0.1.7"` separadamente.

**Rationale**: `__init__.py` já é o local convencional em pacotes Python para expor `__version__` como
atributo público do módulo (usado por `importlib.metadata`, ferramentas de introspecção, e por
convenção PEP recomendada). Colocar a fonte ali, em vez de em `main.py`, evita acoplar a versão do
pacote ao módulo de entrada do CLI — outros pontos de consumo futuros (testes, scripts de build) importam
`assistant_hub_audio` sem precisar importar `main`.

**Alternatives considered**:
- Manter a constante em `main.py` e fazer `__init__.py` importar de lá — invertido e menos convencional;
  a maioria das ferramentas de packaging (`setuptools.dynamic`, `importlib.metadata`) espera encontrar
  `__version__` no pacote raiz, não em um submódulo de CLI.
- Ler a versão diretamente do arquivo `VERSION` da raiz do monorepo em runtime (`Path(__file__).parents[N] / "VERSION"`) — rejeitado: o agente Windows é distribuído/instalado separadamente do
  monorepo (ADR-0003, `specs/002-desktop-distribution/` futuro), e um caminho relativo ao monorepo não é
  garantido de existir no host onde o pacote foi instalado. Quebraria exatamente no cenário descrito no
  Edge Case da spec ("instalado sem `pyproject.toml`/árvore do monorepo disponível em runtime").

## Decisão 2 (revisada) — `pyproject.toml` permanece estático; não usar `dynamic = ["version"]`

> Esta decisão substitui uma versão anterior deste documento que propunha `dynamic = ["version"]` via
> `[tool.setuptools.dynamic]`. Descoberta durante `/speckit-implement`, antes de qualquer alteração de
> código: **já existe** `scripts/release/check-version.sh` (citado pela seção "Versionamento" da
> constituição, executado como o step "Version consistency" do job `policy` em `.github/workflows/ci.yml`),
> que faz `grep -E '(?m)^version\s*=\s*["\']([^"\']+)["\']'` sobre o texto de
> `agents/windows-audio-agent/pyproject.toml` para extrair a versão do agente e compará-la a `VERSION`.

**Decision**: `pyproject.toml` **mantém** `version = "0.1.8"` estático em `[project]`, sem alteração.
Nenhuma migração para `dynamic`/`[tool.setuptools.dynamic]`.

**Rationale**: `dynamic = ["version"]` remove a linha `version = "..."` literal que
`check-version.sh` já depende de encontrar via regex; o script já trata ausência de match como
`<ausente>` e falharia a checagem existente (que hoje passa, pois `0.1.8` já está correto). Trocar o
mecanismo de versionamento do `pyproject.toml` não é necessário para resolver a issue #28 — o valor ali
já está correto e já é verificado; o drift real está em `main.py`/`__init__.py`, que `check-version.sh`
não toca hoje. Preferir não tocar em um mecanismo que já funciona.

**Alternatives considered**:
- `dynamic = ["version"]` lendo `assistant_hub_audio.__version__` via `[tool.setuptools.dynamic]`
  (proposta original) — rejeitada pelo motivo acima.
- `setuptools-scm` (versão derivada de tags Git) — rejeitado: a constituição já define `VERSION` como
  fonte única do monorepo e reserva tags a "processo de release, nunca por PR de feature"; introduzir
  derivação por tag Git criaria uma quarta fonte concorrente em vez de simplificar.

## Decisão 3 (revisada) — Estender `check-version.sh` em vez de criar um novo step em `ci.yml`

> Também revisada após a descoberta acima: em vez de um novo step no job `windows-audio-agent-unit`
> (proposta original), a checagem de FR-005 é feita estendendo o script que a constituição já nomeia
> para esse fim.

**Decision**: Adicionar em `scripts/release/check-version.sh` um novo bloco `check` para
`agents/windows-audio-agent/src/assistant_hub_audio/__init__.py`, extraindo `__version__` com o mesmo
estilo de regex Python já usado ali para o bloco "Agent pyproject" (texto puro, sem `import`/instalação
do pacote), logo após esse bloco. Nenhuma mudança em `.github/workflows/ci.yml`: o step "Version
consistency" já existente no job `policy` passa a cobrir também o `__init__.py` do agente.

**Rationale**:
- Reaproveita o mecanismo que a seção "Versionamento" da constituição já cita explicitamente, em vez de
  introduzir uma segunda forma de checagem de versão no repositório.
- Não requer instalar o pacote: o job `windows-audio-agent-unit` roda os testes via
  `PYTHONPATH=agents/windows-audio-agent/src pytest ...` (`.github/workflows/ci.yml:86`), deliberadamente
  **sem** `pip install`, para não puxar `PyAudioWPatch`/`pycaw` (Windows-only, sem wheel Linux) no runner
  Ubuntu (comentário existente: "Install test deps (no Windows-only pycaw/PyAudioWPatch on Linux)").
  Qualquer checagem baseada em `importlib.metadata.version(...)` (que exige instalação real do pacote)
  falharia nesse job como está configurado hoje; leitura estática de texto (regex) não tem essa
  dependência.
- Falha cedo (CI, no job `policy`, que já roda em todo push/PR) exatamente no cenário que gerou a issue
  #28.

**Alternatives considered**:
- Novo step no job `windows-audio-agent-unit`, instalando o pacote e importando-o (proposta original) —
  funciona em tese, mas exigiria mudar esse job para instalar o pacote (quebrando o isolamento
  deliberado de dependências Windows-only nesse runner) ou aceitar uma segunda checagem paralela à de
  `check-version.sh`; rejeitada em favor de reaproveitar o mecanismo já existente.
- Script Python compartilhado (`scripts/check_version_alignment.py`) chamado por ambos os jobs
  (transcription-service e audio-agent) — mais DRY, mas expande o escopo desta correção pontual para um
  refactor do job do transcription-service já existente e estável; fica registrado aqui como melhoria
  futura possível, fora de escopo desta issue (spec Assumptions: sem ampliar escopo além do drift do
  audio-agent).
- Checar via `pytest` apenas (sem step de CI dedicado) — insuficiente: FR-005 exige explicitamente uma
  checagem de CI análoga à já existente, não apenas cobertura de teste unitário local (que FR-006 já
  cobre separadamente).
