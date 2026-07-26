# Tasks: 026 R6 circuit breaker + streaming

- [x] T001 CircuitState + ProviderCircuitBreaker + unit tests
- [x] T002 InvocationErrorType.CIRCUIT_OPEN
- [x] T003 Config thresholds via `@Value` (defaults 5 / 30000ms)
- [x] T004 Wire breaker em InvocationService.invoke (sync)
- [x] T005 Tests InvocationCircuitBreakerTest
- [x] T006 Stream consumer + FakeProviderAdapter `fake://stream`
- [x] T007 OpenAiCompatibleAdapter streaming parse
- [x] T008 POST /invoke/stream SSE + cancel
- [x] T009 GET /circuit-status
- [x] T010 InvocationStreamTest
- [x] T011 Update contracts docs + umbrella 003
- [x] T012 Full mvn test session-core
