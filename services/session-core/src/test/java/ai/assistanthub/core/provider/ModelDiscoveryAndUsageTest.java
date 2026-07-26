package ai.assistanthub.core.provider;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Executors;

import static org.assertj.core.api.Assertions.assertThat;

/** 027: list models + token usage from provider response. */
class ModelDiscoveryAndUsageTest {

    @TempDir
    Path tempDir;

    @Test
    void fakeListModelsReturnsDeterministicIds() {
        Provider provider = fakeProvider("fake-1", "fake://success");
        ProviderProfile profile = profile(provider);
        InvocationService service = service(profile);

        ModelsDiscoveryResult result = service.listModels("fake-1");

        assertThat(result.success()).isTrue();
        assertThat(result.models()).isNotEmpty();
        assertThat(result.models().stream().map(ModelInfo::id)).contains("fake-model");
    }

    @Test
    void fakeInvokeReportsTokenUsage() {
        Provider provider = fakeProvider("fake-1", "fake://success");
        InvocationService service = service(profile(provider));

        InvocationResult result = service.invoke(
                "chat-route", new InvocationRequest("s1", null, "chat", "hello"));

        assertThat(result.success()).isTrue();
        assertThat(result.promptTokens()).isNotNull().isPositive();
        assertThat(result.completionTokens()).isNotNull().isPositive();
        assertThat(result.totalTokens()).isEqualTo(result.promptTokens() + result.completionTokens());
    }

    @Test
    void openAiCompatibleParsesModelsAndUsage() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/v1/models", exchange -> {
            byte[] body = """
                    {"data":[{"id":"gpt-test","owned_by":"org"},{"id":"other","owned_by":"org"}]}
                    """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, body.length);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(body);
            }
        });
        server.createContext("/v1/chat/completions", exchange -> {
            byte[] body = """
                    {"choices":[{"message":{"content":"oi"}}],
                     "usage":{"prompt_tokens":11,"completion_tokens":2,"total_tokens":13}}
                    """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, body.length);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(body);
            }
        });
        server.setExecutor(Executors.newCachedThreadPool());
        server.start();
        try {
            int port = server.getAddress().getPort();
            String base = "http://127.0.0.1:" + port + "/v1";
            Provider provider = new Provider(
                    "real-1", "Real", ProviderType.OPENAI_COMPATIBLE, true, base,
                    new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                    new ProviderDefaults("gpt-test", null, null, null, 5_000),
                    Set.of("chat"));
            InvocationService service = service(profile(provider), new OpenAiCompatibleAdapter(
                    ProviderTestSupport.newObjectMapper(), new EnvSecretResolver()));

            ModelsDiscoveryResult models = service.listModels("real-1");
            assertThat(models.success()).isTrue();
            assertThat(models.models()).extracting(ModelInfo::id).containsExactly("gpt-test", "other");

            InvocationResult inv = service.invoke(
                    "chat-route", new InvocationRequest("s1", null, "chat", "ping"));
            assertThat(inv.success()).isTrue();
            assertThat(inv.output()).isEqualTo("oi");
            assertThat(inv.promptTokens()).isEqualTo(11);
            assertThat(inv.completionTokens()).isEqualTo(2);
            assertThat(inv.totalTokens()).isEqualTo(13);
        } finally {
            server.stop(0);
        }
    }

    private Provider fakeProvider(String id, String baseUrl) {
        return new Provider(
                id, "Fake", ProviderType.FAKE, true, baseUrl,
                new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                new ProviderDefaults("fake-model", null, null, null, 500),
                Set.of("chat"));
    }

    private ProviderProfile profile(Provider provider) {
        return new ProviderProfile(
                1, List.of(provider), Map.of("chat-route", new ProviderRoute(provider.id(), List.of())));
    }

    private InvocationService service(ProviderProfile profile) {
        return service(profile, new FakeProviderAdapter());
    }

    private InvocationService service(ProviderProfile profile, ProviderAdapterFactory.TypedProviderAdapter adapter) {
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        ProviderTestSupport.writeRawProfile(tempDir, profile, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(ProviderTestSupport.newStore(tempDir, validator));
        return ProviderTestSupport.newInvocationService(registry, adapter);
    }
}
