package ai.assistanthub.core.provider;

import ai.assistanthub.core.session.SessionRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Contrato issue #40: sourceType no resultado (sucesso/falha, N/A, rejeições, multi-canal).
 */
class InvocationSourceTypeContractTest {

    @TempDir
    Path tempDir;

    private ProviderProfileValidator validator;
    private SessionRepository sessionRepository;
    private InvocationService invocationService;

    @BeforeEach
    void setUp() {
        validator = ProviderTestSupport.newValidator();
        sessionRepository = ProviderTestSupport.newSessionRepository(tempDir);
        ProviderProfile profile = new ProviderProfile(
                1,
                List.of(fake("fake-1", "fake://success")),
                Map.of("chat-route", new ProviderRoute("fake-1", List.of())));
        ProviderTestSupport.writeRawProfile(tempDir, profile, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(ProviderTestSupport.newStore(tempDir, validator));
        invocationService = ProviderTestSupport.newInvocationService(registry, sessionRepository, new FakeProviderAdapter());
    }

    private static Provider fake(String id, String baseUrl) {
        return new Provider(
                id, "Fake", ProviderType.FAKE, true, baseUrl,
                new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                new ProviderDefaults("fake-model", null, null, null, 2000),
                java.util.Set.of("chat"));
    }

    @Test
    void successWithMicrophoneChannelPreservesSourceType() {
        String sessionId = ProviderTestSupport.seedChannelOrigin(sessionRepository, "mic-1", "microphone");

        InvocationResult result = invocationService.invoke(
                "chat-route", new InvocationRequest(sessionId, "mic-1", "chat", "ola"));

        assertThat(result.success()).isTrue();
        assertThat(result.sourceType()).isEqualTo("microphone");
        assertThat(result.channelId()).isEqualTo("mic-1");
    }

    @Test
    void successWithSystemChannelPreservesSourceType() {
        String sessionId = ProviderTestSupport.seedChannelOrigin(sessionRepository, "sys-1", "system");

        InvocationResult result = invocationService.invoke(
                "chat-route", new InvocationRequest(sessionId, "sys-1", "chat", "ola"));

        assertThat(result.success()).isTrue();
        assertThat(result.sourceType()).isEqualTo("system");
    }

    @Test
    void providerFailureStillKeepsResolvedSourceType() {
        ProviderProfile failProfile = new ProviderProfile(
                1,
                List.of(fake("fake-fail", "fake://generic-error")),
                Map.of("chat-route", new ProviderRoute("fake-fail", List.of())));
        ProviderTestSupport.writeRawProfile(tempDir, failProfile, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(ProviderTestSupport.newStore(tempDir, validator));
        InvocationService failing = ProviderTestSupport.newInvocationService(
                registry, sessionRepository, new FakeProviderAdapter());
        String sessionId = ProviderTestSupport.seedChannelOrigin(sessionRepository, "mic-1", "microphone");

        InvocationResult result = failing.invoke(
                "chat-route", new InvocationRequest(sessionId, "mic-1", "chat", "ola"));

        assertThat(result.success()).isFalse();
        assertThat(result.sourceType()).isEqualTo("microphone");
    }

    @Test
    void noChannelYieldsNullSourceType() {
        InvocationResult result = invocationService.invoke(
                "chat-route", new InvocationRequest("session-not-uuid", null, "chat", "ola"));

        assertThat(result.success()).isTrue();
        assertThat(result.sourceType()).isNull();
    }

    @Test
    void channelWithoutEventsThrowsBeforeProvider() {
        ai.assistanthub.core.session.ConversationSession session =
                ai.assistanthub.core.session.ConversationSession.create("sem-eventos", "test", Map.of());
        sessionRepository.save(session);

        assertThatThrownBy(() -> invocationService.invoke(
                "chat-route", new InvocationRequest(session.id().toString(), "mic-1", "chat", "ola")))
                .isInstanceOf(ChannelOriginUnresolvedException.class);
    }

    @Test
    void invalidUuidWithChannelThrows() {
        assertThatThrownBy(() -> invocationService.invoke(
                "chat-route", new InvocationRequest("not-a-uuid", "mic-1", "chat", "ola")))
                .isInstanceOf(ChannelOriginUnresolvedException.class)
                .hasMessageContaining("UUID");
    }

    @Test
    void multiChannelSequentialIsolation() {
        ai.assistanthub.core.session.ConversationSession session =
                ai.assistanthub.core.session.ConversationSession.create("multi", "test", Map.of());
        sessionRepository.save(session);
        append(session.id(), "mic-1", "microphone");
        append(session.id(), "sys-1", "system");
        String sessionId = session.id().toString();

        InvocationResult mic = invocationService.invoke(
                "chat-route", new InvocationRequest(sessionId, "mic-1", "chat", "a"));
        InvocationResult sys = invocationService.invoke(
                "chat-route", new InvocationRequest(sessionId, "sys-1", "chat", "b"));

        assertThat(mic.sourceType()).isEqualTo("microphone");
        assertThat(sys.sourceType()).isEqualTo("system");
    }

    @Test
    void multiChannelConcurrentIsolation() throws Exception {
        ai.assistanthub.core.session.ConversationSession session =
                ai.assistanthub.core.session.ConversationSession.create("concurrent", "test", Map.of());
        sessionRepository.save(session);
        append(session.id(), "mic-1", "microphone");
        append(session.id(), "sys-1", "system");
        String sessionId = session.id().toString();

        CompletableFuture<InvocationResult> micFuture = CompletableFuture.supplyAsync(() ->
                invocationService.invoke("chat-route", new InvocationRequest(sessionId, "mic-1", "chat", "a")));
        CompletableFuture<InvocationResult> sysFuture = CompletableFuture.supplyAsync(() ->
                invocationService.invoke("chat-route", new InvocationRequest(sessionId, "sys-1", "chat", "b")));

        InvocationResult mic = micFuture.get(5, TimeUnit.SECONDS);
        InvocationResult sys = sysFuture.get(5, TimeUnit.SECONDS);

        assertThat(mic.sourceType()).isEqualTo("microphone");
        assertThat(sys.sourceType()).isEqualTo("system");
    }

    private void append(java.util.UUID sessionId, String channelId, String sourceType) {
        Map<String, String> correlation = Map.of(
                "channelId", channelId, "sourceType", sourceType, "label", channelId);
        ai.assistanthub.sdk.HubEvent base = ai.assistanthub.sdk.HubEvent.now(
                sessionId, "transcript.final.v2", "transcription-service", Map.of("text", "x"));
        sessionRepository.append(new ai.assistanthub.sdk.HubEvent(
                base.id(), base.sessionId(), base.type(), base.source(),
                base.occurredAt(), base.ingestedAt(), base.payload(), correlation));
    }
}
