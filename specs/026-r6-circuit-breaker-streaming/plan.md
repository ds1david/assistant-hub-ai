# Implementation Plan: 026 R6 circuit breaker + streaming

**Branch**: `feature/026-r6-circuit-breaker-streaming` | **Date**: 2026-07-26 | **Spec**: [spec.md](./spec.md)

## Summary

Adicionar circuit breaker in-memory por `providerId` no `InvocationService` e endpoint SSE de invoke com cancel, suportado por `FakeProviderAdapter` e `OpenAiCompatibleAdapter`.

## Technical Context

**Language**: Java 21, Spring Boot 3 (session-core)  
**Deps**: existentes (`HttpClient`, Spring Web MVC `SseEmitter`)  
**Testing**: JUnit 5, fake adapters, sem rede externa  
**Constraints**: P2/P9/P10; não quebrar 015/017

## Constitution Check

PASS para P1–P10; breaker in-process OK (single instance Developer/desktop).

## Structure

```text
services/session-core/src/main/java/.../provider/
  ProviderCircuitBreaker.java   # NEW
  CircuitState.java             # NEW
  StreamChunkConsumer.java      # NEW functional interface
  InvocationService.java        # wire breaker + stream
  OpenAiCompatibleAdapter.java  # stream invoke
  FakeProviderAdapter.java      # fake://stream
  AiProviderController.java     # SSE + circuit-status
  InvocationErrorType.java      # CIRCUIT_OPEN
  AiProviderHubProperties.java  # thresholds
```

## Phases

1. Breaker + tests  
2. Wire sync invoke  
3. Stream API + fake  
4. OpenAI stream  
5. Docs/umbrella  
