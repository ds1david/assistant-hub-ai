package ai.assistanthub.core.provider;

/** Estado do circuit breaker por provedor (026 / FR-001). */
public enum CircuitState {
    CLOSED,
    OPEN,
    HALF_OPEN
}
