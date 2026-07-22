package ai.assistanthub.core.memory;

import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.sdk.HubEvent;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova US1: sessão e eventos gravados antes de um restart continuam idênticos depois — sem
 * GPU, sem hardware de áudio (FR-008). "Restart gracioso" é simulado abrindo uma nova instância
 * de {@link SessionPersistenceStore} apontando para o mesmo arquivo SQLite.
 */
class SessionPersistenceStoreTest {

    @TempDir
    Path tempDir;

    @Test
    void sessionAndEventsAcrossTwoChannelsSurviveReopeningTheSameFile() {
        SessionPersistenceStore beforeRestart = MemoryHubTestSupport.newStore(tempDir);

        ConversationSession session = ConversationSession.create(
                "Entrevista", "interview-technical", Map.of("perfil", "tecnico"));
        beforeRestart.saveSession(session);

        Map<String, String> micCorrelation =
                Map.of("channelId", "mic-1", "sourceType", "microphone", "label", "Microfone", "device.endpointId", "{mic}");
        Map<String, String> systemCorrelation =
                Map.of("channelId", "system-1", "sourceType", "system", "label", "Sistema", "device.endpointId", "");

        HubEvent micEvent = HubEvent.now(session.id(), "transcript.final.v2", "transcription-service",
                Map.of("text", "ola"));
        micEvent = withCorrelation(micEvent, micCorrelation);
        HubEvent systemEvent = HubEvent.now(session.id(), "transcript.final.v2", "transcription-service",
                Map.of("text", "som do sistema"));
        systemEvent = withCorrelation(systemEvent, systemCorrelation);

        beforeRestart.appendEvent(micEvent);
        beforeRestart.appendEvent(systemEvent);

        // "Restart gracioso": nova instância do store, mesmo arquivo em disco.
        SessionPersistenceStore afterRestart = MemoryHubTestSupport.newStore(tempDir);

        Optional<ConversationSession> reloadedSession = afterRestart.findSession(session.id());
        assertThat(reloadedSession).isPresent();
        assertThat(reloadedSession.get()).isEqualTo(session);

        List<HubEvent> reloadedEvents = afterRestart.findEvents(session.id());
        assertThat(reloadedEvents).hasSize(2);
        assertThat(reloadedEvents.get(0)).isEqualTo(micEvent);
        assertThat(reloadedEvents.get(1)).isEqualTo(systemEvent);
        assertThat(reloadedEvents.get(0).correlation()).containsEntry("channelId", "mic-1");
        assertThat(reloadedEvents.get(1).correlation()).containsEntry("channelId", "system-1");
    }

    @Test
    void sessionWithoutEventsSurvivesReopeningTheSameFile() {
        SessionPersistenceStore beforeRestart = MemoryHubTestSupport.newStore(tempDir);

        ConversationSession session = ConversationSession.create("Sem eventos", "interview-technical", Map.of());
        beforeRestart.saveSession(session);

        SessionPersistenceStore afterRestart = MemoryHubTestSupport.newStore(tempDir);

        assertThat(afterRestart.findSession(session.id())).contains(session);
        assertThat(afterRestart.findEvents(session.id())).isEmpty();
    }

    @Test
    void unknownSessionIsNotFound() {
        SessionPersistenceStore store = MemoryHubTestSupport.newStore(tempDir);
        assertThat(store.findSession(UUID.randomUUID())).isEmpty();
    }

    private static HubEvent withCorrelation(HubEvent event, Map<String, String> correlation) {
        return new HubEvent(event.id(), event.sessionId(), event.type(), event.source(),
                event.occurredAt(), event.ingestedAt(), event.payload(), correlation);
    }
}
