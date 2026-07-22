package ai.assistanthub.core.memory;

import ai.assistanthub.core.session.ConversationSession;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.List;

/**
 * Aplica {@code session-core.memory-hub.retention.max-age}/{@code max-sessions} (issue #29 / R3,
 * FR-004) — expurga sessões {@code ENDED} mais antigas (e seus eventos, em cascata) sem nunca
 * remover uma sessão ativa. Sem configuração explícita, a retenção é indefinida (nenhuma sessão é
 * expurgada) — ver specs/013-issue-29-memory-hub-persistence/data-model.md.
 */
@Component
public class RetentionPolicy {

    private final MemoryHubProperties properties;
    private final SessionPersistenceStore persistenceStore;

    public RetentionPolicy(MemoryHubProperties properties, SessionPersistenceStore persistenceStore) {
        this.properties = properties;
        this.persistenceStore = persistenceStore;
    }

    /** Expurga sessões {@code ENDED} além do limite configurado; retorna quantas foram removidas. */
    public int purgeExpired() {
        Duration maxAge = properties.retention().maxAge();
        Integer maxSessions = properties.retention().maxSessions();
        if (maxAge == null && maxSessions == null) {
            return 0;
        }

        List<ConversationSession> endedOldestFirst = persistenceStore.findEndedSessionsOrderedByEndedAt();
        int purged = 0;

        if (maxAge != null) {
            Instant cutoff = Instant.now().minus(maxAge);
            for (ConversationSession session : endedOldestFirst) {
                if (session.endedAt() != null && session.endedAt().isBefore(cutoff)) {
                    persistenceStore.deleteSession(session.id());
                    purged++;
                }
            }
        }

        if (maxSessions != null) {
            List<ConversationSession> remaining = persistenceStore.findEndedSessionsOrderedByEndedAt();
            int excess = remaining.size() - maxSessions;
            for (int i = 0; i < excess; i++) {
                persistenceStore.deleteSession(remaining.get(i).id());
                purged++;
            }
        }

        return purged;
    }
}
