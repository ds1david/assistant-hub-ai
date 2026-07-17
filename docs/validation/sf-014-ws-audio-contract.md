# Validação SF-014 — contrato WebSocket de áudio

Evidência automatizada do contrato `transcript-event.v2` sem GPU, Docker, WASAPI ou download de modelo.

## Arquitetura de injeção

- `app/engine.py` define `TranscriptionEngine`, a fronteira entre o serviço e o backend de STT (`loaded`, `load()`, `transcribe(audio, language) -> EngineResult`);
- `app/transcriber.py` mantém o Faster-Whisper como implementação padrão via `WhisperEngine` (lazy load pelo `ModelManager`);
- `app/main.py` expõe `create_app(settings=None, engine=None)`; sem argumentos monta o serviço real (`app.main:app` continua válido para uvicorn/Docker);
- os testes injetam `FakeTranscriptionEngine` (definido em `tests/conftest.py`, exclusivo de testes) com `create_app(settings=..., engine=...)` — injeção de dependência explícita, sem monkeypatch.

## Onde

- Testes: `services/transcription-service/tests/test_ws_audio_contract.py`
- Fake: `FakeTranscriptionEngine` em `services/transcription-service/tests/conftest.py`
- Schema: `contracts/transcript-event.v2.schema.json`
- CI: job `transcription-python` em `.github/workflows/ci.yml`, matriz Python 3.10 e 3.11

## O que é coberto

- PCM sintético mono, 16 kHz, signed 16-bit gerado em memória;
- contrato campo a campo para os canais `microphone` e `system`;
- canais `system` e `microphone` simultâneos na mesma sessão, cada um com seus metadados;
- evento validado contra o JSON Schema v2 em todos os cenários;
- `sessionId`, `channelId`, `sourceType`, `label` e `device` preservados ponta a ponta;
- perda de qualquer metadado obrigatório reprova na validação do schema;
- `sourceType` ausente ou inválido e `deviceIndex` não inteiro fecham a conexão com código 1008;
- evento replicado ao feed `/ws/transcripts`;
- supressão de eco: duplicata do sistema no microfone é suprimida, fala local distinta é entregue.

## Como executar

```bash
PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests
```
