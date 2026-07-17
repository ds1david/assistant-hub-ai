package ai.assistanthub.core.session;

import ai.assistanthub.sdk.HubEvent;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class SessionRepositoryTest {
    @Test
    void storesSessionAndEvents() {
        SessionRepository repository = new SessionRepository();
        ConversationSession session = repository.save(
                ConversationSession.create("Teste", "interview-technical", Map.of()));

        repository.append(HubEvent.now(session.id(), "transcript.partial.v1", "system", Map.of("text", "pergunta")));

        assertEquals(1, repository.events(session.id()).size());
    }
}
