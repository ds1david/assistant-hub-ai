package ai.assistanthub.core.transcript;

import ai.assistanthub.core.memory.MemoryHubTestSupport;
import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.core.session.SessionRepository;
import ai.assistanthub.sdk.HubEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova US2: dois canais ("mic" e "system") ativos na mesma sessão nunca se misturam — cada
 * evento registrado mantém o channelId/sourceType/device de origem correto, mesmo quando o texto
 * transcrito coincide entre canais (FR-003).
 */
@SpringBootTest(
        classes = TranscriptFeedClientMultiChannelTest.FakeFeedServerConfig.class,
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class TranscriptFeedClientMultiChannelTest {

    @LocalServerPort
    private int port;

    @TempDir
    Path tempDir;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private final TranscriptEventValidator validator = new TranscriptEventValidator();
    private final TranscriptEventMapper mapper = new TranscriptEventMapper();
    private TranscriptFeedClient client;

    @AfterEach
    void tearDown() {
        if (client != null) {
            client.close();
        }
        FakeFeedServerConfig.SESSIONS.clear();
    }

    @Test
    void interleavedChannelsNeverMixMetadataOrGetDeduplicated() throws Exception {
        SessionRepository sessionRepository = new SessionRepository(MemoryHubTestSupport.newStore(tempDir));
        ConversationSession session = sessionRepository.save(
                ConversationSession.create("Refinamento", "product-refinement", Map.of()));

        TranscriptIngestionProperties properties =
                new TranscriptIngestionProperties("ws://localhost:" + port + "/ws/transcripts");
        client = new TranscriptFeedClient(properties, validator, mapper, sessionRepository, objectMapper);
        client.connect();
        waitUntil(() -> !FakeFeedServerConfig.SESSIONS.isEmpty(), "cliente não conectou ao feed fake");

        String sameText = "isso é uma coincidência";
        FakeFeedServerConfig.broadcast(objectMapper, event("transcript.final.v2", session.id().toString(),
                "mic", "Microfone", "microphone", Map.of("index", 1, "name", "Mic", "endpointId", "{mic}"),
                sameText, "2026-07-22T12:00:00Z"));
        Map<String, Object> nullDevice = new java.util.HashMap<>();
        nullDevice.put("index", null);
        nullDevice.put("name", null);
        nullDevice.put("endpointId", null);
        FakeFeedServerConfig.broadcast(objectMapper, event("transcript.final.v2", session.id().toString(),
                "system", "Sistema", "system", nullDevice,
                sameText, "2026-07-22T12:00:01Z"));
        FakeFeedServerConfig.broadcast(objectMapper, event("transcript.final.v2", session.id().toString(),
                "mic", "Microfone", "microphone", Map.of("index", 1, "name", "Mic", "endpointId", "{mic}"),
                "segunda fala do mic", "2026-07-22T12:00:02Z"));

        waitUntil(() -> sessionRepository.events(session.id()).size() == 3, "eventos não chegaram à sessão");

        List<HubEvent> events = sessionRepository.events(session.id());
        assertThat(events).hasSize(3);

        assertThat(events.get(0).correlation()).containsEntry("channelId", "mic");
        assertThat(events.get(1).correlation()).containsEntry("channelId", "system");
        assertThat(events.get(2).correlation()).containsEntry("channelId", "mic");

        // mesmo texto em canais diferentes permanece como dois registros distintos, não deduplicados
        assertThat(events.get(0).payload().get("text")).isEqualTo(sameText);
        assertThat(events.get(1).payload().get("text")).isEqualTo(sameText);
        assertThat(events.get(0).id()).isNotEqualTo(events.get(1).id());
        assertThat(events.get(1).correlation()).doesNotContainEntry("channelId", "mic");
    }

    private static Map<String, Object> event(String type, String sessionId, String channelId, String label,
            String sourceType, Map<String, Object> device, String text, String occurredAt) {
        Map<String, Object> event = new java.util.LinkedHashMap<>();
        event.put("type", type);
        event.put("sessionId", sessionId);
        event.put("channelId", channelId);
        event.put("label", label);
        event.put("sourceType", sourceType);
        event.put("device", device);
        event.put("text", text);
        event.put("latencyMs", 100);
        event.put("occurredAt", Instant.parse(occurredAt).toString());
        return event;
    }

    private static void waitUntil(java.util.function.BooleanSupplier condition, String failureMessage)
            throws InterruptedException {
        Instant deadline = Instant.now().plus(Duration.ofSeconds(5));
        while (Instant.now().isBefore(deadline)) {
            if (condition.getAsBoolean()) {
                return;
            }
            Thread.sleep(50);
        }
        throw new AssertionError(failureMessage);
    }

    @Configuration
    @EnableAutoConfiguration
    @EnableWebSocket
    static class FakeFeedServerConfig implements WebSocketConfigurer {

        static final List<WebSocketSession> SESSIONS = new CopyOnWriteArrayList<>();

        @Override
        public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
            registry.addHandler(new TextWebSocketHandler() {
                @Override
                public void afterConnectionEstablished(WebSocketSession session) {
                    SESSIONS.add(session);
                }

                @Override
                public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
                    SESSIONS.remove(session);
                }
            }, "/ws/transcripts");
        }

        static void broadcast(ObjectMapper objectMapper, Object event) throws Exception {
            String json = objectMapper.writeValueAsString(event);
            for (WebSocketSession session : SESSIONS) {
                session.sendMessage(new TextMessage(json));
            }
        }
    }
}
