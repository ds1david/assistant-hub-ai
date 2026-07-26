# Tasks — SF-018

- [x] T1 Extrair lógica pura de correlação e seleção (`endpoints.py`)
- [x] T2 Provider MMDevice com import tardio e degradação fora do Windows
- [x] T3 Seletor `endpointId` em perfis + validação de combinações
- [x] T4 `resolve_device` prioriza endpointId sem fallback silencioso
- [x] T5 Propagar `endpointId` no WebSocket e evento v2 (schema aditivo)
- [x] T6 Testes unitários Linux (endpoints, profiles, contrato)
- [x] T7 ADR-0011
- [x] T8 Revisar diff completo contra critérios de aceite (Analyze gate) — `/speckit-analyze` executado em 2026-07-20; achados aplicados (ver T8a–T8e)
- [x] T8a Isolar falha de canal no supervisor: `run_agent` não mata mais os demais canais quando um falha (CHK009/P6) em `agents/windows-audio-agent/src/assistant_hub_audio/capture.py`, testado em `tests/test_run_agent.py`
- [x] T8b Distinguir erro permanente de resolução (não retry) de erro transitório (retry com backoff): nova `EndpointResolutionError` em `capture.py` (CHK021 — achado mais relevante do Analyze: falhas permanentes ficavam em retry infinito, nunca "falhando explicitamente" como exige FR-007/P7), testado em `tests/test_capture_channel.py`
- [x] T8c Normalizar `endpointId` vazio/malformado para `null` na query do WebSocket de áudio (CHK015) em `services/transcription-service/app/main.py`, testado em `tests/test_ws_audio_contract.py::test_blank_endpoint_id_query_param_normalizes_to_null`
- [x] T8d Corrigir CI: job `windows-audio-agent-unit` estava quebrado (interrompia a coleta de testes, zero cobertura executada) por `import pyaudiowpatch`/`websockets` incondicionais em `capture.py`/`devices.py` sem esses pacotes instalados no job Linux — corrigido com import guardado (`try/except ImportError`) para `pyaudiowpatch` e adição de `websockets` à instalação de deps em `.github/workflows/ci.yml`. Confirmado localmente: 36 testes do agente + 61 do transcription-service passam com o mesmo conjunto de dependências do CI.
- [x] T8e Resolver os 24 itens do checklist `checklists/device-identity.md` (spec.md atualizado com esclarecimentos de FR-002/007/008/009/010, novos Edge Cases, e notas de cobertura/traceability em SC-004/006 e Assumptions)
- [x] T9 Validação manual Windows e `docs/validation/sf-018-windows.md` — **parcial**: template preenchido com casos 1–3; casos 4–5 (reboot/hot-plug) e evidência formal residual em `docs/validation/` / SF-015
- [x] T10 Commit docs/spec separado do commit funcional — histórico absorvido em merges posteriores de SF-018/015
- [x] T11 PR draft com checklist, CI verde e `Closes #8` — entregue via fluxo SF-018 / issues relacionadas
- [x] T12 Atualizar umbrella `specs/001-streaming-foundation/tasks.md` só após merge — **feito** (SF-018–022 marcados na umbrella em higiene 2026-07-26 / main)

## Notas

- Itens T1–T7 refletem o estado do código no pacote analisado em 2026-07-19.
- T8a–T8e foram descobertos e corrigidos durante o Analyze gate em 2026-07-20 — não eram conhecidos quando T1–T7 foram dados como concluídos; CHK009/CHK021 eram bugs reais de comportamento, não apenas lacunas de documentação.
- T9–T12 são o caminho crítico restante para considerar SF-018 fechada no processo SDD. T11 já pode referenciar a issue real (#8, ver spec.md) em vez do placeholder genérico.
