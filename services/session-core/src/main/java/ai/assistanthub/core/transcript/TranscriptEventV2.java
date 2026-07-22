package ai.assistanthub.core.transcript;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.Instant;

/**
 * Espelha contracts/transcript-event.v2.schema.json (P4 — sem duplicar regras de validação,
 * apenas a forma dos dados; a conformidade real é checada por {@link TranscriptEventValidator}).
 */
public record TranscriptEventV2(
        String type,
        String sessionId,
        String channelId,
        String label,
        String sourceType,
        Device device,
        String text,
        String language,
        Double languageProbability,
        int latencyMs,
        Double audioSeconds,
        Integer droppedWindows,
        Instant occurredAt) {

    @JsonCreator
    public TranscriptEventV2(
            @JsonProperty("type") String type,
            @JsonProperty("sessionId") String sessionId,
            @JsonProperty("channelId") String channelId,
            @JsonProperty("label") String label,
            @JsonProperty("sourceType") String sourceType,
            @JsonProperty("device") Device device,
            @JsonProperty("text") String text,
            @JsonProperty("language") String language,
            @JsonProperty("languageProbability") Double languageProbability,
            @JsonProperty("latencyMs") int latencyMs,
            @JsonProperty("audioSeconds") Double audioSeconds,
            @JsonProperty("droppedWindows") Integer droppedWindows,
            @JsonProperty("occurredAt") Instant occurredAt) {
        this.type = type;
        this.sessionId = sessionId;
        this.channelId = channelId;
        this.label = label;
        this.sourceType = sourceType;
        this.device = device;
        this.text = text;
        this.language = language;
        this.languageProbability = languageProbability;
        this.latencyMs = latencyMs;
        this.audioSeconds = audioSeconds;
        this.droppedWindows = droppedWindows;
        this.occurredAt = occurredAt;
    }

    public record Device(
            @JsonProperty("index") Integer index,
            @JsonProperty("name") String name,
            @JsonProperty("endpointId") String endpointId) {

        @JsonCreator
        public Device {
        }
    }
}
