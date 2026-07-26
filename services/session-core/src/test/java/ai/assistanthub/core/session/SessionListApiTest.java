package ai.assistanthub.core.session;

import ai.assistanthub.core.memory.MemoryHubTestSupport;
import ai.assistanthub.core.memory.MemorySearchService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * GET /api/sessions (FR-026) — lista vazia e com N sessões, ordenação createdAt desc.
 * Controller construído diretamente (mesmo padrão de AiProviderControllerTest).
 */
class SessionListApiTest {

    @TempDir
    Path tempDir;

    private SessionController controller;
    private SessionRepository repository;

    @BeforeEach
    void setUp() {
        repository = new SessionRepository(MemoryHubTestSupport.newStore(tempDir));
        controller = new SessionController(repository, new MemorySearchService(repository));
    }

    @Test
    void listsEmptyWhenNoSessions() {
        assertThat(controller.listSessions()).isEmpty();
    }

    @Test
    void listsCreatedSessionsNewestFirst() throws InterruptedException {
        ConversationSession first = repository.save(
                ConversationSession.create("Primeira", "interview-technical", Map.of()));
        Thread.sleep(5);
        ConversationSession second = repository.save(
                ConversationSession.create("Segunda", "interview-technical", Map.of()));

        List<ConversationSession> listed = controller.listSessions();

        assertThat(listed).hasSize(2);
        assertThat(listed.get(0).id()).isEqualTo(second.id());
        assertThat(listed.get(1).id()).isEqualTo(first.id());
        assertThat(listed).extracting(ConversationSession::title)
                .containsExactly("Segunda", "Primeira");
    }
}
