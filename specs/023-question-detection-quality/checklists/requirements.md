# Specification Quality Checklist: 023 Question Detection Quality

- [x] Problema e superfície de resposta explícitos (shell vs STT)
- [x] User stories com prioridade e cenários Given/When/Then
- [x] FR cobrem lexical, entrevista, multimodal, prosódia, whisper ops, privacidade, testes
- [x] Defaults fechados (sem TBD bloqueante)
- [x] Out of scope listado
- [x] Success criteria mensuráveis / checáveis
- [x] Data model + contract + plan + tasks + quickstart
- [x] Relação com 019/020/021/022 documentada
- [x] Phase A shippable sem Phase C
- [x] P9: sem PCM em log; P10: testes sem WASAPI real na CI

## Gaps conscientes

- Medição WER formal (Phase B é checklist humano, não métrica CI)
- Budget CPU de prosódia a validar na implementação (T020)
- Decisão final v2 vs v2.1 de schema na T013
