package ai.assistanthub.core.memory;

import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.core.session.SessionStatus;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova US3: um limite de retenção configurado expurga sessões {@code ENDED} mais antigas, nunca
 * remove uma sessão ativa, e novas gravações continuam funcionando normalmente depois do expurgo.
 */
class RetentionPolicyTest {

    @TempDir
    Path tempDir;

    @Test
    void purgesOldestEndedSessionsBeyondMaxSessionsWithoutTouchingActiveSession() {
        MemoryHubDataSource dataSource = MemoryHubTestSupport.newDataSource(tempDir);
        SessionPersistenceStore store = new SessionPersistenceStore(dataSource, MemoryHubTestSupport.newObjectMapper());

        ConversationSession oldest = endedSession("Mais antiga", Instant.now().minusSeconds(300));
        ConversationSession middle = endedSession("Do meio", Instant.now().minusSeconds(200));
        ConversationSession newest = endedSession("Mais recente", Instant.now().minusSeconds(100));
        ConversationSession active = ConversationSession.create("Ativa", "interview-technical", Map.of());

        store.saveSession(oldest);
        store.saveSession(middle);
        store.saveSession(newest);
        store.saveSession(active);

        RetentionPolicy retentionPolicy = new RetentionPolicy(
                new MemoryHubProperties(null, new MemoryHubProperties.Retention(null, 1)), store);

        int purged = retentionPolicy.purgeExpired();

        assertThat(purged).isEqualTo(2);
        assertThat(store.findSession(oldest.id())).isEmpty();
        assertThat(store.findSession(middle.id())).isEmpty();
        assertThat(store.findSession(newest.id())).isPresent();
        assertThat(store.findSession(active.id())).isPresent();

        // Novas gravações continuam funcionando normalmente após o expurgo.
        ConversationSession afterPurge = ConversationSession.create("Depois do expurgo", "interview-technical", Map.of());
        store.saveSession(afterPurge);
        assertThat(store.findSession(afterPurge.id())).isPresent();
    }

    @Test
    void doesNothingWhenNoRetentionLimitIsConfigured() {
        MemoryHubDataSource dataSource = MemoryHubTestSupport.newDataSource(tempDir);
        SessionPersistenceStore store = new SessionPersistenceStore(dataSource, MemoryHubTestSupport.newObjectMapper());
        store.saveSession(endedSession("Antiga sem limite", Instant.now().minusSeconds(10_000)));

        RetentionPolicy retentionPolicy = new RetentionPolicy(new MemoryHubProperties(null, null), store);

        assertThat(retentionPolicy.purgeExpired()).isZero();
        assertThat(store.findAllSessions()).hasSize(1);
    }

    private static ConversationSession endedSession(String title, Instant endedAt) {
        return new ConversationSession(
                UUID.randomUUID(), title, "interview-technical", SessionStatus.ENDED,
                endedAt, endedAt, endedAt, Map.of());
    }
}
