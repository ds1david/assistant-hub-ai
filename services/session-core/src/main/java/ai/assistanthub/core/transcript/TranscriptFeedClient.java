package ai.assistanthub.core.transcript;

import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.core.session.SessionRepository;
import ai.assistanthub.core.session.SessionStatus;
import ai.assistanthub.sdk.HubEvent;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.ValidationMessage;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.client.WebSocketClient;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.util.Set;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Cliente WebSocket que consome o feed global {@code /ws/transcripts} do transcription-service
 * (fronteira: transcrição publica, session-core consome — FR-001/FR-005). Nunca escreve de volta
 * na sessão remota; a única ação é ler, validar, mapear e anexar à sessão local correspondente.
 */
@Component
public class TranscriptFeedClient extends TextWebSocketHandler {

    private static final Logger LOGGER = LoggerFactory.getLogger(TranscriptFeedClient.class);
    private static final long INITIAL_BACKOFF_SECONDS = 1;
    private static final long MAX_BACKOFF_SECONDS = 30;

    private final TranscriptIngestionProperties properties;
    private final TranscriptEventValidator validator;
    private final TranscriptEventMapper mapper;
    private final SessionRepository sessionRepository;
    private final ObjectMapper objectMapper;
    private final WebSocketClient webSocketClient;
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor(runnable -> {
        Thread thread = new Thread(runnable, "transcript-feed-client");
        thread.setDaemon(true);
        return thread;
    });
    private final AtomicBoolean stopped = new AtomicBoolean(true);
    private final AtomicLong backoffSeconds = new AtomicLong(INITIAL_BACKOFF_SECONDS);

    @org.springframework.beans.factory.annotation.Autowired
    public TranscriptFeedClient(
            TranscriptIngestionProperties properties,
            TranscriptEventValidator validator,
            TranscriptEventMapper mapper,
            SessionRepository sessionRepository,
            ObjectMapper objectMapper) {
        this(properties, validator, mapper, sessionRepository, objectMapper, new StandardWebSocketClient());
    }

    TranscriptFeedClient(
            TranscriptIngestionProperties properties,
            TranscriptEventValidator validator,
            TranscriptEventMapper mapper,
            SessionRepository sessionRepository,
            ObjectMapper objectMapper,
            WebSocketClient webSocketClient) {
        this.properties = properties;
        this.validator = validator;
        this.mapper = mapper;
        this.sessionRepository = sessionRepository;
        this.objectMapper = objectMapper;
        this.webSocketClient = webSocketClient;
    }

    /** Inicia a conexão (e as tentativas de reconexão com backoff); não bloqueia a chamada. */
    public void connect() {
        stopped.set(false);
        backoffSeconds.set(INITIAL_BACKOFF_SECONDS);
        attemptConnect();
    }

    /** Para definitivamente o cliente — nenhuma nova tentativa de conexão é agendada depois disso. */
    public void close() {
        stopped.set(true);
        scheduler.shutdownNow();
    }

    /**
     * A ingestão começa junto com o session-core, mas só depois do contexto estar totalmente de
     * pé (ApplicationReadyEvent) — uma falha ao conectar aqui nunca impede a subida do serviço,
     * pois {@link #attemptConnect()} apenas loga e agenda nova tentativa (FR-005: consumidor
     * passivo, nunca uma dependência rígida de inicialização).
     */
    @EventListener(ApplicationReadyEvent.class)
    public void onApplicationReady() {
        connect();
    }

    @PreDestroy
    public void onShutdown() {
        close();
    }

    private void attemptConnect() {
        if (stopped.get()) {
            return;
        }
        webSocketClient.execute(this, properties.feedUrl()).whenComplete((session, error) -> {
            if (error != null) {
                LOGGER.warn("Falha ao conectar ao feed de transcrição em {}: {}", properties.feedUrl(),
                        error.toString());
                scheduleReconnect();
            } else {
                backoffSeconds.set(INITIAL_BACKOFF_SECONDS);
            }
        });
    }

    private void scheduleReconnect() {
        if (stopped.get()) {
            return;
        }
        long delay = backoffSeconds.getAndUpdate(current -> Math.min(current * 2, MAX_BACKOFF_SECONDS));
        scheduler.schedule(this::attemptConnect, delay, TimeUnit.SECONDS);
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        LOGGER.info("Conectado ao feed de transcrição em {}", properties.feedUrl());
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        JsonNode node;
        try {
            node = objectMapper.readTree(message.getPayload());
        } catch (Exception e) {
            LOGGER.warn("Evento de transcrição descartado — corpo não é JSON válido: {}", e.toString());
            return;
        }

        Set<ValidationMessage> violations = validator.validate(node);
        if (!violations.isEmpty()) {
            LOGGER.warn("Evento de transcrição rejeitado por não conformidade ao contrato v2: {}", violations);
            return;
        }

        TranscriptEventV2 event;
        try {
            event = objectMapper.treeToValue(node, TranscriptEventV2.class);
        } catch (Exception e) {
            LOGGER.warn("Evento de transcrição válido pelo schema, mas falhou ao desserializar: {}", e.toString());
            return;
        }

        UUID sessionId;
        try {
            sessionId = UUID.fromString(event.sessionId());
        } catch (IllegalArgumentException e) {
            LOGGER.warn(
                    "Evento de transcrição descartado — sessionId '{}' não corresponde a nenhuma sessão conhecida (type={}, channelId={})",
                    event.sessionId(), event.type(), event.channelId());
            return;
        }

        ConversationSession conversationSession = sessionRepository.findById(sessionId).orElse(null);
        if (conversationSession == null || conversationSession.status() == SessionStatus.ENDED) {
            LOGGER.warn(
                    "Evento de transcrição descartado — sessão '{}' desconhecida ou encerrada (type={}, channelId={})",
                    event.sessionId(), event.type(), event.channelId());
            return;
        }

        HubEvent hubEvent = mapper.toHubEvent(event, sessionId);
        sessionRepository.append(hubEvent);
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) {
        LOGGER.warn("Erro de transporte no feed de transcrição: {}", exception.toString());
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus closeStatus) {
        LOGGER.info("Conexão com o feed de transcrição encerrada ({}) — agendando reconexão", closeStatus);
        scheduleReconnect();
    }
}
