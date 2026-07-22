# Quickstart: Alinhar VERSION reportada pelo CLI do audio-agent (Issue #28)

Validação executável, 100% em WSL/Linux (P10 — sem hardware Windows necessário para esta correção).

## Pré-requisitos

- Checkout do branch `012-issue-28-align-audio-agent-cli-version` com a correção aplicada.
- Python 3.11 ou 3.12 disponível via SDKMAN/ambiente do projeto.
- **Não instalar o pacote completo** (`pip install -e agents/windows-audio-agent`) em WSL/Linux: a
  dependência `PyAudioWPatch` não tem build para Linux (é um fork do PyAudio específico para WASAPI no
  Windows). O mesmo padrão já usado pelo job `windows-audio-agent-unit` do CI se aplica aqui: instalar só
  as dependências não-Windows-only e importar o pacote via `PYTHONPATH`, sem instalação completa.

## Setup

```bash
cd agents/windows-audio-agent
python -m venv .venv-agent   # se ainda não existir
source .venv-agent/bin/activate
pip install pytest PyYAML numpy scipy websockets psutil
```

## Cenário 1 — CLI reporta a mesma versão do arquivo `VERSION` (SC-001)

```bash
cat ../../VERSION
PYTHONPATH=src python -m assistant_hub_audio.main --version
```

**Resultado esperado**: os dois valores são idênticos (ex.: ambos `0.1.8`). Antes da correção, o segundo
comando reportava `0.1.7`.

## Cenário 2 — Fonte única dentro do pacote, sem segunda constante manual (SC-002)

```bash
PYTHONPATH=src python -c "import assistant_hub_audio as m; print(m.__version__)"
grep -n "VERSION" src/assistant_hub_audio/main.py
```

**Resultado esperado**: `assistant_hub_audio.__version__` é igual à saída de `--version` e ao arquivo
`VERSION`; `main.py` não contém mais nenhuma linha declarando `VERSION = "..."` própria (o `grep` não
retorna uma atribuição hardcoded — apenas, no máximo, o uso do valor importado).

## Cenário 3 — Regressão automatizada (FR-006)

```bash
PYTHONPATH=src pytest tests/test_version.py -v
```

**Resultado esperado**: `test_version.py` passa, comprovando que `assistant_hub_audio.__version__` é
igual ao conteúdo do arquivo `VERSION` na raiz do monorepo, sem depender de hardware/GPU nem de
instalação do pacote.

## Cenário 4 — Checagem de CI estendida (FR-005)

`scripts/release/check-version.sh` (já existente, chamado pelo step "Version consistency" do job
`policy` em `.github/workflows/ci.yml`) passa a verificar também `__init__.py:__version__` do audio-agent.
Reproduzir localmente antes de depender do CI remoto:

```bash
cd /home/david/workspace/assistant-hub-ai
chmod +x scripts/release/check-version.sh
./scripts/release/check-version.sh
```

**Resultado esperado**: saída inclui uma linha `OK    windows-audio-agent __init__.py: 0.1.8` (ou
equivalente) além das checagens já existentes (README, transcription-service, agent pyproject); o script
termina com código de saída `0` e a mensagem "Versões alinhadas em `0.1.8`".

## Cenário de regressão negativa (edge case da spec)

```bash
# Simular drift deliberado para confirmar que as duas checagens pegam a divergência
sed -i 's/__version__ = ".*"/__version__ = "0.0.0-drift-test"/' src/assistant_hub_audio/__init__.py

PYTHONPATH=src pytest tests/test_version.py -v   # deve FALHAR
cd /home/david/workspace/assistant-hub-ai && ./scripts/release/check-version.sh   # deve FALHAR (exit != 0)

# Reverter a alteração de teste
git checkout -- agents/windows-audio-agent/src/assistant_hub_audio/__init__.py
```

**Resultado esperado**: os dois comandos falham com a divergência explícita antes da reversão — confirma
que a suíte automatizada (FR-006) e a checagem de CI estendida (FR-005) realmente bloqueiam regressão de
drift, não apenas passam por coincidência.
