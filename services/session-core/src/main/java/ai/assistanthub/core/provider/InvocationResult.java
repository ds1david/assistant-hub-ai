package ai.assistanthub.core.provider;

import java.time.Instant;

/**
 * Resultado tipado de {@link InvocationService#invoke}, exposto via
 * {@code POST /api/ai-providers/invoke} (FR-012). {@code providerId} é o provedor que
 * efetivamente respondeu — pode ser um fallback, não necessariamente o {@code primary} da rota.
 * {@code sourceType} é resolvido no servidor a partir do contexto de sessão/canal (issue #40);
 * nulo quando a invocação não está ligada a um canal.
 */
public record InvocationResult(
        String providerId,
        String model,
        String capability,
        String sessionId,
        String channelId,
        String sourceType,
        boolean success,
        InvocationErrorType errorType,
        String output,
        String message,
        long latencyMs,
        Instant occurredAt) {
}
