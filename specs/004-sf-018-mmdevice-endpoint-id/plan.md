# Plan — SF-018 MMDevice endpoint identity

## Arquitetura

```
Profile YAML (endpointId)
        │
        ▼
profiles.DeviceSelector ──► devices.resolve_device
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              endpointId     index      default/regex
                    │
                    ▼
         endpoints.find_device_for_endpoint
                    │
         correlate_devices(PortAudio, MMDevice)
                    │
         mmdevice.MMDeviceEndpointProvider (Windows)
         NullEndpointProvider (Linux/CI)
                    │
                    ▼
         capture WebSocket query + transcript-event.v2.device.endpointId
```

## Arquivos principais (já existentes no piloto)

| Área | Path |
|------|------|
| Provider Windows | `agents/windows-audio-agent/src/assistant_hub_audio/mmdevice.py` |
| Correlação/seleção | `.../endpoints.py` |
| Resolução | `.../devices.py` |
| Perfis | `.../profiles.py` |
| Captura/WS | `.../capture.py` |
| Schema | `contracts/transcript-event.v2.schema.json` |
| Serviço | `services/transcription-service/app/main.py` |
| ADR | `docs/adr/0011-mmdevice-endpoint-identity.md` |
| Testes | `agents/windows-audio-agent/tests/test_endpoints.py`, `test_profiles.py` |

## Estratégia de testes

1. **Linux/CI:** fakes de provider; correlação; erros de `find_device_for_endpoint`; round-trip de perfil; contrato WS com `endpointId`.
2. **Windows smoke (CI):** import do provider e CLI (sem hardware obrigatório).
3. **Manual Windows:** `docs/validation/sf-018-windows.md` — list/probe/run, reboot, hot-plug, desabilitado, Bluetooth.

## Riscos de implementação

- Não apresentar correlação por nome como garantia absoluta.
- Não degradar para `index` quando `endpointId` falhar.
- Manter mudança de schema estritamente aditiva.

## Ordem de execução neste piloto SDD

1. Formalizar spec/plan/tasks/analyze (retrospectivo).
2. Revisar diff completo vs aceite.
3. Rodar testes Linux.
4. Validação Windows + evidência.
5. Commits separados (docs/spec vs feat) + PR draft.
