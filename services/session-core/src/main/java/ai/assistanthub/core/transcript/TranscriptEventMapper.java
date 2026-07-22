package ai.assistanthub.core.transcript;

import ai.assistanthub.sdk.HubEvent;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Traduz um {@link TranscriptEventV2} para o {@link HubEvent} genérico já consumido por
 * SessionRepository/SessionController — sem ampliar o SDK compartilhado (P4). Metadados de
 * canal/dispositivo vão para {@code correlation}; conteúdo da transcrição vai para
 * {@code payload} (FR-002/FR-003).
 */
@Component
public class TranscriptEventMapper {

    private static final String SOURCE = "transcription-service";

    public HubEvent toHubEvent(TranscriptEventV2 event, UUID sessionId) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("text", event.text());
        if (event.language() != null) {
            payload.put("language", event.language());
        }
        if (event.languageProbability() != null) {
            payload.put("languageProbability", event.languageProbability());
        }
        payload.put("latencyMs", event.latencyMs());
        if (event.audioSeconds() != null) {
            payload.put("audioSeconds", event.audioSeconds());
        }
        if (event.droppedWindows() != null) {
            payload.put("droppedWindows", event.droppedWindows());
        }

        TranscriptEventV2.Device device = event.device();
        Map<String, String> correlation = new LinkedHashMap<>();
        correlation.put("channelId", event.channelId());
        correlation.put("sourceType", event.sourceType());
        correlation.put("label", event.label());
        correlation.put("device.index", device.index() == null ? "" : String.valueOf(device.index()));
        correlation.put("device.name", device.name() == null ? "" : device.name());
        correlation.put("device.endpointId", device.endpointId() == null ? "" : device.endpointId());

        return new HubEvent(null, sessionId, event.type(), SOURCE, event.occurredAt(), null, payload, correlation);
    }
}
