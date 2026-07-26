package ai.assistanthub.core.memory;

import java.time.Instant;
import java.util.UUID;

/** Decisão / ação / compromisso extraído do transcript (heurística, R3.2). */
public record MemoryItem(
        MemoryItemKind kind,
        String text,
        UUID eventId,
        String sourceType,
        Instant occurredAt) {
}
