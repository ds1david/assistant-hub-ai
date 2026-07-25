package ai.assistanthub.core.provider;

/**
 * Resultado de {@link ProviderAdapter#testConnection(Provider)} (FR-011). {@code message} nunca
 * contém segredo nem header de autenticação (US5).
 */
public record ConnectionTestResult(String providerId, boolean success, InvocationErrorType errorType, String message) {

    public static ConnectionTestResult success(String providerId, String message) {
        return new ConnectionTestResult(providerId, true, null, message);
    }

    public static ConnectionTestResult failure(String providerId, InvocationErrorType errorType, String message) {
        return new ConnectionTestResult(providerId, false, errorType, message);
    }
}
