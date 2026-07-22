package ai.assistanthub.core.memory;

import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.sdk.HubEvent;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova US2: depois de uma sessão retomada (nova instância de {@link SessionPersistenceStore}
 * apontando para o mesmo arquivo), novos eventos — de um canal já existente ou de um canal novo —
 * se juntam aos eventos anteriores em ordem cronológica correta, sem misturar canais.
 */
class SessionPersistenceAppendOrderTest {

    @TempDir
    Path tempDir;

    @Test
    void newEventsAfterResumeContinueChronologicalOrderWithoutMixingChannels() {
        SessionPersistenceStore beforeRestart = MemoryHubTestSupport.newStore(tempDir);
        ConversationSession session = ConversationSession.create("Retomada", "interview-technical", Map.of());
        beforeRestart.saveSession(session);

        HubEvent micEvent1 = eventOnChannel(session.id(), "mic", "microphone", "primeira fala do mic");
        beforeRestart.appendEvent(micEvent1);

        // "Restart": nova instância do store, mesmo arquivo em disco (sessão retomada).
        SessionPersistenceStore afterRestart = MemoryHubTestSupport.newStore(tempDir);

        HubEvent micEvent2 = eventOnChannel(session.id(), "mic", "microphone", "segunda fala do mic");
        HubEvent systemEvent = eventOnChannel(session.id(), "system", "system", "fala do sistema");
        afterRestart.appendEvent(micEvent2);
        afterRestart.appendEvent(systemEvent);

        List<HubEvent> events = afterRestart.findEvents(session.id());
        assertThat(events).hasSize(3);
        assertThat(events.get(0).id()).isEqualTo(micEvent1.id());
        assertThat(events.get(1).id()).isEqualTo(micEvent2.id());
        assertThat(events.get(2).id()).isEqualTo(systemEvent.id());

        assertThat(events.get(0).correlation()).containsEntry("channelId", "mic");
        assertThat(events.get(1).correlation()).containsEntry("channelId", "mic");
        assertThat(events.get(2).correlation()).containsEntry("channelId", "system");
    }

    private static HubEvent eventOnChannel(UUID sessionId, String channelId, String sourceType, String text) {
        Map<String, String> correlation = Map.of(
                "channelId", channelId, "sourceType", sourceType, "label", channelId);
        return new HubEvent(null, sessionId, "transcript.final.v2", "transcription-service",
                Instant.now(), null, Map.of("text", text), correlation);
    }
}
