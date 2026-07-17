package ai.assistanthub.sdk;

import java.time.Instant;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

public record HubEvent(
        UUID id,
        UUID sessionId,
        String type,
        String source,
        Instant occurredAt,
        Instant ingestedAt,
        Map<String, Object> payload,
        Map<String, String> correlation) {

    public HubEvent {
        id = id == null ? UUID.randomUUID() : id;
        Objects.requireNonNull(sessionId, "sessionId");
        Objects.requireNonNull(type, "type");
        Objects.requireNonNull(source, "source");
        occurredAt = occurredAt == null ? Instant.now() : occurredAt;
        ingestedAt = ingestedAt == null ? Instant.now() : ingestedAt;
        payload = Map.copyOf(payload == null ? Map.of() : payload);
        correlation = Map.copyOf(correlation == null ? Map.of() : correlation);
    }

    public static HubEvent now(UUID sessionId, String type, String source, Map<String, Object> payload) {
        Instant now = Instant.now();
        return new HubEvent(null, sessionId, type, source, now, now, payload, Map.of());
    }
}
