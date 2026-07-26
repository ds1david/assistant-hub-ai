package ai.assistanthub.core.provider;

import java.time.Instant;

/**
 * Resultado tipado de {@link InvocationService#invoke}, exposto via
 * {@code POST /api/ai-providers/invoke} (FR-012). {@code providerId} é o provedor que
 * efetivamente respondeu — pode ser um fallback, não necessariamente o {@code primary} da rota.
 * {@code sourceType} é resolvido no servidor a partir do contexto de sessão/canal (issue #40);
 * nulo quando a invocação não está ligada a um canal.
 * Tokens (027) só quando o adaptador os extrai da resposta do provedor.
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
        Instant occurredAt,
        Integer promptTokens,
        Integer completionTokens,
        Integer totalTokens) {

    /** Compat: resultado sem tokens reportados. */
    public static InvocationResult of(
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
        return new InvocationResult(
                providerId, model, capability, sessionId, channelId, sourceType, success, errorType,
                output, message, latencyMs, occurredAt, null, null, null);
    }

    public static InvocationResult of(
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
            Instant occurredAt,
            Integer promptTokens,
            Integer completionTokens,
            Integer totalTokens) {
        return new InvocationResult(
                providerId, model, capability, sessionId, channelId, sourceType, success, errorType,
                output, message, latencyMs, occurredAt, promptTokens, completionTokens, totalTokens);
    }
}
