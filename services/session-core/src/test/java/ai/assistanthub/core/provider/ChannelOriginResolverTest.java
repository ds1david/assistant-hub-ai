package ai.assistanthub.core.provider;

import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.core.session.SessionRepository;
import ai.assistanthub.sdk.HubEvent;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Resolvedor de origem (issue #40): canônicos, conflito, UUID inválido.
 */
class ChannelOriginResolverTest {

    @TempDir
    Path tempDir;

    private SessionRepository sessionRepository;
    private ChannelOriginResolver resolver;

    @BeforeEach
    void setUp() {
        sessionRepository = ProviderTestSupport.newSessionRepository(tempDir);
        resolver = ProviderTestSupport.newOriginResolver(sessionRepository);
    }

    @Test
    void resolvesMicrophoneFromSessionEvents() {
        String sessionId = ProviderTestSupport.seedChannelOrigin(sessionRepository, "mic-1", "microphone");

        assertThat(resolver.resolve(sessionId, "mic-1")).isEqualTo("microphone");
    }

    @Test
    void resolvesSystemFromSessionEvents() {
        String sessionId = ProviderTestSupport.seedChannelOrigin(sessionRepository, "sys-1", "system");

        assertThat(resolver.resolve(sessionId, "sys-1")).isEqualTo("system");
    }

    @Test
    void rejectsInvalidSessionUuid() {
        assertThatThrownBy(() -> resolver.resolve("session-1", "mic-1"))
                .isInstanceOf(ChannelOriginUnresolvedException.class)
                .hasMessageContaining("UUID");
    }

    @Test
    void rejectsMissingEvents() {
        ConversationSession session = ConversationSession.create("vazia", "test", Map.of());
        sessionRepository.save(session);

        assertThatThrownBy(() -> resolver.resolve(session.id().toString(), "mic-1"))
                .isInstanceOf(ChannelOriginUnresolvedException.class)
                .hasMessageContaining("não resolvível");
    }

    @Test
    void rejectsNonCanonicalOrigin() {
        String sessionId = seedRawOrigin("mic-1", "other");

        assertThatThrownBy(() -> resolver.resolve(sessionId, "mic-1"))
                .isInstanceOf(ChannelOriginUnresolvedException.class)
                .hasMessageContaining("não canônica");
    }

    @Test
    void rejectsConflictingOriginsOnSameChannel() {
        ConversationSession session = ConversationSession.create("conflito", "test", Map.of());
        sessionRepository.save(session);
        appendEvent(session.id(), "mic-1", "microphone");
        appendEvent(session.id(), "mic-1", "system");

        assertThatThrownBy(() -> resolver.resolve(session.id().toString(), "mic-1"))
                .isInstanceOf(ChannelOriginUnresolvedException.class)
                .hasMessageContaining("conflito");
    }

    @Test
    void ignoresOtherChannelsWhenResolving() {
        ConversationSession session = ConversationSession.create("multi", "test", Map.of());
        sessionRepository.save(session);
        appendEvent(session.id(), "mic-1", "microphone");
        appendEvent(session.id(), "sys-1", "system");

        assertThat(resolver.resolve(session.id().toString(), "mic-1")).isEqualTo("microphone");
        assertThat(resolver.resolve(session.id().toString(), "sys-1")).isEqualTo("system");
    }

    private String seedRawOrigin(String channelId, String sourceType) {
        ConversationSession session = ConversationSession.create("raw", "test", Map.of());
        sessionRepository.save(session);
        appendEvent(session.id(), channelId, sourceType);
        return session.id().toString();
    }

    private void appendEvent(UUID sessionId, String channelId, String sourceType) {
        Map<String, String> correlation = Map.of(
                "channelId", channelId,
                "sourceType", sourceType,
                "label", channelId);
        HubEvent base = HubEvent.now(sessionId, "transcript.final.v2", "transcription-service", Map.of("text", "x"));
        sessionRepository.append(new HubEvent(
                base.id(), base.sessionId(), base.type(), base.source(),
                base.occurredAt(), base.ingestedAt(), base.payload(), correlation));
    }
}
