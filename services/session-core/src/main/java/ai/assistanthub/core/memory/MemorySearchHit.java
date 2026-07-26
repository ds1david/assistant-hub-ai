package ai.assistanthub.core.memory;

import java.time.Instant;
import java.util.UUID;

/** Hit de busca textual/temporal sobre eventos da sessão (R3.2 / issue #65). */
public record MemorySearchHit(
        UUID eventId,
        String type,
        String text,
        String sourceType,
        String channelId,
        Instant occurredAt) {
}
