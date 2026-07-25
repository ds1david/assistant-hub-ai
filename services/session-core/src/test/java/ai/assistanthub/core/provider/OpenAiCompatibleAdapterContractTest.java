package ai.assistanthub.core.provider;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova o request/response de {@link OpenAiCompatibleAdapter} contra um servidor HTTP local
 * (research.md Decisão 8) — determinístico, sem tocar rede externa (P10/SC-003).
 */
class OpenAiCompatibleAdapterContractTest {

    private HttpServer server;

    @AfterEach
    void stopServer() {
        if (server != null) {
            server.stop(0);
        }
    }

    private String startServer(int statusCode, String responseBody, AtomicReference<String> capturedAuthHeader)
            throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            capturedAuthHeader.set(exchange.getRequestHeaders().getFirst("Authorization"));
            byte[] bytes = responseBody.getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(statusCode, bytes.length);
            try (var os = exchange.getResponseBody()) {
                os.write(bytes);
            }
        });
        server.start();
        return "http://127.0.0.1:" + server.getAddress().getPort();
    }

    private Provider provider(String baseUrl, ProviderAuthentication authentication) {
        return new Provider(
                "real-1", "Real", ProviderType.OPENAI_COMPATIBLE, true, baseUrl,
                authentication,
                new ProviderDefaults("gpt-test", null, null, null, 3000),
                Set.of("chat"));
    }

    @Test
    void invokeReturnsSuccessAndExtractsContent() throws IOException {
        String baseUrl = startServer(200, """
                {"choices":[{"message":{"content":"ola de volta"}}]}
                """, new AtomicReference<>());
        OpenAiCompatibleAdapter adapter = new OpenAiCompatibleAdapter(
                new ObjectMapper(), secretRef -> Optional.empty());

        AdapterOutcome outcome = adapter.invoke(
                provider(baseUrl, new ProviderAuthentication(AuthenticationMode.NONE, null, null)),
                new InvocationRequest("session-1", "mic-1", "chat", "ola"));

        assertThat(outcome.success()).isTrue();
        assertThat(outcome.output()).isEqualTo("ola de volta");
    }

    @Test
    void invokeAppliesBearerAuthorizationHeader() throws IOException {
        AtomicReference<String> capturedHeader = new AtomicReference<>();
        String baseUrl = startServer(200, "{\"choices\":[{\"message\":{\"content\":\"ok\"}}]}", capturedHeader);
        OpenAiCompatibleAdapter adapter = new OpenAiCompatibleAdapter(
                new ObjectMapper(), secretRef -> Optional.of("super-secret-token"));

        adapter.invoke(
                provider(baseUrl, new ProviderAuthentication(AuthenticationMode.BEARER, "env:FAKE_VAR", null)),
                new InvocationRequest("session-1", "mic-1", "chat", "ola"));

        assertThat(capturedHeader.get()).isEqualTo("Bearer super-secret-token");
    }

    @Test
    void classifiesAuthenticationFailure() throws IOException {
        String baseUrl = startServer(401, "{}", new AtomicReference<>());
        OpenAiCompatibleAdapter adapter = new OpenAiCompatibleAdapter(
                new ObjectMapper(), secretRef -> Optional.empty());

        AdapterOutcome outcome = adapter.invoke(
                provider(baseUrl, new ProviderAuthentication(AuthenticationMode.NONE, null, null)),
                new InvocationRequest("session-1", "mic-1", "chat", "ola"));

        assertThat(outcome.success()).isFalse();
        assertThat(outcome.errorType()).isEqualTo(InvocationErrorType.AUTHENTICATION);
    }

    @Test
    void testConnectionIncludesPublicErrorDetailAndRedactsApiKeyMaterial() throws IOException {
        String body = """
                {"code":"permission-denied","error":"The API key xai-ABCDEFGHijklmnop is disabled"}
                """;
        String baseUrl = startServer(403, body, new AtomicReference<>());
        OpenAiCompatibleAdapter adapter = new OpenAiCompatibleAdapter(
                new ObjectMapper(), secretRef -> Optional.empty());

        ConnectionTestResult result = adapter.testConnection(
                provider(baseUrl, new ProviderAuthentication(AuthenticationMode.NONE, null, null)));

        assertThat(result.success()).isFalse();
        assertThat(result.errorType()).isEqualTo(InvocationErrorType.AUTHENTICATION);
        assertThat(result.message()).contains("HTTP 403");
        assertThat(result.message()).contains("disabled");
        assertThat(result.message()).contains("xai-[REDACTED]");
        assertThat(result.message()).doesNotContain("ABCDEFGHijklmnop");
    }

    @Test
    void classifiesModelNotFound() throws IOException {
        String baseUrl = startServer(404, "{}", new AtomicReference<>());
        OpenAiCompatibleAdapter adapter = new OpenAiCompatibleAdapter(
                new ObjectMapper(), secretRef -> Optional.empty());

        AdapterOutcome outcome = adapter.invoke(
                provider(baseUrl, new ProviderAuthentication(AuthenticationMode.NONE, null, null)),
                new InvocationRequest("session-1", "mic-1", "chat", "ola"));

        assertThat(outcome.errorType()).isEqualTo(InvocationErrorType.MODEL_NOT_FOUND);
    }

    @Test
    void classifiesRateLimit() throws IOException {
        String baseUrl = startServer(429, "{}", new AtomicReference<>());
        OpenAiCompatibleAdapter adapter = new OpenAiCompatibleAdapter(
                new ObjectMapper(), secretRef -> Optional.empty());

        AdapterOutcome outcome = adapter.invoke(
                provider(baseUrl, new ProviderAuthentication(AuthenticationMode.NONE, null, null)),
                new InvocationRequest("session-1", "mic-1", "chat", "ola"));

        assertThat(outcome.errorType()).isEqualTo(InvocationErrorType.RATE_LIMITED);
    }

    @Test
    void testConnectionSucceedsAgainstModelsEndpoint() throws IOException {
        String baseUrl = startServer(200, "{\"data\":[]}", new AtomicReference<>());
        OpenAiCompatibleAdapter adapter = new OpenAiCompatibleAdapter(
                new ObjectMapper(), secretRef -> Optional.empty());

        ConnectionTestResult result = adapter.testConnection(
                provider(baseUrl, new ProviderAuthentication(AuthenticationMode.NONE, null, null)));

        assertThat(result.success()).isTrue();
    }
}
