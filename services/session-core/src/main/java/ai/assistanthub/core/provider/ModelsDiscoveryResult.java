package ai.assistanthub.core.provider;

import java.util.List;

/**
 * Resultado de descoberta de modelos (027). {@code models} vazia em falha; nunca inclui segredos.
 */
public record ModelsDiscoveryResult(
        String providerId,
        boolean success,
        InvocationErrorType errorType,
        String message,
        List<ModelInfo> models) {

    public static ModelsDiscoveryResult ok(String providerId, List<ModelInfo> models) {
        return new ModelsDiscoveryResult(providerId, true, null, "ok", List.copyOf(models));
    }

    public static ModelsDiscoveryResult failure(
            String providerId, InvocationErrorType errorType, String message) {
        return new ModelsDiscoveryResult(providerId, false, errorType, message, List.of());
    }
}
