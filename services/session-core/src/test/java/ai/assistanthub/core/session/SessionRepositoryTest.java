package ai.assistanthub.core.session;

import ai.assistanthub.core.memory.MemoryHubTestSupport;
import ai.assistanthub.sdk.HubEvent;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class SessionRepositoryTest {

    @TempDir
    Path tempDir;

    @Test
    void storesSessionAndEvents() {
        SessionRepository repository = new SessionRepository(MemoryHubTestSupport.newStore(tempDir));
        ConversationSession session = repository.save(
                ConversationSession.create("Teste", "interview-technical", Map.of()));

        repository.append(HubEvent.now(session.id(), "transcript.partial.v1", "system", Map.of("text", "pergunta")));

        assertEquals(1, repository.events(session.id()).size());
    }
}
