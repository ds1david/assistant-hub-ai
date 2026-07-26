package ai.assistanthub.core.session;

import ai.assistanthub.core.memory.SessionPersistenceStore;
import ai.assistanthub.sdk.HubEvent;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.Collections;
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
 *
 * <p>As listas de eventos por sessão são {@link Collections#synchronizedList}; {@link #append}
 * e {@link #events} sincronizam no mesmo monitor da lista. Isso permite que o
 * {@code TranscriptFeedClient} despache mensagens do feed WebSocket em threads de I/O
 * distintas sem corromper ou perder eventos sob canais concorrentes (SF-021 / FR-003).
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
        events.putIfAbsent(session.id(), newEventList());
        persistenceStore.saveSession(session);
        return session;
    }

    public Optional<ConversationSession> findById(UUID id) {
        return Optional.ofNullable(sessions.get(id));
    }

    /**
     * Lista sessões conhecidas no cache (rehidratado do Memory Hub na subida).
     * Ordenação: {@code createdAt} descendente (mais recente primeiro).
     */
    public List<ConversationSession> list() {
        return sessions.values().stream()
                .sorted((a, b) -> b.createdAt().compareTo(a.createdAt()))
                .toList();
    }

    public void append(HubEvent event) {
        List<HubEvent> sessionEvents = events.computeIfAbsent(event.sessionId(), ignored -> newEventList());
        // Memória + persistência sob o mesmo monitor da sessão: evita corrida no ArrayList e
        // inserts SQLite concorrentes na mesma sessão (busy/UNIQUE sob carga multi-canal).
        synchronized (sessionEvents) {
            sessionEvents.add(event);
            persistenceStore.appendEvent(event);
        }
    }

    public List<HubEvent> events(UUID sessionId) {
        List<HubEvent> sessionEvents = events.get(sessionId);
        if (sessionEvents == null) {
            return List.of();
        }
        synchronized (sessionEvents) {
            return List.copyOf(sessionEvents);
        }
    }

    /**
     * Popula apenas o cache em memória a partir de dados já persistidos, sem regravar no Memory
     * Hub (evitaria violar a restrição {@code UNIQUE} de {@code event_id}) — uso exclusivo de
     * {@code MemoryHubStartupRehydrator} na subida do processo.
     */
    public void hydrate(ConversationSession session, List<HubEvent> sessionEvents) {
        sessions.put(session.id(), session);
        List<HubEvent> copy = newEventList();
        synchronized (copy) {
            copy.addAll(sessionEvents);
        }
        events.put(session.id(), copy);
    }

    private static List<HubEvent> newEventList() {
        return Collections.synchronizedList(new ArrayList<>());
    }
}
