package ai.assistanthub.core.memory;

import ai.assistanthub.sdk.HubEvent;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class HeuristicMemoryExtractorTest {

    @Test
    void classifiesDecisionActionCommitment() {
        assertThat(HeuristicMemoryExtractor.classify("Decidimos usar Spring Boot no monólito"))
                .isEqualTo(MemoryItemKind.DECISION);
        assertThat(HeuristicMemoryExtractor.classify("Vamos migrar o deploy na sexta"))
                .isEqualTo(MemoryItemKind.ACTION);
        assertThat(HeuristicMemoryExtractor.classify("Me comprometo a entregar o RFC até sexta"))
                .isEqualTo(MemoryItemKind.COMMITMENT);
        assertThat(HeuristicMemoryExtractor.classify("Como funciona o garbage collector?"))
                .isNull();
    }

    @Test
    void extractFromEvents() {
        UUID session = UUID.randomUUID();
        HubEvent e1 = event(session, "We decided to use Postgres", "system");
        HubEvent e2 = event(session, "hello world", "microphone");
        List<MemoryItem> items = HeuristicMemoryExtractor.extract(List.of(e1, e2));
        assertThat(items).hasSize(1);
        assertThat(items.get(0).kind()).isEqualTo(MemoryItemKind.DECISION);
        assertThat(items.get(0).sourceType()).isEqualTo("system");
    }

    private static HubEvent event(UUID sessionId, String text, String sourceType) {
        Instant now = Instant.parse("2026-07-26T12:00:00Z");
        return new HubEvent(
                UUID.randomUUID(),
                sessionId,
                "transcript.final.v2",
                "transcription-service",
                now,
                now,
                Map.of("text", text),
                Map.of("sourceType", sourceType, "channelId", "ch-1"));
    }
}
