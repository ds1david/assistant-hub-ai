package ai.assistanthub.core.memory;

import ai.assistanthub.core.session.SessionRepository;
import ai.assistanthub.sdk.HubEvent;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

/**
 * Busca textual/temporal sobre eventos da sessão (cache Memory Hub). Sem embeddings (R3.2 P0).
 */
@Service
public class MemorySearchService {

    public static final int DEFAULT_LIMIT = 50;
    public static final int MAX_LIMIT = 200;

    private final SessionRepository sessionRepository;

    public MemorySearchService(SessionRepository sessionRepository) {
        this.sessionRepository = sessionRepository;
    }

    public List<MemorySearchHit> search(
            UUID sessionId,
            String query,
            String sourceType,
            Instant from,
            Instant to,
            Integer limit) {
        String q = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        int lim = limit == null ? DEFAULT_LIMIT : Math.min(Math.max(limit, 1), MAX_LIMIT);
        List<HubEvent> events = sessionRepository.events(sessionId);
        List<MemorySearchHit> hits = new ArrayList<>();
        for (HubEvent event : events) {
            if (from != null && event.occurredAt().isBefore(from)) {
                continue;
            }
            if (to != null && event.occurredAt().isAfter(to)) {
                continue;
            }
            String st = correlation(event, "sourceType");
            if (sourceType != null && !sourceType.isBlank() && !sourceType.equalsIgnoreCase(st)) {
                continue;
            }
            String text = HeuristicMemoryExtractor.textOf(event);
            if (text == null) {
                continue;
            }
            if (!q.isEmpty() && !text.toLowerCase(Locale.ROOT).contains(q)) {
                continue;
            }
            hits.add(new MemorySearchHit(
                    event.id(),
                    event.type(),
                    text,
                    st,
                    correlation(event, "channelId"),
                    event.occurredAt()));
            if (hits.size() >= lim) {
                break;
            }
        }
        return hits;
    }

    public List<MemoryItem> memoryItems(UUID sessionId) {
        return HeuristicMemoryExtractor.extract(sessionRepository.events(sessionId));
    }

    private static String correlation(HubEvent event, String key) {
        Map<String, String> c = event.correlation();
        return c == null ? null : c.get(key);
    }
}
