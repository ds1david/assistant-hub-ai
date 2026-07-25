package ai.assistanthub.core.provider;

import ai.assistanthub.core.session.SessionRepository;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.slf4j.LoggerFactory;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SC-006 / FR-012: log estruturado ecoa o mesmo sourceType do resultado.
 */
class InvocationSourceTypeLogTest {

    @TempDir
    Path tempDir;

    private ListAppender<ILoggingEvent> appender;
    private Logger invocationLogger;

    @BeforeEach
    void attachAppender() {
        invocationLogger = (Logger) LoggerFactory.getLogger(InvocationService.class);
        appender = new ListAppender<>();
        appender.start();
        invocationLogger.addAppender(appender);
    }

    @AfterEach
    void detachAppender() {
        invocationLogger.detachAppender(appender);
        appender.stop();
    }

    @Test
    void logContainsResolvedSourceTypeMatchingResult() {
        SessionRepository sessions = ProviderTestSupport.newSessionRepository(tempDir);
        String sessionId = ProviderTestSupport.seedChannelOrigin(sessions, "mic-1", "microphone");
        InvocationService service = serviceWith(sessions);

        InvocationResult result = service.invoke(
                "chat-route", new InvocationRequest(sessionId, "mic-1", "chat", "ola"));

        assertThat(result.sourceType()).isEqualTo("microphone");
        assertThat(appender.list).isNotEmpty();
        String message = appender.list.get(appender.list.size() - 1).getFormattedMessage();
        assertThat(message).contains("ai-provider-invocation");
        assertThat(message).contains("sourceType=microphone");
    }

    @Test
    void logDoesNotInventOriginWhenNoChannel() {
        InvocationService service = serviceWith(ProviderTestSupport.newSessionRepository(tempDir));

        InvocationResult result = service.invoke(
                "chat-route", new InvocationRequest("not-uuid", null, "chat", "ola"));

        assertThat(result.sourceType()).isNull();
        String message = appender.list.get(appender.list.size() - 1).getFormattedMessage();
        assertThat(message).contains("sourceType=null");
    }

    private InvocationService serviceWith(SessionRepository sessions) {
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        ProviderProfile profile = new ProviderProfile(
                1,
                List.of(new Provider(
                        "fake-1", "Fake", ProviderType.FAKE, true, "fake://success",
                        new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                        new ProviderDefaults("fake-model", null, null, null, 2000),
                        Set.of("chat"))),
                Map.of("chat-route", new ProviderRoute("fake-1", List.of())));
        ProviderTestSupport.writeRawProfile(tempDir, profile, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(ProviderTestSupport.newStore(tempDir, validator));
        return ProviderTestSupport.newInvocationService(registry, sessions, new FakeProviderAdapter());
    }
}
