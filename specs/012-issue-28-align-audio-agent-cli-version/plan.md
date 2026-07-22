# Implementation Plan: Alinhar VERSION reportada pelo CLI do audio-agent (Issue #28)

**Branch**: `012-issue-28-align-audio-agent-cli-version` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/012-issue-28-align-audio-agent-cli-version/spec.md`

## Summary

Eliminar o drift de versão do `agents/windows-audio-agent` (`main.py:VERSION="0.1.7"`,
`__init__.py:__version__="0.1.6"` e `pyproject.toml:version="0.1.8"` — três strings mantidas
manualmente, cada uma podendo divergir de `VERSION` na raiz, que já é `0.1.8`).
`assistant_hub_audio/__init__.py:__version__` passa a ser a única constante hardcoded dentro do código
do pacote; `main.py` importa esse valor em vez de declarar o seu próprio. `pyproject.toml` **permanece
estático** (`version = "0.1.8"`, já correto) — descoberto durante `/speckit-implement` que
`scripts/release/check-version.sh` já verifica esse campo por regex (step "Version consistency" do job
`policy`), então mudar para versão dinâmica quebraria esse check já existente sem necessidade (ver
research.md, Decisão 2 revisada). A checagem de CI (FR-005) é feita **estendendo esse mesmo script**
com um novo bloco para `__init__.py`, em vez de criar um novo step em `.github/workflows/ci.yml` — o job
`windows-audio-agent-unit` roda testes via `PYTHONPATH=...` sem instalar o pacote (evita
`PyAudioWPatch`/`pycaw`, Windows-only), então uma checagem baseada em import/`importlib.metadata`
falharia ali; a leitura estática de texto que `check-version.sh` já faz não tem essa dependência
(research.md, Decisão 3 revisada).

## Technical Context

**Language/Version**: Python 3.11+ (`agents/windows-audio-agent/pyproject.toml: requires-python = ">=3.11"`), inalterado — CI já roda a suíte do agente em 3.11 e 3.12 (matrix do job `windows-audio-agent-unit`).

**Primary Dependencies**: Nenhuma dependência nova. `main.py` passa a importar `__version__` de `assistant_hub_audio` (import interno ao pacote, stdlib apenas) em vez de declarar sua própria constante; `pyproject.toml` não é alterado (permanece estático, sem `setuptools-scm` nem `[tool.setuptools.dynamic]`).

**Storage**: N/A.

**Testing**: `pytest` (suíte existente em `agents/windows-audio-agent/tests/`), com um novo `tests/test_version.py` cobrindo FR-006 (`assistant_hub_audio.__version__` == conteúdo de `VERSION` da raiz, lido estaticamente do arquivo). CI: `scripts/release/check-version.sh` estendido com um novo bloco `check` para `__init__.py` — reaproveita o step "Version consistency" já existente no job `policy` de `.github/workflows/ci.yml`, sem novo step/job.

**Target Platform**: WSL/Linux para desenvolvimento, testes automatizados e CI (P3/P10 — sem hardware Windows necessário para esta correção); Windows nativo continua sendo onde o CLI (`assistant-hub-audio --version`) é efetivamente invocado por operadores em campo, mas o comportamento não depende de nada Windows-only.

**Project Type**: CLI/agent Python existente (`assistant-hub-audio`, `agents/windows-audio-agent`) — chore de alinhamento de metadado, sem novo serviço nem nova aplicação.

**Performance Goals**: N/A — mudança não tem caminho de execução em runtime de captura (afeta só `--version`/import do pacote).

**Constraints**: Nenhuma nova dependência de runtime (spec FR — implícito por escopo mínimo); a checagem de CI deve rodar 100% sem hardware/GPU (P10); a fonte de verdade do monorepo continua sendo o arquivo `VERSION` da raiz (seção "Versionamento" da constituição) — este plano não altera esse arquivo nem o valor da versão em si (`0.1.8`), só remove as duas cópias divergentes.

**Scale/Scope**: 3 arquivos existentes modificados (`main.py`, `__init__.py`, `pyproject.toml`) + 1 arquivo de teste novo (`tests/test_version.py`) + 1 step novo em `.github/workflows/ci.yml`. Nenhum módulo novo, nenhuma mudança de escala do agente.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Como esta correção cumpre |
|---|---|---|
| P1 — Spec antes de código | PASS | `spec.md` já escrita e validada (checklist 100% verde) antes deste plano; nenhuma linha de código de domínio alterada ainda. |
| P2 — Core independente de fornecedores | N/A | Mudança de metadado de empacotamento (`pyproject.toml`, `__init__.py`), não toca captura/STT/LLM nem integrações de provedor. |
| P3 — WSL-first | PASS | Toda a verificação (testes + step de CI) roda em WSL/Linux; nada exige host Windows real. |
| P4 — Contratos versionados | N/A | `--version` não é um schema de evento/dado versionado por `contracts/`; é metadado de build do pacote. |
| P5 — Separação por canal e origem | N/A | Sem relação com `sessionId`/`channelId`/`sourceType`. |
| P6 — Isolamento de endpoint de áudio | N/A | Sem alteração em captura, PyAudio ou processos por endpoint. |
| P7 — Identidade de dispositivo | N/A | Sem alteração em resolução de `endpointId`/`index`/`default`. |
| P8 — Automação com autorização | PASS | Nenhuma automação de Git/CI além de um novo step de verificação (não publica, não faz merge/push). |
| P9 — Privacidade | PASS | Nenhum dado novo, sensível ou não, é logado; string de versão é pública por natureza (já exposta hoje). |
| P10 — Qualidade determinística | PASS | Teste novo (FR-006) e step de CI (FR-005) rodam sem hardware/GPU, mesmo padrão do smoke test já existente para o serviço de transcrição. |
| Versionamento (seção dedicada) | PASS | Esta correção é exatamente o que a seção "Versionamento" da constituição já exige ("CI falha se ... `pyproject` do agent ... divergirem de `VERSION`") — hoje inexistente para o audio-agent; este plano fecha essa lacuna. |

Nenhuma violação a justificar — tabela de Complexity Tracking permanece vazia.

## Project Structure

### Documentation (this feature)

```text
specs/012-issue-28-align-audio-agent-cli-version/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command) — N/A, ver nota abaixo
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

Sem `contracts/`: `--version` já existe como flag do CLI (`argparse`, `action="version"`); esta correção
não introduz uma interface nova nem muda seu formato de saída (`%(prog)s {VERSION}`), apenas corrige qual
valor é substituído em `{VERSION}`. Não há schema de evento/API envolvido. `data-model.md` é gerado como
um registro mínimo apontando para essa ausência (nenhuma entidade de domínio nova), para manter o layout
padrão de artefatos da feature — mesma decisão já tomada em `specs/009-issue-20-mmdevice-notification-fix/`.

### Source Code (repository root)

```text
agents/windows-audio-agent/
├── pyproject.toml                  # INALTERADO — version = "0.1.8" já correto e já verificado por
│                                      scripts/release/check-version.sh; não migrar para dynamic
│                                      (research.md Decisão 2 revisada)
├── src/assistant_hub_audio/
│   ├── __init__.py                 # MODIFICADO — __version__ = "0.1.8" (fonte única hardcoded
│   │                                  dentro do código do pacote; alinhado a VERSION da raiz —
│   │                                  FR-002/FR-003)
│   ├── main.py                     # MODIFICADO — remove VERSION="0.1.7" hardcoded; importa
│   │                                  __version__ de assistant_hub_audio para o argparse --version
│   │                                  (FR-001/FR-002); nenhum outro subcomando alterado (FR-007)
│   └── capture.py, devices.py, profiles.py, endpoints.py, hotplug.py, mmdevice.py,
│       mmdevice_notifications.py, process_resolver.py  # inalterados
└── tests/
    └── test_version.py             # NOVO — regressão: __version__ == conteúdo de VERSION (raiz),
                                       lido estaticamente do arquivo (FR-006)

scripts/release/
└── check-version.sh                # MODIFICADO — novo bloco check() para __init__.py:__version__
                                       do audio-agent, mesmo estilo regex do bloco "Agent pyproject"
                                       já existente (FR-005; research.md Decisão 3 revisada)
```

`.github/workflows/ci.yml` **não é alterado**: o step "Version consistency" do job `policy` já chama
`scripts/release/check-version.sh`, então a extensão do script é suficiente para cobrir FR-005.

**Structure Decision**: projeto único existente (`agents/windows-audio-agent`). Nenhum módulo novo de
domínio é criado — a correção é local ao ponto único onde o CLI expõe a versão (`main.py`, `__init__.py`)
e ao script de verificação de versão do monorepo (`check-version.sh`), mantendo a separação já validada
entre módulos Windows-only (`mmdevice*.py`, import lazy) e módulos puros/testáveis em WSL — nenhum deles
é tocado aqui.

## Complexity Tracking

Nenhuma violação da Constitution Check acima requer justificativa; tabela intencionalmente vazia.
