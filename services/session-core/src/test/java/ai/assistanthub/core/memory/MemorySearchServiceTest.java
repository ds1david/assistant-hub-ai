package ai.assistanthub.core.memory;

import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.core.session.SessionRepository;
import ai.assistanthub.sdk.HubEvent;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class MemorySearchServiceTest {

    @TempDir
    Path tempDir;

    private SessionRepository repository;
    private MemorySearchService searchService;
    private UUID sessionId;

    @BeforeEach
    void setUp() throws Exception {
        SessionPersistenceStore store = MemoryHubTestSupport.newStore(tempDir);
        repository = new SessionRepository(store);
        searchService = new MemorySearchService(repository);
        ConversationSession session = ConversationSession.create("Mem", "interview-technical", Map.of());
        sessionId = session.id();
        repository.save(session);
        repository.append(event(sessionId, "Spring Boot na Claro", "system", Instant.parse("2026-07-26T10:00:00Z")));
        repository.append(event(sessionId, "Eu usei Java no projeto", "microphone", Instant.parse("2026-07-26T10:05:00Z")));
        repository.append(event(sessionId, "Decidimos adotar Postgres", "system", Instant.parse("2026-07-26T10:10:00Z")));
    }

    @Test
    void searchByQuery() {
        List<MemorySearchHit> hits = searchService.search(sessionId, "spring", null, null, null, 10);
        assertThat(hits).hasSize(1);
        assertThat(hits.get(0).text()).containsIgnoringCase("Spring");
        assertThat(hits.get(0).sourceType()).isEqualTo("system");
    }

    @Test
    void searchBySourceType() {
        List<MemorySearchHit> hits = searchService.search(sessionId, "", "microphone", null, null, 10);
        assertThat(hits).hasSize(1);
        assertThat(hits.get(0).sourceType()).isEqualTo("microphone");
    }

    @Test
    void searchByTimeWindow() {
        Instant from = Instant.parse("2026-07-26T10:04:00Z");
        Instant to = Instant.parse("2026-07-26T10:11:00Z");
        List<MemorySearchHit> hits = searchService.search(sessionId, null, null, from, to, 10);
        assertThat(hits).hasSize(2);
    }

    @Test
    void memoryItemsIncludesDecision() {
        List<MemoryItem> items = searchService.memoryItems(sessionId);
        assertThat(items).anyMatch(i -> i.kind() == MemoryItemKind.DECISION);
    }

    private static HubEvent event(UUID sessionId, String text, String sourceType, Instant at) {
        return new HubEvent(
                UUID.randomUUID(),
                sessionId,
                "transcript.final.v2",
                "transcription-service",
                at,
                at,
                Map.of("text", text),
                Map.of("sourceType", sourceType, "channelId", "c1"));
    }
}
