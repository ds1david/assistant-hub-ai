package ai.assistanthub.core.memory;

import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.core.session.SessionStatus;
import ai.assistanthub.sdk.HubEvent;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova que `session_events.sequence` (`INTEGER PRIMARY KEY AUTOINCREMENT`) nunca é reutilizada
 * — mesmo depois que {@link RetentionPolicy} expurga TODOS os eventos de uma sessão anterior e a
 * tabela `session_events` fica temporariamente vazia. Sem `AUTOINCREMENT`, um ROWID simples
 * poderia ser reaproveitado nesse cenário, quebrando a ordem cronológica (FR-003) da próxima
 * sessão. O comportamento é garantido pelo motor SQLite (tabela `sqlite_sequence`), sem lógica
 * própria de contagem em {@link SessionPersistenceStore}.
 */
class SessionPersistenceSequenceIntegrityTest {

    @TempDir
    Path tempDir;

    @Test
    void sequenceIsNeverReusedAfterRetentionEmptiesTheEventsTable() {
        SessionPersistenceStore store = MemoryHubTestSupport.newStore(tempDir);

        ConversationSession oldSession = new ConversationSession(
                java.util.UUID.randomUUID(), "Antiga", "interview-technical", SessionStatus.ENDED,
                Instant.now().minusSeconds(60), Instant.now().minusSeconds(60), Instant.now().minusSeconds(30),
                Map.of());
        store.saveSession(oldSession);
        store.appendEvent(HubEvent.now(oldSession.id(), "transcript.final.v2", "transcription-service",
                Map.of("text", "evento antigo")));

        // Expurgo total da sessão antiga (mesma operação usada por RetentionPolicy) — a tabela
        // session_events fica momentaneamente sem nenhuma linha da sessão antiga.
        store.deleteSession(oldSession.id());
        assertThat(store.findEvents(oldSession.id())).isEmpty();

        ConversationSession newSession = ConversationSession.create("Nova", "interview-technical", Map.of());
        store.saveSession(newSession);
        HubEvent firstNewEvent = HubEvent.now(newSession.id(), "transcript.final.v2", "transcription-service",
                Map.of("text", "primeiro evento da sessão nova"));
        HubEvent secondNewEvent = HubEvent.now(newSession.id(), "transcript.final.v2", "transcription-service",
                Map.of("text", "segundo evento da sessão nova"));
        store.appendEvent(firstNewEvent);
        store.appendEvent(secondNewEvent);

        List<HubEvent> events = store.findEvents(newSession.id());
        assertThat(events).hasSize(2);
        assertThat(events.get(0).id()).isEqualTo(firstNewEvent.id());
        assertThat(events.get(1).id()).isEqualTo(secondNewEvent.id());
    }
}
