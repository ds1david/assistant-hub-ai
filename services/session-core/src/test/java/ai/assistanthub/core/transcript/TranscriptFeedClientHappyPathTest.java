package ai.assistanthub.core.transcript;

import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.core.session.SessionRepository;
import ai.assistanthub.sdk.HubEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
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

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova US1 ponta a ponta: um evento sintético publicado num feed WebSocket fake (que reproduz o
 * formato de /ws/transcripts) chega ao session-core e vira um registro na sessão preservando os
 * metadados de canal/dispositivo — sem hardware, GPU ou STT real (FR-007).
 */
@SpringBootTest(
        classes = TranscriptFeedClientHappyPathTest.FakeFeedServerConfig.class,
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class TranscriptFeedClientHappyPathTest {

    @LocalServerPort
    private int port;

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
    void partialThenFinalEventsAreBothRecordedInChronologicalOrder() throws Exception {
        SessionRepository sessionRepository = new SessionRepository();
        ConversationSession session = sessionRepository.save(
                ConversationSession.create("Entrevista", "interview-technical", Map.of()));

        TranscriptIngestionProperties properties =
                new TranscriptIngestionProperties("ws://localhost:" + port + "/ws/transcripts");
        client = new TranscriptFeedClient(properties, validator, mapper, sessionRepository, objectMapper);
        client.connect();

        waitUntil(() -> !FakeFeedServerConfig.SESSIONS.isEmpty(), "cliente não conectou ao feed fake");

        Map<String, Object> device = Map.of("index", 2, "name", "Headset USB", "endpointId", "{guid-mic}");
        FakeFeedServerConfig.broadcast(objectMapper, Map.of(
                "type", "transcript.partial.v2",
                "sessionId", session.id().toString(),
                "channelId", "mic-1",
                "label", "Microfone principal",
                "sourceType", "microphone",
                "device", device,
                "text", "ola",
                "latencyMs", 90,
                "occurredAt", Instant.parse("2026-07-22T12:00:00Z").toString()));
        FakeFeedServerConfig.broadcast(objectMapper, Map.of(
                "type", "transcript.final.v2",
                "sessionId", session.id().toString(),
                "channelId", "mic-1",
                "label", "Microfone principal",
                "sourceType", "microphone",
                "device", device,
                "text", "ola mundo",
                "latencyMs", 130,
                "occurredAt", Instant.parse("2026-07-22T12:00:01Z").toString()));

        waitUntil(() -> sessionRepository.events(session.id()).size() == 2, "eventos não chegaram à sessão");

        List<HubEvent> events = sessionRepository.events(session.id());
        assertThat(events).hasSize(2);
        assertThat(events.get(0).type()).isEqualTo("transcript.partial.v2");
        assertThat(events.get(1).type()).isEqualTo("transcript.final.v2");
        assertThat(events.get(0).correlation())
                .containsEntry("channelId", "mic-1")
                .containsEntry("sourceType", "microphone")
                .containsEntry("device.endpointId", "{guid-mic}");
        assertThat(events.get(1).payload()).containsEntry("text", "ola mundo");
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
