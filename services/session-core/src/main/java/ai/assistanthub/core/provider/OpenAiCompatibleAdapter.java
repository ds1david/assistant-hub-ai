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
import java.util.ArrayList;
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
                    : ConnectionTestResult.failure(
                            provider.id(), errorType, httpFailureMessage(response.statusCode(), response.body()));
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
    public ModelsDiscoveryResult listModels(Provider provider) {
        try {
            HttpRequest request = requestBuilder(provider, "/models", provider.defaults().timeoutMs())
                    .GET()
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            InvocationErrorType errorType = classify(response.statusCode());
            if (errorType != null) {
                return ModelsDiscoveryResult.failure(
                        provider.id(), errorType, httpFailureMessage(response.statusCode(), response.body()));
            }
            return ModelsDiscoveryResult.ok(provider.id(), parseModels(response.body()));
        } catch (HttpTimeoutException e) {
            return ModelsDiscoveryResult.failure(provider.id(), InvocationErrorType.TIMEOUT, "timeout ao listar modelos");
        } catch (IOException | InterruptedException e) {
            if (Thread.currentThread().isInterrupted()) {
                Thread.currentThread().interrupt();
            }
            return ModelsDiscoveryResult.failure(provider.id(), InvocationErrorType.GENERIC, describe(e));
        }
    }

    @Override
    public AdapterOutcome invoke(Provider provider, InvocationRequest request) {
        try {
            Map<String, Object> body = Map.of(
                    "model", provider.defaults().model(),
                    "messages", List.of(Map.of("role", "user", "content", request.input())),
                    "stream", false);
            HttpRequest httpRequest = requestBuilder(provider, "/chat/completions", provider.defaults().timeoutMs())
                    .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(body)))
                    .build();
            HttpResponse<String> response = httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString());

            InvocationErrorType errorType = classify(response.statusCode());
            if (errorType != null) {
                return AdapterOutcome.failure(errorType, httpFailureMessage(response.statusCode(), response.body()));
            }
            String content = extractContent(response.body());
            Integer[] usage = extractUsage(response.body());
            if (usage != null) {
                return AdapterOutcome.success(content, usage[0], usage[1], usage[2]);
            }
            return AdapterOutcome.success(content);
        } catch (HttpTimeoutException e) {
            return AdapterOutcome.failure(InvocationErrorType.TIMEOUT, "timeout na invocação");
        } catch (IOException | InterruptedException e) {
            if (Thread.currentThread().isInterrupted()) {
                Thread.currentThread().interrupt();
            }
            return AdapterOutcome.failure(InvocationErrorType.GENERIC, describe(e));
        }
    }

    @Override
    public AdapterOutcome invokeStream(
            Provider provider,
            InvocationRequest request,
            StreamChunkListener listener,
            java.util.function.BooleanSupplier cancelled) {
        try {
            Map<String, Object> body = Map.of(
                    "model", provider.defaults().model(),
                    "messages", List.of(Map.of("role", "user", "content", request.input())),
                    "stream", true);
            HttpRequest httpRequest = requestBuilder(provider, "/chat/completions", provider.defaults().timeoutMs())
                    .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(body)))
                    .header("Accept", "text/event-stream")
                    .build();
            HttpResponse<java.io.InputStream> response =
                    httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofInputStream());

            InvocationErrorType errorType = classify(response.statusCode());
            if (errorType != null) {
                String bodyText = new String(response.body().readAllBytes(), java.nio.charset.StandardCharsets.UTF_8);
                return AdapterOutcome.failure(errorType, httpFailureMessage(response.statusCode(), bodyText));
            }

            StringBuilder assembled = new StringBuilder();
            try (java.io.BufferedReader reader = new java.io.BufferedReader(
                    new java.io.InputStreamReader(response.body(), java.nio.charset.StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    if (cancelled.getAsBoolean() || Thread.currentThread().isInterrupted()) {
                        return AdapterOutcome.failure(InvocationErrorType.GENERIC, "invocação cancelada");
                    }
                    if (!line.startsWith("data:")) {
                        continue;
                    }
                    String data = line.substring(5).trim();
                    if (data.isEmpty() || "[DONE]".equals(data)) {
                        if ("[DONE]".equals(data)) {
                            break;
                        }
                        continue;
                    }
                    String delta = extractDeltaContent(data);
                    if (delta != null && !delta.isEmpty()) {
                        listener.onChunk(delta);
                        assembled.append(delta);
                    }
                }
            }
            return AdapterOutcome.success(assembled.toString());
        } catch (HttpTimeoutException e) {
            return AdapterOutcome.failure(InvocationErrorType.TIMEOUT, "timeout na invocação stream");
        } catch (IOException | InterruptedException e) {
            if (Thread.currentThread().isInterrupted()) {
                Thread.currentThread().interrupt();
            }
            if (cancelled.getAsBoolean()) {
                return AdapterOutcome.failure(InvocationErrorType.GENERIC, "invocação cancelada");
            }
            return AdapterOutcome.failure(InvocationErrorType.GENERIC, describe(e));
        }
    }

    private String extractDeltaContent(String jsonLine) {
        try {
            JsonNode root = objectMapper.readTree(jsonLine);
            JsonNode content = root.path("choices").path(0).path("delta").path("content");
            if (content.isMissingNode() || content.isNull()) {
                return null;
            }
            return content.asText();
        } catch (IOException e) {
            return null;
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

    /** @return {@code [prompt, completion, total]} ou null se usage ausente (não inventa valores). */
    private Integer[] extractUsage(String responseBody) {
        try {
            JsonNode usage = objectMapper.readTree(responseBody).path("usage");
            if (usage.isMissingNode() || usage.isNull()) {
                return null;
            }
            Integer prompt = intOrNull(usage.get("prompt_tokens"));
            Integer completion = intOrNull(usage.get("completion_tokens"));
            Integer total = intOrNull(usage.get("total_tokens"));
            if (prompt == null && completion == null && total == null) {
                return null;
            }
            if (total == null && prompt != null && completion != null) {
                total = prompt + completion;
            }
            return new Integer[] {prompt, completion, total};
        } catch (IOException e) {
            return null;
        }
    }

    private static Integer intOrNull(JsonNode node) {
        if (node == null || node.isNull() || !node.isNumber()) {
            return null;
        }
        return node.asInt();
    }

    private List<ModelInfo> parseModels(String responseBody) {
        List<ModelInfo> models = new ArrayList<>();
        try {
            JsonNode data = objectMapper.readTree(responseBody).path("data");
            if (!data.isArray()) {
                return models;
            }
            for (JsonNode item : data) {
                JsonNode id = item.get("id");
                if (id == null || !id.isTextual() || id.asText().isBlank()) {
                    continue;
                }
                String ownedBy = item.path("owned_by").isTextual() ? item.path("owned_by").asText() : null;
                models.add(new ModelInfo(id.asText(), ownedBy));
            }
        } catch (IOException ignored) {
            // lista vazia
        }
        return models;
    }

    /**
     * Monta mensagem de falha HTTP segura para UI/log: status + trecho público do corpo
     * ({@code error}/{@code message}/{@code code}), sem repassar chaves em claro.
     */
    private String httpFailureMessage(int statusCode, String responseBody) {
        String detail = extractPublicErrorDetail(responseBody);
        return detail == null || detail.isBlank()
                ? "HTTP " + statusCode
                : "HTTP " + statusCode + ": " + detail;
    }

    private String extractPublicErrorDetail(String responseBody) {
        if (responseBody == null || responseBody.isBlank()) {
            return null;
        }
        try {
            JsonNode root = objectMapper.readTree(responseBody);
            for (String field : List.of("error", "message", "detail")) {
                JsonNode node = root.get(field);
                if (node == null || node.isNull()) {
                    continue;
                }
                if (node.isTextual()) {
                    return redactSecrets(node.asText());
                }
                if (node.isObject()) {
                    JsonNode nestedMessage = node.get("message");
                    if (nestedMessage != null && nestedMessage.isTextual()) {
                        return redactSecrets(nestedMessage.asText());
                    }
                }
            }
            JsonNode code = root.get("code");
            if (code != null && code.isTextual()) {
                return redactSecrets(code.asText());
            }
        } catch (IOException ignored) {
            // corpo não-JSON — ignora
        }
        return null;
    }

    /** Remove padrões típicos de API key para não ecoar credenciais em message (US5). */
    private static String redactSecrets(String text) {
        if (text == null) {
            return null;
        }
        String redacted = text
                .replaceAll("(?i)\\b(xai|sk|sk-proj|nvapi)-[A-Za-z0-9_\\-]{8,}", "$1-[REDACTED]")
                .replaceAll("(?i)Bearer\\s+[A-Za-z0-9._\\-]+", "Bearer [REDACTED]");
        return redacted.length() > 280 ? redacted.substring(0, 277) + "..." : redacted;
    }

    private static String trimTrailingSlash(String baseUrl) {
        return baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
    }

    private static String describe(Exception e) {
        return e.getClass().getSimpleName() + (e.getMessage() != null ? ": " + e.getMessage() : "");
    }
}
