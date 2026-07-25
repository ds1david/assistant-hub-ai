package ai.assistanthub.core.provider;

import ai.assistanthub.core.session.SessionRepository;
import ai.assistanthub.sdk.HubEvent;
import org.springframework.stereotype.Component;

import java.util.LinkedHashSet;
import java.util.Set;
import java.util.UUID;

/**
 * Resolve {@code sourceType} canônico a partir de {@link HubEvent#correlation()} já gravados
 * na sessão (issue #40 / FR-010–FR-013). Chamador nunca é fonte de verdade.
 */
@Component
public class ChannelOriginResolver {

    private static final Set<String> CANONICAL = Set.of("microphone", "system");

    private final SessionRepository sessionRepository;

    public ChannelOriginResolver(SessionRepository sessionRepository) {
        this.sessionRepository = sessionRepository;
    }

    /**
     * @param sessionId string UUID da sessão
     * @param channelId canal referenciado (não blank)
     * @return origem canônica única do canal
     * @throws ChannelOriginUnresolvedException UUID inválido, sem eventos, valor não canônico ou conflito
     */
    public String resolve(String sessionId, String channelId) {
        UUID uuid;
        try {
            uuid = UUID.fromString(sessionId);
        } catch (IllegalArgumentException | NullPointerException e) {
            throw new ChannelOriginUnresolvedException(
                    "sessionId inválido para resolução de origem do canal (esperado UUID)");
        }

        Set<String> origins = new LinkedHashSet<>();
        for (HubEvent event : sessionRepository.events(uuid)) {
            if (event.correlation() == null) {
                continue;
            }
            String eventChannel = event.correlation().get("channelId");
            if (eventChannel == null || !eventChannel.equals(channelId)) {
                continue;
            }
            String sourceType = event.correlation().get("sourceType");
            if (sourceType == null || sourceType.isBlank()) {
                continue;
            }
            origins.add(sourceType);
        }

        if (origins.isEmpty()) {
            throw new ChannelOriginUnresolvedException(
                    "origem do canal '" + channelId + "' não resolvível: sem eventos com sourceType na sessão");
        }
        if (origins.size() > 1) {
            throw new ChannelOriginUnresolvedException(
                    "conflito de origem no canal '" + channelId + "': " + origins);
        }
        String origin = origins.iterator().next();
        if (!CANONICAL.contains(origin)) {
            throw new ChannelOriginUnresolvedException(
                    "origem do canal '" + channelId + "' não canônica: '" + origin + "'");
        }
        return origin;
    }
}
