package ai.assistanthub.core.provider;

import java.time.Instant;

/**
 * Resultado tipado de {@link InvocationService#invoke}, exposto via
 * {@code POST /api/ai-providers/invoke} (FR-012). {@code providerId} é o provedor que
 * efetivamente respondeu — pode ser um fallback, não necessariamente o {@code primary} da rota.
 */
public record InvocationResult(
        String providerId,
        String model,
        String capability,
        String sessionId,
        String channelId,
        boolean success,
        InvocationErrorType errorType,
        String output,
        String message,
        long latencyMs,
        Instant occurredAt) {
}
