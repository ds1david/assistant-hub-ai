package ai.assistanthub.core.session;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

public record ConversationSession(
        UUID id,
        String title,
        String profileId,
        SessionStatus status,
        Instant createdAt,
        Instant startedAt,
        Instant endedAt,
        Map<String, Object> metadata) {

    public static ConversationSession create(String title, String profileId, Map<String, Object> metadata) {
        return new ConversationSession(
                UUID.randomUUID(), title, profileId, SessionStatus.CREATED,
                Instant.now(), null, null, Map.copyOf(metadata == null ? Map.of() : metadata));
    }
}
