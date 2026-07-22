---

description: "Task list for aligning the audio-agent CLI reported VERSION (Issue #28)"
---

# Tasks: Alinhar VERSION reportada pelo CLI do audio-agent (Issue #28)

**Input**: Design documents from `/specs/012-issue-28-align-audio-agent-cli-version/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md (N/A — sem entidades), quickstart.md

**Tests**: FR-006 exige explicitamente um teste de regressão (`tests/test_version.py`); incluído abaixo
como parte da User Story 2.

**Organization**: Tasks agrupadas por user story (spec.md). Esta é uma correção prospectiva — nenhuma
linha de código foi alterada ainda; todas as tasks começam `[ ]`.

> **Nota de revisão (durante `/speckit-implement`, antes de qualquer código)**: a versão original desta
> lista assumia (a) tornar `pyproject.toml` dinâmico via `[tool.setuptools.dynamic]` e (b) um novo step
> em `.github/workflows/ci.yml`. Ambas foram substituídas — ver `research.md` (Decisões 2 e 3 revisadas)
> e `plan.md`. `pyproject.toml` permanece inalterado; a checagem de CI (FR-005) estende
> `scripts/release/check-version.sh` em vez de criar um novo step.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependências)
- **[Story]**: A qual user story esta task pertence (US1, US2, US3)
- Caminhos de arquivo exatos incluídos nas descrições

---

## Phase 1: Setup

**Purpose**: Preparar ambiente de teste do agente e registrar baseline antes de qualquer alteração

- [X] T001 [P] Criar/ativar `.venv-agent` e instalar apenas as dependências não-Windows-only (`cd agents/windows-audio-agent && python -m venv .venv-agent && source .venv-agent/bin/activate && pip install pytest PyYAML numpy scipy websockets psutil`) — **sem** `pip install -e .` (evita `PyAudioWPatch`, sem build para Linux; mesmo padrão do job `windows-audio-agent-unit` do CI) — sem alteração de código (quickstart.md Setup)
- [X] T002 Rodar a suíte de testes atual (`PYTHONPATH=agents/windows-audio-agent/src pytest -q agents/windows-audio-agent/tests`) e registrar a contagem de "passed" como baseline, para comparação de não-regressão em T014 (FR-007) — baseline: 95 passed

**Checkpoint**: Ambiente pronto e baseline registrado; nenhuma alteração de código ainda.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Estabelecer a única constante de versão hardcoded dentro do código do pacote, da qual
US1/US2/US3 dependem

**⚠️ CRITICAL**: Nenhuma user story pode ser implementada sem esta task

- [X] T003 Atualizar `__version__ = "0.1.8"` em `agents/windows-audio-agent/src/assistant_hub_audio/__init__.py`, alinhado ao conteúdo atual de `VERSION` na raiz do monorepo — passa a ser a única constante de versão mantida manualmente dentro do código do pacote (`pyproject.toml` continua com sua própria cópia estática, inalterada — FR-002, FR-003; research.md Decisão 1)

**Checkpoint**: Fonte única definida dentro do código do pacote — user stories abaixo podem prosseguir em
paralelo.

---

## Phase 3: User Story 1 - Operador confia na versão reportada por `--version` (Priority: P1) 🎯 MVP

**Goal**: `assistant-hub-audio --version` reporta o mesmo valor do arquivo `VERSION` da raiz, sem hardcode
divergente em `main.py` (FR-001)

**Independent Test**: quickstart.md Cenário 1 — comparar `cat VERSION` com
`PYTHONPATH=src python -m assistant_hub_audio.main --version`

### Implementation for User Story 1

- [X] T004 [US1] Remover `VERSION = "0.1.7"` hardcoded de `agents/windows-audio-agent/src/assistant_hub_audio/main.py` e importar `__version__` de `assistant_hub_audio` (`from . import __version__`), usando-o em `parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")` — depends on T003 (FR-001, FR-002)
- [X] T005 [US1] Revisar o diff de `main.py` (T004) e confirmar que nenhum outro subcomando (`list-devices`, `probe`, `run`) foi alterado — checagem de diff, sem novo código (FR-007) — diff confirmado: só a linha `--version` mudou
- [X] T006 [P] [US1] Validar manualmente quickstart.md Cenário 1: `PYTHONPATH=agents/windows-audio-agent/src python -m assistant_hub_audio.main --version` reporta o mesmo valor de `VERSION` na raiz — depends on T004 — confirmado: `main.py 0.1.8` == `VERSION` (0.1.8)

**Checkpoint**: User Story 1 completa e testável de forma independente — CLI corrigido.

---

## Phase 4: User Story 2 - Fontes internas de versão do pacote não divergem entre si (Priority: P2)

**Goal**: `assistant_hub_audio.__version__` e `--version` reportam o mesmo valor entre si e o mesmo valor
já presente em `pyproject.toml`/`VERSION`, sem que `main.py` mantenha uma segunda constante em paralelo
(FR-003, FR-004)

**Independent Test**: quickstart.md Cenários 2 e 3

### Tests for User Story 2

- [X] T007 [P] [US2] Criar `agents/windows-audio-agent/tests/test_version.py` com teste de regressão comparando `assistant_hub_audio.__version__` ao conteúdo do arquivo `VERSION` na raiz do monorepo (leitura relativa a partir do arquivo de teste — `Path(__file__).resolve().parents[3] / "VERSION"` — sem depender de instalação do pacote nem de `importlib.metadata`) — depends on T003 (FR-006)

### Implementation for User Story 2

- [X] T008 [US2] Rodar `PYTHONPATH=agents/windows-audio-agent/src pytest agents/windows-audio-agent/tests/test_version.py -v` confirmando que passa (quickstart.md Cenário 3) — depends on T004, T007 — 1 passed
- [X] T009 [P] [US2] Confirmar (checagem de diff, sem alteração de arquivo) que `agents/windows-audio-agent/pyproject.toml` permanece com `version = "0.1.8"` estático, sem migração para `dynamic`/`[tool.setuptools.dynamic]` — depends on T003 (FR-004; research.md Decisão 2 revisada) — `git diff` vazio para o arquivo, confirmado

**Checkpoint**: User Story 2 completa — `__version__` e `--version` alinhados entre si e a `VERSION`/`pyproject.toml`; `main.py` não mantém mais constante própria.

---

## Phase 5: User Story 3 - CI impede regressão futura de drift de versão no audio-agent (Priority: P3)

**Goal**: `scripts/release/check-version.sh` (já executado pelo CI) falha se `VERSION`, `pyproject.toml`
ou `__init__.py` do agente divergirem entre si (FR-005)

**Independent Test**: quickstart.md Cenário 4 e o cenário de regressão negativa (drift deliberado)

### Implementation for User Story 3

- [X] T010 [US3] Adicionar em `scripts/release/check-version.sh` um novo bloco `check` para `agents/windows-audio-agent/src/assistant_hub_audio/__init__.py:__version__`, extraído por regex Python no mesmo estilo do bloco "Agent pyproject" já existente logo acima (sem `import` do pacote, sem instalação) — depends on T003 (FR-005; research.md Decisão 3 revisada)
- [X] T011 [P] [US3] Validar localmente `./scripts/release/check-version.sh` (quickstart.md Cenário 4), confirmando saída `OK` para o novo bloco e exit code `0` — depends on T010 — confirmado: `OK windows-audio-agent __init__.py: 0.1.8`, "Versões alinhadas em 0.1.8"
- [X] T012 [US3] Executar o cenário de regressão negativa do quickstart.md (drift deliberado em `__init__.py`, confirmar que `test_version.py` E `check-version.sh` falham, reverter a alteração de teste) — depends on T007, T010 — confirmado: `test_version.py` FAILED (`0.0.0-drift-test` != `0.1.8`) e `check-version.sh` FAIL/exit 1; revertido para `0.1.8` (nota: `git checkout --` restaurou o commit, não o T003 em working tree — recriado manualmente e reconfirmado verde)

**Checkpoint**: Todas as user stories completas — drift de versão no audio-agent agora é bloqueado pelo CI
(job `policy`, step "Version consistency"), mesmo mecanismo já usado para README/FastAPI/pyproject.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirmar ausência de regressão e preparar o fechamento do ciclo (gate G3)

- [X] T013 [P] Rodar a suíte completa do agente (`PYTHONPATH=agents/windows-audio-agent/src pytest -q agents/windows-audio-agent/tests`) e comparar com o baseline de T002, confirmando zero regressões (SC-004) — depends on T008, T012 — 96 passed (baseline 95 + test_version.py novo); zero regressões
- [X] T014 Preparar diff resumido, riscos e evidências de teste (T002 baseline, T013 pós-mudança, T011/T012 CI) para o PR draft, conforme regra operacional da constituição ("Ao final do ciclo: diff resumido, riscos, testes executados e evidências") — depends on T013 — resumo apresentado no relatório de conclusão desta sessão

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: Depende de Setup. T003 BLOQUEIA todas as user stories
- **User Story 1 (Phase 3)**: Depende de Foundational (T003). Sem dependência de US2/US3
- **User Story 2 (Phase 4)**: Depende de Foundational (T003) e de T004 (US1) para T008, já que o teste roda contra o `main.py` corrigido; T009 é independente
- **User Story 3 (Phase 5)**: Depende de Foundational (T003); T012 depende também de T007 (US2)
- **Polish (Phase 6)**: T013 depende de T008 (US2) e T012 (US3); T014 depende de T013

### Parallel Opportunities

- T004 (US1) e T007/T009 (US2) podem rodar em paralelo após T003 — arquivos diferentes (`main.py` vs `tests/test_version.py`/checagem de `pyproject.toml`)
- T010 (US3, extensão de `check-version.sh`) pode rodar em paralelo com T004 (US1) — arquivos diferentes
- T006 (US1, validação manual) pode rodar em paralelo com T011 (US3, validação local do script)

---

## Parallel Example: User Story 1 + User Story 2 + User Story 3

```bash
# Após Foundational (T003), as três stories tocam arquivos diferentes e podem avançar em paralelo:
Task: "Remove hardcoded VERSION from main.py, import __version__"          # T004 (US1)
Task: "Create tests/test_version.py regression test"                       # T007 (US2)
Task: "Extend check-version.sh with __init__.py check block"               # T010 (US3)
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRITICAL — bloqueia todas as stories)
3. Completar Phase 3: User Story 1
4. **STOP e VALIDAR**: `assistant-hub-audio --version` reporta o valor correto (quickstart.md Cenário 1)
5. Isso já resolve o sintoma relatado na issue #28

### Incremental Delivery

1. Setup + Foundational (T001–T003) → fonte única definida
2. US1 (T004–T006) → CLI corrigido, testável independentemente (MVP)
3. US2 (T007–T009) → `__version__`/`--version` alinhados, `pyproject.toml` confirmado intacto
4. US3 (T010–T012) → CI (via `check-version.sh`) bloqueia regressão futura
5. Polish (T013–T014) → suíte completa sem regressão, evidências prontas para o PR draft

---

## Notes

- `[P]` tasks = arquivos diferentes, sem dependências
- `[Story]` mapeia a task à user story correspondente para rastreabilidade
- Nenhuma task depende de hardware Windows real (P10) — toda a validação roda em WSL/Linux
- Nenhuma task instala o pacote completo (`pip install -e .`) em WSL/Linux — `PyAudioWPatch` não tem
  build para Linux; import via `PYTHONPATH`, mesmo padrão do job `windows-audio-agent-unit` do CI
- Commit após cada task ou grupo lógico
