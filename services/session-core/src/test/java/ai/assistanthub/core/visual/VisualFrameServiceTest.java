package ai.assistanthub.core.visual;

import ai.assistanthub.core.memory.MemoryHubTestSupport;
import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.core.session.SessionRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.web.server.ResponseStatusException;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class VisualFrameServiceTest {

    @TempDir
    Path tempDir;

    private SessionRepository repository;
    private VisualFrameService service;
    private UUID sessionId;

    @BeforeEach
    void setUp() {
        repository = new SessionRepository(MemoryHubTestSupport.newStore(tempDir));
        service = new VisualFrameService(repository, new FakeOcrEngine());
        ConversationSession session = ConversationSession.create("Vis", "interview-technical", Map.of());
        sessionId = session.id();
        repository.save(session);
    }

    @Test
    void rejectsWithoutConsent() {
        assertThatThrownBy(() -> service.ingest(sessionId, false, "text", null, "shell", null, null, null, null))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("consent");
    }

    @Test
    void ingestsAndListsWithMaskedOcr() {
        Map<String, Object> created = service.ingest(
                sessionId,
                true,
                "Email me at secret@example.com about Java",
                null,
                "shell-stub",
                null,
                100,
                50,
                null);
        assertThat(created.get("type")).isEqualTo(VisualFrameService.EVENT_TYPE);
        @SuppressWarnings("unchecked")
        Map<String, Object> payload = (Map<String, Object>) created.get("payload");
        assertThat(payload.get("ocrText").toString()).contains("[email]");
        assertThat(payload.get("ocrText").toString()).doesNotContain("secret@example.com");
        assertThat(payload.get("masked")).isEqualTo(true);
        assertThat(payload.get("consent")).isEqualTo(true);
        assertThat(payload.get("imageStored")).isEqualTo(false);

        List<Map<String, Object>> list = service.list(sessionId);
        assertThat(list).hasSize(1);
        assertThat(list.get(0).get("eventId")).isEqualTo(created.get("eventId"));
    }

    @Test
    void unknownSessionNotFound() {
        assertThatThrownBy(() -> service.list(UUID.randomUUID()))
                .isInstanceOf(ResponseStatusException.class);
    }
}
