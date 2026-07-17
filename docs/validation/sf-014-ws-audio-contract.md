# Validação SF-014 — contrato WebSocket de áudio

Evidência automatizada do contrato `transcript-event.v2` sem GPU, Docker, WASAPI ou download de modelo.

## Onde

- Testes: `services/transcription-service/tests/test_ws_audio_contract.py`
- Fake injetável: `FakeWhisperModel` em `services/transcription-service/tests/conftest.py`, injetado via `ModelManager(settings, model_factory=...)`
- Schema: `contracts/transcript-event.v2.schema.json`
- CI: job `transcription-python` em `.github/workflows/ci.yml`, matriz Python 3.10 e 3.11

## O que é coberto

- PCM sintético mono, 16 kHz, signed 16-bit gerado em memória;
- canais `system` e `microphone` simultâneos na mesma sessão;
- evento validado campo a campo contra o JSON Schema v2;
- `sessionId`, `channelId`, `sourceType`, `label` e `device` preservados ponta a ponta;
- perda de qualquer metadado obrigatório reprova na validação do schema;
- `sourceType` ausente ou inválido e `deviceIndex` não inteiro fecham a conexão com código 1008;
- evento replicado ao feed `/ws/transcripts`;
- supressão de eco: duplicata do sistema no microfone é suprimida, fala local distinta é entregue.

## Como executar

```bash
PYTHONPATH=services/transcription-service pytest -q services/transcription-service/tests
```
