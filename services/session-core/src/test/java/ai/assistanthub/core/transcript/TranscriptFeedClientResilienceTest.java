package ai.assistanthub.core.transcript;

import ai.assistanthub.core.memory.MemoryHubTestSupport;
import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.core.session.SessionRepository;
import ai.assistanthub.core.session.SessionStatus;
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
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova US3: session-core é um consumidor passivo e resiliente — evento sem campo obrigatório e
 * evento de sessão desconhecida/encerrada são descartados sem derrubar a ingestão de outros
 * eventos, e nenhuma mensagem é enviada de volta ao servidor (FR-004/FR-005).
 */
@SpringBootTest(
        classes = TranscriptFeedClientResilienceTest.FakeFeedServerConfig.class,
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class TranscriptFeedClientResilienceTest {

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
        FakeFeedServerConfig.MESSAGES_FROM_CLIENT.clear();
    }

    @Test
    void malformedAndUnknownSessionEventsAreDroppedWithoutBreakingIngestionOrSendingControlMessages()
            throws Exception {
        SessionRepository sessionRepository = new SessionRepository(MemoryHubTestSupport.newStore(tempDir));
        ConversationSession activeSession = sessionRepository.save(
                ConversationSession.create("Sessão ativa", "interview-technical", Map.of()));
        ConversationSession endedSession = sessionRepository.save(new ConversationSession(
                UUID.randomUUID(), "Sessão encerrada", "interview-technical", SessionStatus.ENDED,
                Instant.now(), Instant.now(), Instant.now(), Map.of()));

        TranscriptIngestionProperties properties =
                new TranscriptIngestionProperties("ws://localhost:" + port + "/ws/transcripts");
        client = new TranscriptFeedClient(properties, validator, mapper, sessionRepository, objectMapper);
        client.connect();
        waitUntil(() -> !FakeFeedServerConfig.SESSIONS.isEmpty(), "cliente não conectou ao feed fake");

        // 1) evento sem campo obrigatório (falta "device")
        Map<String, Object> malformed = new java.util.LinkedHashMap<>();
        malformed.put("type", "transcript.final.v2");
        malformed.put("sessionId", activeSession.id().toString());
        malformed.put("channelId", "mic-1");
        malformed.put("label", "Mic");
        malformed.put("sourceType", "microphone");
        malformed.put("text", "sem device");
        malformed.put("latencyMs", 100);
        malformed.put("occurredAt", Instant.parse("2026-07-22T12:00:00Z").toString());
        FakeFeedServerConfig.broadcast(objectMapper, malformed);

        // 2) evento válido para sessão inexistente
        FakeFeedServerConfig.broadcast(objectMapper, validEvent(UUID.randomUUID().toString(), "mic-1"));

        // 3) evento válido para sessão já encerrada
        FakeFeedServerConfig.broadcast(objectMapper, validEvent(endedSession.id().toString(), "mic-1"));

        // 4) evento válido para sessão ativa, enviado logo depois dos inválidos — deve ser processado
        FakeFeedServerConfig.broadcast(objectMapper, validEvent(activeSession.id().toString(), "mic-1"));

        waitUntil(() -> sessionRepository.events(activeSession.id()).size() == 1,
                "evento válido não foi processado após os eventos inválidos");

        List<HubEvent> activeEvents = sessionRepository.events(activeSession.id());
        assertThat(activeEvents).hasSize(1);
        assertThat(sessionRepository.events(endedSession.id())).isEmpty();
        assertThat(FakeFeedServerConfig.MESSAGES_FROM_CLIENT).isEmpty();
    }

    private static Map<String, Object> validEvent(String sessionId, String channelId) {
        Map<String, Object> event = new java.util.LinkedHashMap<>();
        event.put("type", "transcript.final.v2");
        event.put("sessionId", sessionId);
        event.put("channelId", channelId);
        event.put("label", "Mic");
        event.put("sourceType", "microphone");
        event.put("device", Map.of("index", 1, "name", "Mic", "endpointId", "{mic}"));
        event.put("text", "evento válido");
        event.put("latencyMs", 100);
        event.put("occurredAt", Instant.now().toString());
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
        static final List<String> MESSAGES_FROM_CLIENT = new CopyOnWriteArrayList<>();

        @Override
        public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
            registry.addHandler(new TextWebSocketHandler() {
                @Override
                public void afterConnectionEstablished(WebSocketSession session) {
                    SESSIONS.add(session);
                }

                @Override
                protected void handleTextMessage(WebSocketSession session, TextMessage message) {
                    MESSAGES_FROM_CLIENT.add(message.getPayload());
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
