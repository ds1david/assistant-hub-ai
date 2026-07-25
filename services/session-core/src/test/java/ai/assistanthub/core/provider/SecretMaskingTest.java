package ai.assistanthub.core.provider;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova US5 (FR-007/FR-014/SC-004): o valor resolvido de um segredo nunca aparece em log,
 * resposta de {@link AiProviderController} ou no arquivo de perfil persistido — só
 * {@code secretRef} (não sensível) e a prévia mascarada de {@link SecretPreview}.
 */
class SecretMaskingTest {

    private static final String RAW_SECRET = "super-secret-value-should-never-leak-xyz789";

    @TempDir
    Path tempDir;

    private HttpServer server;
    private ListAppender<ILoggingEvent> logAppender;

    @BeforeEach
    void attachLogAppender() {
        logAppender = new ListAppender<>();
        logAppender.start();
        ((Logger) LoggerFactory.getLogger(InvocationService.class)).addAppender(logAppender);
    }

    @AfterEach
    void tearDown() {
        ((Logger) LoggerFactory.getLogger(InvocationService.class)).detachAppender(logAppender);
        if (server != null) {
            server.stop(0);
        }
    }

    private String startServer() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            byte[] bytes = "{\"choices\":[{\"message\":{\"content\":\"ok\"}}]}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, bytes.length);
            try (var os = exchange.getResponseBody()) {
                os.write(bytes);
            }
        });
        server.start();
        return "http://127.0.0.1:" + server.getAddress().getPort();
    }

    private Provider providerWithSecret(String baseUrl) {
        return new Provider(
                "real-1", "Real", ProviderType.OPENAI_COMPATIBLE, true, baseUrl,
                new ProviderAuthentication(AuthenticationMode.BEARER, "env:FAKE_VAR", null),
                new ProviderDefaults("gpt-test", null, null, null, 3000),
                Set.of("chat"));
    }

    @Test
    void resolvedSecretNeverAppearsInLogApiResponseOrPersistedFile() throws IOException {
        String baseUrl = startServer();
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        ProviderProfileStore store = ProviderTestSupport.newStore(tempDir, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(store);
        Provider provider = providerWithSecret(baseUrl);
        registry.save(provider);
        registry.reload();
        // registra a rota separadamente pois save() acima já persistiu o provider sozinho
        ProviderProfile withRoute = new ProviderProfile(
                registry.profile().version(), registry.profile().providers(),
                Map.of("chat-route", new ProviderRoute("real-1", List.of())));
        store.save(withRoute);
        registry.reload();

        OpenAiCompatibleAdapter adapter =
                new OpenAiCompatibleAdapter(new ObjectMapper(), secretRef -> Optional.of(RAW_SECRET));
        InvocationService invocationService = ProviderTestSupport.newInvocationService(registry, adapter);
        AiProviderController controller =
                new AiProviderController(registry, invocationService, secretRef -> Optional.of(RAW_SECRET));

        InvocationResult result = invocationService.invoke(
                "chat-route", new InvocationRequest("s1", null, "chat", "ola"));
        assertThat(result.success()).isTrue();

        // 1) nunca no log estruturado da invocação (FR-008/FR-007)
        String allLogMessages = logAppender.list.stream().map(ILoggingEvent::getFormattedMessage).reduce("", String::concat);
        assertThat(allLogMessages).doesNotContain(RAW_SECRET);

        // 2) nunca em nenhuma resposta de API — list/create/secret-preview/invoke
        assertThat(controller.list().toString()).doesNotContain(RAW_SECRET);
        assertThat(controller.secretPreview("real-1").maskedValue()).doesNotContain(RAW_SECRET);
        assertThat(result.toString()).doesNotContain(RAW_SECRET);

        // 3) nunca no arquivo YAML persistido (export = o próprio arquivo, só com secretRef)
        String fileContents = Files.readString(tempDir.resolve("ai-providers-test.yaml"));
        assertThat(fileContents).doesNotContain(RAW_SECRET).contains("env:FAKE_VAR");
    }

    @Test
    void authenticationFailureMessageNeverLeaksHeaderContent() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            byte[] bytes = "{}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(401, bytes.length);
            try (var os = exchange.getResponseBody()) {
                os.write(bytes);
            }
        });
        server.start();
        String baseUrl = "http://127.0.0.1:" + server.getAddress().getPort();

        OpenAiCompatibleAdapter adapter =
                new OpenAiCompatibleAdapter(new ObjectMapper(), secretRef -> Optional.of(RAW_SECRET));

        ConnectionTestResult result = adapter.testConnection(providerWithSecret(baseUrl));

        assertThat(result.success()).isFalse();
        assertThat(result.errorType()).isEqualTo(InvocationErrorType.AUTHENTICATION);
        assertThat(result.message()).doesNotContain(RAW_SECRET).doesNotContain("Bearer");
    }
}
