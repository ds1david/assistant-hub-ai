package ai.assistanthub.core.transcript;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class TranscriptContractTest {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final TranscriptEventValidator validator = new TranscriptEventValidator();

    @Test
    void acceptsValidEventWithEndpointId() throws Exception {
        JsonNode event = objectMapper.readTree("""
                {
                  "type": "transcript.final.v2",
                  "sessionId": "sess-1",
                  "channelId": "mic-1",
                  "label": "Microfone principal",
                  "sourceType": "microphone",
                  "device": {"index": 2, "name": "Headset USB", "endpointId": "{0.0.1.00000000}.{guid}"},
                  "text": "ola mundo",
                  "latencyMs": 120,
                  "occurredAt": "2026-07-22T12:00:00Z"
                }
                """);

        assertThat(validator.validate(event)).isEmpty();
    }

    @Test
    void acceptsValidEventWithNullEndpointId() throws Exception {
        JsonNode event = objectMapper.readTree("""
                {
                  "type": "transcript.partial.v2",
                  "sessionId": "sess-1",
                  "channelId": "system",
                  "label": "Audio do sistema",
                  "sourceType": "system",
                  "device": {"index": null, "name": null, "endpointId": null},
                  "text": "parcial",
                  "latencyMs": 80,
                  "occurredAt": "2026-07-22T12:00:01Z"
                }
                """);

        assertThat(validator.validate(event)).isEmpty();
    }

    @Test
    void rejectsEventMissingRequiredDeviceField() throws Exception {
        JsonNode event = objectMapper.readTree("""
                {
                  "type": "transcript.final.v2",
                  "sessionId": "sess-1",
                  "channelId": "mic-1",
                  "label": "Microfone principal",
                  "sourceType": "microphone",
                  "text": "sem device",
                  "latencyMs": 120,
                  "occurredAt": "2026-07-22T12:00:00Z"
                }
                """);

        assertThat(validator.validate(event)).isNotEmpty();
    }
}
