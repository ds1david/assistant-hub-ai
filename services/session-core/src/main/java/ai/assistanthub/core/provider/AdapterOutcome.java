package ai.assistanthub.core.provider;

/**
 * Retorno de {@link ProviderAdapter#invoke} — sem os metadados de proveniência/tempo (que
 * {@link InvocationService} adiciona ao montar o {@link InvocationResult} final).
 */
public record AdapterOutcome(boolean success, String output, InvocationErrorType errorType, String message) {

    public static AdapterOutcome success(String output) {
        return new AdapterOutcome(true, output, null, null);
    }

    public static AdapterOutcome failure(InvocationErrorType errorType, String message) {
        return new AdapterOutcome(false, null, errorType, message);
    }
}
