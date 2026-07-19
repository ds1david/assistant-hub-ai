# Tasks — SF-018

- [x] T1 Extrair lógica pura de correlação e seleção (`endpoints.py`)
- [x] T2 Provider MMDevice com import tardio e degradação fora do Windows
- [x] T3 Seletor `endpointId` em perfis + validação de combinações
- [x] T4 `resolve_device` prioriza endpointId sem fallback silencioso
- [x] T5 Propagar `endpointId` no WebSocket e evento v2 (schema aditivo)
- [x] T6 Testes unitários Linux (endpoints, profiles, contrato)
- [x] T7 ADR-0011
- [ ] T8 Revisar diff completo contra critérios de aceite (Analyze gate)
- [ ] T9 Validação manual Windows e `docs/validation/sf-018-windows.md`
- [ ] T10 Commit docs/spec separado do commit funcional
- [ ] T11 PR draft com checklist, CI verde e `Closes #<issue>`
- [ ] T12 Atualizar umbrella `specs/001-streaming-foundation/tasks.md` só após merge

## Notas

- Itens T1–T7 refletem o estado do código no pacote analisado em 2026-07-19.
- T8–T12 são o caminho crítico para considerar SF-018 fechada no processo SDD.
