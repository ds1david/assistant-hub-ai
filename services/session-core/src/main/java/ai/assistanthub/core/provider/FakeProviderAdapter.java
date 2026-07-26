package ai.assistanthub.core.provider;

import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.function.BooleanSupplier;

/**
 * Adaptador determinístico, sem rede (FR-009/SC-003) — usado em testes automatizados e como
 * fixture de exemplo. O modo é escolhido pelo esquema de {@link Provider#baseUrl()}
 * ({@code fake://<modo>}): {@code success} (padrão), {@code stream}, {@code hang},
 * {@code auth-error}, {@code model-not-found}, {@code rate-limit}, {@code generic-error}.
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

    @Override
    public AdapterOutcome invokeStream(
            Provider provider,
            InvocationRequest request,
            StreamChunkListener listener,
            BooleanSupplier cancelled) {
        FakeMode mode = FakeMode.fromBaseUrl(provider.baseUrl());
        if (mode == FakeMode.HANG) {
            sleepUntilInterrupted();
            if (Thread.currentThread().isInterrupted() || cancelled.getAsBoolean()) {
                return AdapterOutcome.failure(InvocationErrorType.GENERIC, "invocação cancelada");
            }
        }
        InvocationErrorType errorType = mode.errorType();
        if (errorType != null) {
            return AdapterOutcome.failure(errorType, mode.message());
        }

        String full = "[fake:" + provider.id() + "] " + request.input();
        if (mode == FakeMode.STREAM || mode == FakeMode.SUCCESS) {
            // STREAM: chunks por palavra; SUCCESS stream default also splits for multi-chunk tests
            String[] parts = full.split("(?<=\\s)|(?=\\s)");
            if (mode == FakeMode.STREAM || parts.length > 1) {
                StringBuilder acc = new StringBuilder();
                for (String part : parts) {
                    if (cancelled.getAsBoolean() || Thread.currentThread().isInterrupted()) {
                        return AdapterOutcome.failure(InvocationErrorType.GENERIC, "invocação cancelada");
                    }
                    if (part.isEmpty()) {
                        continue;
                    }
                    listener.onChunk(part);
                    acc.append(part);
                    if (mode == FakeMode.STREAM) {
                        sleepBriefly();
                    }
                }
                return AdapterOutcome.success(acc.toString());
            }
        }
        listener.onChunk(full);
        return AdapterOutcome.success(full);
    }

    private static void sleepBriefly() {
        try {
            Thread.sleep(5);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
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
        STREAM(null, null),
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
                case "stream" -> STREAM;
                case "auth-error" -> AUTH_ERROR;
                case "model-not-found" -> MODEL_NOT_FOUND;
                case "rate-limit" -> RATE_LIMITED;
                case "generic-error" -> GENERIC_ERROR;
                default -> SUCCESS;
            };
        }
    }
}
