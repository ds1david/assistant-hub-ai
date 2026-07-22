package ai.assistanthub.core.session;

import ai.assistanthub.core.memory.SessionPersistenceStore;
import ai.assistanthub.sdk.HubEvent;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Cache em memória de sessões/eventos, apoiado por {@link SessionPersistenceStore} (Memory Hub,
 * issue #29 / R3) — cada {@code save}/{@code append} grava nos dois lugares na mesma operação;
 * leituras continuam servidas pelo cache, agora repovoado a partir do SQLite na subida do
 * processo (ver {@code ai.assistanthub.core.memory.MemoryHubStartupRehydrator}).
 */
@Repository
public class SessionRepository {
    private final Map<UUID, ConversationSession> sessions = new ConcurrentHashMap<>();
    private final Map<UUID, List<HubEvent>> events = new ConcurrentHashMap<>();
    private final SessionPersistenceStore persistenceStore;

    public SessionRepository(SessionPersistenceStore persistenceStore) {
        this.persistenceStore = persistenceStore;
    }

    public ConversationSession save(ConversationSession session) {
        sessions.put(session.id(), session);
        events.putIfAbsent(session.id(), new ArrayList<>());
        persistenceStore.saveSession(session);
        return session;
    }

    public Optional<ConversationSession> findById(UUID id) {
        return Optional.ofNullable(sessions.get(id));
    }

    public void append(HubEvent event) {
        events.computeIfAbsent(event.sessionId(), ignored -> new ArrayList<>()).add(event);
        persistenceStore.appendEvent(event);
    }

    public List<HubEvent> events(UUID sessionId) {
        return List.copyOf(events.getOrDefault(sessionId, List.of()));
    }

    /**
     * Popula apenas o cache em memória a partir de dados já persistidos, sem regravar no Memory
     * Hub (evitaria violar a restrição {@code UNIQUE} de {@code event_id}) — uso exclusivo de
     * {@code MemoryHubStartupRehydrator} na subida do processo.
     */
    public void hydrate(ConversationSession session, List<HubEvent> sessionEvents) {
        sessions.put(session.id(), session);
        events.put(session.id(), new ArrayList<>(sessionEvents));
    }
}
