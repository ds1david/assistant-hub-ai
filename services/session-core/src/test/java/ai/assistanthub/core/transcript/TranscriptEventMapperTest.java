package ai.assistanthub.core.transcript;

import ai.assistanthub.sdk.HubEvent;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class TranscriptEventMapperTest {

    private final TranscriptEventMapper mapper = new TranscriptEventMapper();

    @Test
    void preservesChannelAndDeviceMetadata() {
        UUID sessionId = UUID.randomUUID();
        TranscriptEventV2 event = new TranscriptEventV2(
                "transcript.final.v2",
                "sess-1",
                "mic-1",
                "Microfone principal",
                "microphone",
                new TranscriptEventV2.Device(2, "Headset USB", "{0.0.1.00000000}.{guid}"),
                "ola mundo",
                "pt",
                0.98,
                120,
                3.2,
                0,
                Instant.parse("2026-07-22T12:00:00Z"),
                null);

        HubEvent hubEvent = mapper.toHubEvent(event, sessionId);

        assertThat(hubEvent.sessionId()).isEqualTo(sessionId);
        assertThat(hubEvent.type()).isEqualTo("transcript.final.v2");
        assertThat(hubEvent.source()).isEqualTo("transcription-service");
        assertThat(hubEvent.occurredAt()).isEqualTo(event.occurredAt());
        assertThat(hubEvent.correlation())
                .containsEntry("channelId", "mic-1")
                .containsEntry("sourceType", "microphone")
                .containsEntry("label", "Microfone principal")
                .containsEntry("device.index", "2")
                .containsEntry("device.name", "Headset USB")
                .containsEntry("device.endpointId", "{0.0.1.00000000}.{guid}");
        assertThat(hubEvent.payload())
                .containsEntry("text", "ola mundo")
                .containsEntry("language", "pt")
                .containsEntry("latencyMs", 120);
    }

    @Test
    void acceptsNullEndpointIdWithoutError() {
        UUID sessionId = UUID.randomUUID();
        TranscriptEventV2 event = new TranscriptEventV2(
                "transcript.partial.v2",
                "sess-1",
                "system",
                "Audio do sistema",
                "system",
                new TranscriptEventV2.Device(null, null, null),
                "parcial",
                null,
                null,
                80,
                null,
                null,
                Instant.parse("2026-07-22T12:00:01Z"),
                null);

        HubEvent hubEvent = mapper.toHubEvent(event, sessionId);

        assertThat(hubEvent.correlation())
                .containsEntry("device.index", "")
                .containsEntry("device.name", "")
                .containsEntry("device.endpointId", "");
        assertThat(hubEvent.payload()).doesNotContainKey("language");
    }

    @Test
    void preservesOptionalProsodyInPayload() {
        UUID sessionId = UUID.randomUUID();
        TranscriptEventV2 event = new TranscriptEventV2(
                "transcript.final.v2",
                "sess-1",
                "sys-1",
                "Sistema",
                "system",
                new TranscriptEventV2.Device(null, null, null),
                "voce ja usou spring",
                "pt",
                0.9,
                100,
                1.0,
                0,
                Instant.parse("2026-07-22T12:00:02Z"),
                java.util.Map.of(
                        "questionScore", 0.78,
                        "contour", "rising",
                        "f0EndSlopeSemitones", 2.1));

        HubEvent hubEvent = mapper.toHubEvent(event, sessionId);

        assertThat(hubEvent.payload()).containsKey("prosody");
        @SuppressWarnings("unchecked")
        java.util.Map<String, Object> prosody =
                (java.util.Map<String, Object>) hubEvent.payload().get("prosody");
        assertThat(prosody).containsEntry("questionScore", 0.78);
        assertThat(prosody).containsEntry("contour", "rising");
    }

    @Test
    void distinctChannelsProduceIndependentHubEvents() {
        UUID sessionId = UUID.randomUUID();
        Instant now = Instant.parse("2026-07-22T12:00:02Z");
        TranscriptEventV2 micEvent = new TranscriptEventV2(
                "transcript.final.v2", "sess-1", "mic", "Mic", "microphone",
                new TranscriptEventV2.Device(1, "Mic", null), "mesmo texto", null, null, 50, null, null, now, null);
        TranscriptEventV2 systemEvent = new TranscriptEventV2(
                "transcript.final.v2", "sess-1", "system", "System", "system",
                new TranscriptEventV2.Device(null, null, null), "mesmo texto", null, null, 50, null, null, now, null);

        HubEvent micHubEvent = mapper.toHubEvent(micEvent, sessionId);
        HubEvent systemHubEvent = mapper.toHubEvent(systemEvent, sessionId);

        assertThat(micHubEvent.correlation().get("channelId")).isEqualTo("mic");
        assertThat(systemHubEvent.correlation().get("channelId")).isEqualTo("system");
        assertThat(micHubEvent.id()).isNotEqualTo(systemHubEvent.id());
    }
}
