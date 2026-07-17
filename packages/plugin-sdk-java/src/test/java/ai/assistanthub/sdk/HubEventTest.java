package ai.assistanthub.sdk;

import org.junit.jupiter.api.Test;

import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class HubEventTest {
    @Test
    void createsEventWithDefaults() {
        UUID sessionId = UUID.randomUUID();
        HubEvent event = HubEvent.now(sessionId, "transcript.partial.v1", "microphone", Map.of("text", "olá"));

        assertNotNull(event.id());
        assertEquals(sessionId, event.sessionId());
        assertEquals("olá", event.payload().get("text"));
    }
}
