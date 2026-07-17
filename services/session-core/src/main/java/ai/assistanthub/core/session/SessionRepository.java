package ai.assistanthub.core.session;

import ai.assistanthub.sdk.HubEvent;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@Repository
public class SessionRepository {
    private final Map<UUID, ConversationSession> sessions = new ConcurrentHashMap<>();
    private final Map<UUID, List<HubEvent>> events = new ConcurrentHashMap<>();

    public ConversationSession save(ConversationSession session) {
        sessions.put(session.id(), session);
        events.putIfAbsent(session.id(), new ArrayList<>());
        return session;
    }

    public Optional<ConversationSession> findById(UUID id) {
        return Optional.ofNullable(sessions.get(id));
    }

    public void append(HubEvent event) {
        events.computeIfAbsent(event.sessionId(), ignored -> new ArrayList<>()).add(event);
    }

    public List<HubEvent> events(UUID sessionId) {
        return List.copyOf(events.getOrDefault(sessionId, List.of()));
    }
}
