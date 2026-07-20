# Implementation Plan: SF-015 — Matriz manual de hardware R1

**Branch**: `005-sf-015-hardware-matrix` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-sf-015-hardware-matrix/spec.md`

## Summary

SF-015 é uma feature de **validação manual + documentação**, sem alteração de código de domínio. O trabalho consiste em executar o `windows-audio-agent` (`list-devices`, `probe`, `run`) contra três cenários de hardware real no Windows — conference cam, Bluetooth output + microfone USB, microfone default — e registrar evidência estruturada em `docs/validation/`, confirmando que `endpointId`/`channelId`/`sourceType` (contratos das SF-016/017/018) não regridem. O mesmo ciclo de testes fecha retroativamente o placeholder pendente em `docs/validation/sf-018-windows.md`.

## Technical Context

**Language/Version**: N/A (nenhum código novo; CLI já existe em Python 3.11, `agents/windows-audio-agent`)

**Primary Dependencies**: `assistant-hub-audio` CLI (`list-devices`, `probe`, `run`) já publicado pela SF-018

**Storage**: Arquivos Markdown em `docs/validation/`

**Testing**: Nenhum teste automatizado novo (validação é manual, hardware físico — constituição P10). Suíte existente do agente (`pytest agents/windows-audio-agent/tests`) permanece como regressão de contrato, não é criada aqui.

**Target Platform**: Windows real (Python nativo), conforme ADR-0003/ADR-0005; execução de comandos e commit da evidência a partir do WSL.

**Project Type**: Documentação/validação (não é library/cli/web-service novo)

**Performance Goals**: N/A — feature não introduz requisito de performance; latência percebida é registrada qualitativamente por cenário.

**Constraints**: Execução depende de hardware físico específico (conference cam, dispositivo Bluetooth, microfone USB) estar disponível no momento do teste; sem automação de hardware no CI (FR-007).

**Scale/Scope**: 3 cenários mínimos + fechamento do gap de evidência da SF-018; escopo fechado pela spec, sem expansão para hot-plug automatizado (isso é SF-019) ou métricas de latência formais (isso é SF-016/SF-022).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Aplica? | Avaliação |
|-----------|---------|-----------|
| P1 — Spec antes de código | Sim | `spec.md` e gate G1 precedem esta execução; não há código de domínio a alterar. |
| P2 — Core independente de fornecedores | N/A | Nenhuma integração de provedor externo envolvida. |
| P3 — WSL-first, Windows quando necessário | Sim | Execução dos comandos de captura ocorre no Windows nativo; commit da evidência é feito do WSL. Nenhuma tentativa de capturar WASAPI no WSL. |
| P4 — Contratos versionados | N/A | Nenhum schema é criado ou alterado; a matriz apenas verifica os contratos já publicados nas SF-016/017/018. |
| P5 — Separação por canal e origem | Sim | Critério central da matriz: confirmar `channelId`/`sourceType`/device metadata ponta a ponta em cada cenário. |
| P6 — Isolamento de endpoint de áudio | Sim (verificação) | Cenários de dois dispositivos simultâneos (conference cam, Bluetooth+USB) reexercitam o isolamento por processo já implementado; não há novo código de isolamento aqui. |
| P7 — Identidade de dispositivo | Sim (verificação) | Reexercita `endpointId` > `index` > `default`/`nameRegex` (ADR-0011) e a ausência de fallback silencioso, nos três cenários. |
| P8 — Automação com autorização | Sim | Fluxo `spec-cycle.sh` cuida de branch/commit/PR draft; merge e fechamento de issue continuam manuais. |
| P9 — Privacidade por padrão | Sim | Evidência registra `endpointId`/friendly name/latência percebida; não registra áudio bruto nem segredos (item explícito no template `docs/validation/sf-018-windows.md`, seção "Segurança"). |
| P10 — Qualidade determinística | Sim | Esta é exatamente a exigência de P10: validação manual gera arquivo em `docs/validation/` com ambiente, commit, passos e resultado. |

**Resultado**: Nenhuma violação. Nenhuma linha de Complexity Tracking necessária.

**Re-check pós Fase 1**: `research.md`, `data-model.md` e `quickstart.md` confirmam que nenhuma interface nova foi introduzida e nenhum código de domínio é tocado — apenas arquivos em `docs/validation/`. Gate mantém-se aprovado sem alterações.

## Project Structure

### Documentation (this feature)

```text
specs/005-sf-015-hardware-matrix/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

Não há `contracts/`: a feature não expõe nem altera nenhuma interface (API, schema, CLI). Ela consome a CLI e os contratos de evento já publicados pela SF-018 e verifica que continuam válidos.

### Source Code (repository root)

Nenhum diretório de código é criado ou modificado por esta feature. Os únicos artefatos de repositório afetados são de documentação:

```text
docs/validation/
├── sf-018-windows.md          # preenchido retroativamente (Cenário 3 reaproveita os casos)
├── sf-015-conference-cam.md   # novo — Cenário 1
├── sf-015-bluetooth-usb.md    # novo — Cenário 2
└── sf-015-default-mic.md      # novo — Cenário 3 (espelha e referencia sf-018-windows.md)
```

**Structure Decision**: Um arquivo de evidência por cenário (em vez de expandir `r1-audio-validation.md` monoliticamente) para manter cada cenário independentemente revisável e para não misturar o formato específico da SF-018 (que já tem seu próprio template com casos 1–7) com os dois cenários novos. `r1-audio-validation.md` permanece como estava (pré-existente, fora do escopo desta feature) — os novos arquivos seguem o mesmo padrão de seções (Ambiente, Dispositivos, Casos, Resultado) já estabelecido em `sf-018-windows.md`.

## Complexity Tracking

Sem violações de constituição a justificar.
