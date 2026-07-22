# Feature Specification: Alinhar VERSION reportada pelo CLI do audio-agent (Issue #28)

**Feature Branch**: `012-issue-28-align-audio-agent-cli-version`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Issue #28 [chore] alinhar VERSION reportada pelo CLI do audio-agent."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operador confia na versão reportada por `--version` (Priority: P1)

Um operador ou mantenedor, ao investigar um bug de campo ou validar um deploy, roda `assistant-hub-audio --version` no host Windows para saber exatamente qual build do agente está em uso. Hoje esse comando reporta `0.1.7`, um valor hardcoded em `main.py` que já ficou defasado em relação ao arquivo `VERSION` da raiz do monorepo (`0.1.8`, fonte única segundo a constituição) e ao `pyproject.toml` do agente (também `0.1.8`). Isso torna o `--version` não confiável para diagnóstico e suporte.

**Why this priority**: É o sintoma direto da issue e a única saída do CLI hoje usada para identificar a versão em campo; sem isso corrigido, qualquer triagem de bug baseada em versão reportada é potencialmente enganosa.

**Independent Test**: Rodar `assistant-hub-audio --version` (ou `python -m assistant_hub_audio --version`) em um checkout limpo e comparar a saída com o conteúdo de `VERSION` na raiz do monorepo — devem ser idênticos.

**Acceptance Scenarios**:

1. **Given** o arquivo `VERSION` na raiz do monorepo contém `0.1.8`, **When** o operador roda `assistant-hub-audio --version`, **Then** a saída reporta `0.1.8` (mesmo valor, sem hardcode divergente em `main.py`).
2. **Given** uma futura atualização do arquivo `VERSION` da raiz (ex.: `0.1.9`) sem qualquer edição manual em `main.py`, **When** o pacote do agente é reconstruído/reinstalado, **Then** `--version` reporta o novo valor automaticamente.

---

### User Story 2 - Fontes internas de versão do pacote não divergem entre si (Priority: P2)

Além do CLI, o pacote expõe `assistant_hub_audio.__version__` (hoje `0.1.6`, também defasado e não referenciado por `main.py`) e o `pyproject.toml` declara `version = "0.1.8"`. Um desenvolvedor que importa o pacote programaticamente (`import assistant_hub_audio; assistant_hub_audio.__version__`) ou inspeciona os metadados instalados (`importlib.metadata.version(...)`) precisa ver o mesmo número reportado pelo CLI, sem precisar saber que existem três lugares distintos guardando "a versão".

**Why this priority**: Reduz o risco de a mesma classe de bug (drift de versão) reaparecer em outro ponto de acesso à versão do pacote, mesmo não sendo o sintoma citado na issue.

**Independent Test**: Em um ambiente de teste (WSL, sem hardware), instalar o pacote localmente e comparar `assistant_hub_audio.__version__`, a saída de `assistant-hub-audio --version` e `VERSION` da raiz — os três devem coincidir.

**Acceptance Scenarios**:

1. **Given** o pacote instalado a partir do `pyproject.toml` atual, **When** o código lê `assistant_hub_audio.__version__`, **Then** o valor é igual ao de `VERSION` na raiz e ao reportado por `--version`.
2. **Given** o `pyproject.toml` do agente, **When** sua versão é comparada com `VERSION` da raiz, **Then** ambos coincidem (sem exigir duas edições manuais separadas para manter o alinhamento).

---

### User Story 3 - CI impede regressão futura de drift de versão no audio-agent (Priority: P3)

A constituição do projeto já declara que "CI falha se README, serviço FastAPI, `pyproject` do agent ou asserts divergirem de `VERSION`", e o pipeline (`.github/workflows/ci.yml`) já tem um smoke test equivalente para o serviço de transcrição (FastAPI). O CLI do audio-agent não tem checagem análoga hoje, o que é exatamente como esse drift passou despercebido até virar a issue #28. Um mantenedor quer que uma futura tentativa de editar apenas um dos três lugares (VERSION, pyproject, CLI) quebre o CI antes de chegar a `main`.

**Why this priority**: É prevenção de regressão, não o sintoma relatado; tem valor mesmo isolada, mas depende das User Stories 1 e 2 já terem uma fonte única para checar.

**Independent Test**: Introduzir deliberadamente um valor divergente em `main.py` (ex.: voltar para `"0.1.7"`) em um branch de teste e confirmar que o job de CI correspondente falha; reverter e confirmar que o job passa.

**Acceptance Scenarios**:

1. **Given** o pipeline de CI, **When** `VERSION`, `pyproject.toml` do agente e o valor reportado por `--version` estão alinhados, **Then** o job de checagem de versão do audio-agent passa.
2. **Given** o mesmo pipeline, **When** qualquer um dos três valores é editado manualmente e diverge dos demais, **Then** o job falha com uma mensagem que identifica qual arquivo/fonte está desalinhado.

---

### Edge Cases

- O que acontece se o pacote for instalado sem o `pyproject.toml` disponível em runtime (ex.: binário empacotado da feature futura `specs/002-desktop-distribution/`)? A versão reportada por `--version` não pode depender de ler `pyproject.toml` em disco no runtime; deve vir de um valor resolvido em build/empacotamento (ex.: metadado do pacote instalado via `importlib.metadata`, ou constante gerada a partir de `VERSION` no momento do build).
- O que acontece se `VERSION` da raiz for atualizado mas o agente Windows não for reinstalado/reconstruído? `--version` continua reportando a versão do build instalado (comportamento esperado de qualquer CLI versionado) — não há leitura dinâmica de `VERSION` em tempo de execução no host Windows.
- O que acontece com o `__version__` do pacote (`assistant_hub_audio/__init__.py`) hoje hardcoded e não referenciado por `main.py`? Deve deixar de ser uma terceira fonte manual e passar a ser derivado da mesma fonte usada pelo CLI, eliminando a possibilidade de divergir de novo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O comando `assistant-hub-audio --version` MUST reportar o mesmo valor de versão contido no arquivo `VERSION` da raiz do monorepo, para o build correspondente.
- **FR-002**: `main.py` MUST NOT declarar um valor de versão hardcoded independente (`VERSION = "0.1.7"`); o valor exibido MUST vir de uma única fonte compartilhada dentro do pacote do agente.
- **FR-003**: `assistant_hub_audio.__version__` MUST reportar o mesmo valor que `assistant-hub-audio --version` e que `pyproject.toml`; não pode existir uma segunda constante de versão mantida manualmente em paralelo.
- **FR-004**: O `pyproject.toml` do agente (`agents/windows-audio-agent/pyproject.toml`) MUST continuar sendo a fonte de versão do pacote Python instalável e MUST ser mantido igual ao `VERSION` da raiz, conforme já exigido pela seção "Versionamento" da constituição do projeto.
- **FR-005**: O pipeline de CI (`.github/workflows/ci.yml`) MUST incluir uma checagem automatizada, análoga à já existente para o serviço de transcrição (linha ~64, "Import smoke test (version from VERSION file)"), que falha se a versão reportada pelo CLI do audio-agent (`--version` ou `__version__`) divergir do arquivo `VERSION` da raiz.
- **FR-006**: A suíte de testes automatizados do audio-agent (WSL, sem hardware) MUST incluir um teste de regressão que verifique `assistant_hub_audio.__version__` (ou a saída de `--version`) contra o `pyproject.toml`/`VERSION`, prevenindo reintrodução do drift.
- **FR-007**: A correção MUST NOT alterar o comportamento de nenhum outro subcomando do CLI (`list-devices`, `probe`, `run`) além da saída de `--version`.

### Key Entities

- **Fonte única de versão**: o arquivo `VERSION` na raiz do monorepo — já definido pela constituição do projeto como a fonte de verdade para todo o monorepo (serviço de transcrição, README, `pyproject` do agente).
- **Versão reportada do audio-agent**: o valor de versão observável a partir do pacote `assistant_hub_audio` — hoje espalhado em três lugares (`main.py:VERSION`, `__init__.py:__version__`, `pyproject.toml:version`) e que esta feature consolida em uma única fonte dentro do pacote, sincronizada com `VERSION` da raiz.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `assistant-hub-audio --version` reporta exatamente o mesmo valor presente no arquivo `VERSION` da raiz, verificável em um checkout limpo sem edição manual adicional.
- **SC-002**: Existe exatamente uma constante/fonte de versão mantida manualmente dentro do pacote do audio-agent (o `pyproject.toml`); nenhum outro arquivo do pacote (`main.py`, `__init__.py`) contém um número de versão hardcoded independente.
- **SC-003**: O CI falha em 100% das tentativas de merge que introduzam divergência entre `VERSION` da raiz e a versão reportada pelo audio-agent, com o mesmo nível de proteção já aplicado ao serviço de transcrição.
- **SC-004**: Zero regressões na suíte automatizada existente do audio-agent (`list-devices`, `probe`, `run`, perfis) após a mudança.

## Assumptions

- "CLI do audio-agent" refere-se ao pacote `agents/windows-audio-agent` (`assistant-hub-audio`, entrypoint `assistant_hub_audio.main:main`), único agente Python com um `VERSION`/`--version` divergente identificado no repositório.
- O mecanismo concreto de sincronização entre `VERSION` (raiz) e o pacote do agente (ex.: ler `importlib.metadata` do pacote instalado, gerar uma constante no build, ou um passo de sincronização versionado) é uma decisão técnica de implementação e será detalhado em `plan.md`; esta spec fixa apenas o requisito de fonte única e o comportamento observável do CLI.
- O agente roda em Python nativo do Windows (ADR-0003/ADR-0007) mas a checagem de CI descrita em FR-005/FR-006 roda em WSL/Linux (P3/P10 — testes automatizados não dependem de hardware Windows), na mesma esteira já usada pelo job `windows-audio-agent-unit` do pipeline.
- Fora de escopo: qualquer mudança no número de versão em si (ex.: bump de `0.1.8` para `0.1.9`) ou no processo de release/tag, que a constituição reserva a "processo de release, nunca por PR de feature".
