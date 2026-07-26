package ai.assistanthub.core.provider;

/**
 * Retorno de {@link ProviderAdapter#invoke} — sem os metadados de proveniência/tempo (que
 * {@link InvocationService} adiciona ao montar o {@link InvocationResult} final).
 * Tokens opcionais (027) só quando o provedor os reporta — nunca inventados.
 */
public record AdapterOutcome(
        boolean success,
        String output,
        InvocationErrorType errorType,
        String message,
        Integer promptTokens,
        Integer completionTokens,
        Integer totalTokens) {

    public static AdapterOutcome success(String output) {
        return new AdapterOutcome(true, output, null, null, null, null, null);
    }

    public static AdapterOutcome success(String output, Integer promptTokens, Integer completionTokens, Integer totalTokens) {
        return new AdapterOutcome(true, output, null, null, promptTokens, completionTokens, totalTokens);
    }

    public static AdapterOutcome failure(InvocationErrorType errorType, String message) {
        return new AdapterOutcome(false, null, errorType, message, null, null, null);
    }
}
