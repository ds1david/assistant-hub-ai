# Quickstart: validar a captura de áudio por processo (SF-020)

## Pré-requisitos

- WSL: ambiente Python do agente já configurado (`agents/windows-audio-agent`); não instalar
  `PyAudioWPatch` (Windows-only) — só as libs de teste, como já feito para as correções de SF-019.
- Windows (para a revalidação manual, seção 2): Windows 10 build 20348+ (research.md §1), Python nativo
  com o agente instalado, e um aplicativo que realmente emita áudio (ex.: navegador tocando um vídeo, um
  app de conferência) para servir de alvo.

## 1. Validação automatizada (WSL/Linux, sem hardware)

```bash
cd agents/windows-audio-agent
python3 -m compileall -q src
PYTHONPATH=src python3 -m pytest -q tests -k "process_resolver or capture"
```

**Resultado esperado**: todos os testes passam, cobrindo (FR-001..FR-006, FR-011, FR-012):

- resolução por PID existente/inexistente (FR-005);
- resolução por nome com 0, 1 ou múltiplas correspondências (FR-005);
- restrição de usuário — processo de outro usuário/sistema falha explicitamente (FR-011);
- re-seguimento automático por nome após o PID sair (FR-012), vs. falha permanente por PID (FR-006);
- canal por processo integrado ao mesmo laço de retry/backoff de `capture_channel`, sem regressão nos
  canais por dispositivo já existentes (FR-007).

`process_capture.py` (caminho COM real, `ActivateAudioInterfaceAsync`) não é exercido em WSL — é
Windows-only, import lazy, coberto só pela seção 2 abaixo (P10).

## 2. Validação manual Windows (captura real por processo) — FR-009/SC-001..SC-005

1. Anotar branch e commit (`git rev-parse --short HEAD`), versão do Windows (`winver`/build number —
   confirmar ≥ 20348).
2. Criar um perfil apontando um canal para um processo/aplicativo em execução, por nome:

   ```yaml
   version: 1
   name: process-capture-smoke
   server: ws://127.0.0.1:8001
   channels:
     - id: app_audio
       label: Áudio do aplicativo alvo
       kind: loopback
       device:
         processName: "chrome.exe"
       processing:
         gainDb: 0
   ```

3. Iniciar o aplicativo alvo e garantir que ele está tocando áudio (SC-001).
4. Rodar `assistant-hub-audio run --session smoke-020 --profile <perfil>` em foreground; confirmar que a
   transcrição do canal reflete só o áudio do aplicativo alvo (não o mix do dispositivo de saída
   inteiro).
5. Fechar o aplicativo (ou seu processo) durante a captura; confirmar:
   - seleção por **PID**: o canal reporta erro explícito e para (SC-003, FR-006);
   - seleção por **nome**: abrir novamente o mesmo aplicativo e confirmar que o canal retoma
     automaticamente, sem reiniciar o processo manualmente (SC-003, FR-012).
6. Tentar (separadamente) configurar um canal para um PID de outro usuário/processo de sistema e
   confirmar falha explícita no startup, sem captura (FR-011).
7. Rodar um perfil misturando este canal por processo com um canal por `endpointId` (SF-018) na mesma
   sessão; provocar um unplug no canal por `endpointId` e confirmar que o comportamento de hot-plug
   (SF-019) permanece inalterado e o canal por processo não é afetado (US3).
8. Registrar o resultado em `docs/validation/sf-020-windows.md` (ambiente, commit, passos, resultado
   PASS/FAIL), formato análogo a `docs/validation/sf-018-windows.md`/`sf-019-windows.md`.

## Referências

- Requisitos completos: `spec.md` (FR-001..FR-012, SC-001..SC-005).
- Decisões técnicas (API Windows, `psutil`, decisão de não mudar o contrato): `research.md`.
- Entidades e regras de resolução: `data-model.md`.
- Contrato (sem mudança): `contracts/README.md`.
- Features relacionadas (compatibilidade, não alteradas): `specs/004-sf-018-mmdevice-endpoint-id/`,
  `specs/006-sf-019-hotplug-listener/`.
