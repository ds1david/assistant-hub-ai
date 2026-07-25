package ai.assistanthub.core.provider;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Fala HTTP genérico com qualquer endpoint {@code openai-compatible} (Ollama, OpenAI/GPT, NVIDIA
 * NIM, endpoint custom) via {@code java.net.http.HttpClient} — nenhum SDK de fornecedor é
 * importado (P2, research.md Decisão 1). Usado tanto para {@code type: openai-compatible}
 * quanto — nesta fatia, na ausência de um {@code GeminiAdapter} dedicado (research.md Decisão
 * 5) — não para {@code gemini}, que permanece sem adaptador.
 */
@Component
public class OpenAiCompatibleAdapter implements ProviderAdapterFactory.TypedProviderAdapter {

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final SecretResolver secretResolver;

    public OpenAiCompatibleAdapter(ObjectMapper objectMapper, SecretResolver secretResolver) {
        this.httpClient = HttpClient.newBuilder().build();
        this.objectMapper = objectMapper;
        this.secretResolver = secretResolver;
    }

    @Override
    public ProviderType supportedType() {
        return ProviderType.OPENAI_COMPATIBLE;
    }

    @Override
    public ConnectionTestResult testConnection(Provider provider) {
        try {
            HttpRequest request = requestBuilder(provider, "/models", provider.defaults().timeoutMs())
                    .GET()
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            InvocationErrorType errorType = classify(response.statusCode());
            return errorType == null
                    ? ConnectionTestResult.success(provider.id(), "conexão OK (" + response.statusCode() + ")")
                    : ConnectionTestResult.failure(provider.id(), errorType, "HTTP " + response.statusCode());
        } catch (HttpTimeoutException e) {
            return ConnectionTestResult.failure(provider.id(), InvocationErrorType.TIMEOUT, "timeout ao testar conexão");
        } catch (IOException | InterruptedException e) {
            if (Thread.currentThread().isInterrupted()) {
                Thread.currentThread().interrupt();
            }
            return ConnectionTestResult.failure(provider.id(), InvocationErrorType.GENERIC, describe(e));
        }
    }

    @Override
    public AdapterOutcome invoke(Provider provider, InvocationRequest request) {
        try {
            Map<String, Object> body = Map.of(
                    "model", provider.defaults().model(),
                    "messages", List.of(Map.of("role", "user", "content", request.input())));
            HttpRequest httpRequest = requestBuilder(provider, "/chat/completions", provider.defaults().timeoutMs())
                    .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(body)))
                    .build();
            HttpResponse<String> response = httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString());

            InvocationErrorType errorType = classify(response.statusCode());
            if (errorType != null) {
                return AdapterOutcome.failure(errorType, "HTTP " + response.statusCode());
            }
            return AdapterOutcome.success(extractContent(response.body()));
        } catch (HttpTimeoutException e) {
            return AdapterOutcome.failure(InvocationErrorType.TIMEOUT, "timeout na invocação");
        } catch (IOException | InterruptedException e) {
            if (Thread.currentThread().isInterrupted()) {
                Thread.currentThread().interrupt();
            }
            return AdapterOutcome.failure(InvocationErrorType.GENERIC, describe(e));
        }
    }

    private HttpRequest.Builder requestBuilder(Provider provider, String path, int timeoutMs) {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(trimTrailingSlash(provider.baseUrl()) + path))
                .timeout(Duration.ofMillis(timeoutMs))
                .header("Content-Type", "application/json");
        applyAuthentication(builder, provider.authentication());
        return builder;
    }

    /** Resolve o segredo só aqui, no momento da chamada HTTP — nunca logado nem devolvido (FR-007). */
    private void applyAuthentication(HttpRequest.Builder builder, ProviderAuthentication authentication) {
        if (authentication == null || authentication.mode() == AuthenticationMode.NONE) {
            return;
        }
        Optional<String> secret = secretResolver.resolve(authentication.secretRef());
        if (secret.isEmpty()) {
            return; // segredo não resolvido — o provedor responderá 401/403, classificado normalmente
        }
        switch (authentication.mode()) {
            case BEARER -> builder.header("Authorization", "Bearer " + secret.get());
            case API_KEY -> {
                String headerName = authentication.headerName() != null ? authentication.headerName() : "x-api-key";
                builder.header(headerName, secret.get());
            }
            case NONE -> {
                // sem cabeçalho
            }
        }
    }

    private static InvocationErrorType classify(int statusCode) {
        if (statusCode == 401 || statusCode == 403) {
            return InvocationErrorType.AUTHENTICATION;
        }
        if (statusCode == 404) {
            return InvocationErrorType.MODEL_NOT_FOUND;
        }
        if (statusCode == 429) {
            return InvocationErrorType.RATE_LIMITED;
        }
        if (statusCode >= 200 && statusCode < 300) {
            return null;
        }
        return InvocationErrorType.GENERIC;
    }

    private String extractContent(String responseBody) {
        try {
            JsonNode root = objectMapper.readTree(responseBody);
            JsonNode content = root.path("choices").path(0).path("message").path("content");
            return content.isMissingNode() ? responseBody : content.asText();
        } catch (IOException e) {
            return responseBody;
        }
    }

    private static String trimTrailingSlash(String baseUrl) {
        return baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
    }

    private static String describe(Exception e) {
        return e.getClass().getSimpleName() + (e.getMessage() != null ? ": " + e.getMessage() : "");
    }
}
