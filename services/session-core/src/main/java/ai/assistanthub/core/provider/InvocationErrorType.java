package ai.assistanthub.core.provider;

/**
 * Taxonomia de erro de invocação/teste de conexão (FR-006, FR-011) — ver research.md Decisão 6
 * para o mapeamento a partir do status HTTP retornado pelo provedor.
 */
public enum InvocationErrorType {
    AUTHENTICATION,
    MODEL_NOT_FOUND,
    TIMEOUT,
    RATE_LIMITED,
    GENERIC,
    /** Capacidade solicitada ausente de {@code provider.capabilities()} (FR-010) — rejeitado antes de chamar o adaptador. */
    CAPABILITY_MISMATCH,
    /**
     * Provedor não chamado porque o circuit breaker está OPEN (026). Não conta como falha
     * adicional no breaker.
     */
    CIRCUIT_OPEN
}
