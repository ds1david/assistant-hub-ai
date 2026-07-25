package ai.assistanthub.core.provider;

import org.springframework.stereotype.Component;

import java.time.Duration;

/**
 * Adaptador determinístico, sem rede (FR-009/SC-003) — usado em testes automatizados e como
 * fixture de exemplo. O modo é escolhido pelo esquema de {@link Provider#baseUrl()}
 * ({@code fake://<modo>}): {@code success} (padrão), {@code hang} (dorme além de qualquer
 * {@code timeoutMs} razoável, para exercitar o isolamento por timeout de
 * {@link InvocationService} de forma real, não auto-reportada), {@code auth-error},
 * {@code model-not-found}, {@code rate-limit}, {@code generic-error}.
 */
@Component
public class FakeProviderAdapter implements ProviderAdapterFactory.TypedProviderAdapter {

    @Override
    public ProviderType supportedType() {
        return ProviderType.FAKE;
    }

    @Override
    public ConnectionTestResult testConnection(Provider provider) {
        FakeMode mode = FakeMode.fromBaseUrl(provider.baseUrl());
        if (mode == FakeMode.HANG) {
            sleepUntilInterrupted();
        }
        InvocationErrorType errorType = mode.errorType();
        return errorType == null
                ? ConnectionTestResult.success(provider.id(), "conexão fake ok")
                : ConnectionTestResult.failure(provider.id(), errorType, mode.message());
    }

    @Override
    public AdapterOutcome invoke(Provider provider, InvocationRequest request) {
        FakeMode mode = FakeMode.fromBaseUrl(provider.baseUrl());
        if (mode == FakeMode.HANG) {
            sleepUntilInterrupted();
        }
        InvocationErrorType errorType = mode.errorType();
        return errorType == null
                ? AdapterOutcome.success("[fake:" + provider.id() + "] " + request.input())
                : AdapterOutcome.failure(errorType, mode.message());
    }

    private static void sleepUntilInterrupted() {
        try {
            Thread.sleep(Duration.ofSeconds(30));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private enum FakeMode {
        SUCCESS(null, null),
        HANG(null, null),
        AUTH_ERROR(InvocationErrorType.AUTHENTICATION, "autenticação simulada falhou"),
        MODEL_NOT_FOUND(InvocationErrorType.MODEL_NOT_FOUND, "modelo simulado inexistente"),
        RATE_LIMITED(InvocationErrorType.RATE_LIMITED, "rate limit simulado"),
        GENERIC_ERROR(InvocationErrorType.GENERIC, "erro genérico simulado");

        private final InvocationErrorType errorType;
        private final String message;

        FakeMode(InvocationErrorType errorType, String message) {
            this.errorType = errorType;
            this.message = message;
        }

        InvocationErrorType errorType() {
            return errorType;
        }

        String message() {
            return message;
        }

        static FakeMode fromBaseUrl(String baseUrl) {
            if (baseUrl == null || !baseUrl.startsWith("fake://")) {
                return SUCCESS;
            }
            String mode = baseUrl.substring("fake://".length());
            return switch (mode) {
                case "hang" -> HANG;
                case "auth-error" -> AUTH_ERROR;
                case "model-not-found" -> MODEL_NOT_FOUND;
                case "rate-limit" -> RATE_LIMITED;
                case "generic-error" -> GENERIC_ERROR;
                default -> SUCCESS;
            };
        }
    }
}
