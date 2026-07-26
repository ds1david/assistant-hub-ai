# Quickstart: 026

```bash
cd services/session-core
mvn -q test -Dtest=ProviderCircuitBreakerTest,InvocationCircuitBreakerTest,InvocationStreamTest,InvocationTimeoutAndFallbackTest
mvn -q test
```

Esperado: suíte verde; testes novos cobrem OPEN skip, half-open, SSE chunks + cancel.
