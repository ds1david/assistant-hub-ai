package ai.assistanthub.core.provider;

/** Visão observável do breaker de um provedor (US3 / FR-001). */
public record ProviderCircuitSnapshot(
        String providerId,
        CircuitState state,
        int consecutiveFailures,
        Long openUntilEpochMs) {
}
