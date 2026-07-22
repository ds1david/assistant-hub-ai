package ai.assistanthub.core.memory;

import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.core.session.SessionStatus;
import ai.assistanthub.sdk.HubEvent;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Grava/lê {@link ConversationSession} e {@link HubEvent} no SQLite local do Memory Hub
 * (issue #29 / R3), por trás da mesma API já usada em memória por
 * {@code ai.assistanthub.core.session.SessionRepository} — ver
 * specs/013-issue-29-memory-hub-persistence/data-model.md. Cada gravação é uma transação
 * própria: uma interrupção a meio (crash) não deixa dado parcial visível (FR-009).
 */
@Component
public class SessionPersistenceStore {

    private static final String UPSERT_SESSION = """
            INSERT INTO sessions (id, title, profile_id, status, created_at, started_at, ended_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                profile_id = excluded.profile_id,
                status = excluded.status,
                created_at = excluded.created_at,
                started_at = excluded.started_at,
                ended_at = excluded.ended_at,
                metadata_json = excluded.metadata_json
            """;

    private static final String SELECT_SESSION_BY_ID = """
            SELECT id, title, profile_id, status, created_at, started_at, ended_at, metadata_json
            FROM sessions WHERE id = ?
            """;

    private static final String SELECT_ENDED_SESSIONS_BY_ENDED_AT = """
            SELECT id, title, profile_id, status, created_at, started_at, ended_at, metadata_json
            FROM sessions WHERE status = 'ENDED' ORDER BY ended_at ASC
            """;

    private static final String SELECT_ALL_SESSIONS = """
            SELECT id, title, profile_id, status, created_at, started_at, ended_at, metadata_json
            FROM sessions
            """;

    private static final String INSERT_EVENT = """
            INSERT INTO session_events
                (event_id, session_id, type, source, occurred_at, ingested_at, payload_json, correlation_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """;

    private static final String SELECT_EVENTS_BY_SESSION = """
            SELECT event_id, session_id, type, source, occurred_at, ingested_at, payload_json, correlation_json
            FROM session_events WHERE session_id = ? ORDER BY sequence ASC
            """;

    private static final String DELETE_EVENTS_BY_SESSION = "DELETE FROM session_events WHERE session_id = ?";
    private static final String DELETE_SESSION_BY_ID = "DELETE FROM sessions WHERE id = ?";

    private final MemoryHubDataSource dataSource;
    private final ObjectMapper objectMapper;

    public SessionPersistenceStore(MemoryHubDataSource dataSource, ObjectMapper objectMapper) {
        this.dataSource = dataSource;
        this.objectMapper = objectMapper;
    }

    public void saveSession(ConversationSession session) {
        try (Connection connection = dataSource.newConnection();
             PreparedStatement statement = connection.prepareStatement(UPSERT_SESSION)) {
            statement.setString(1, session.id().toString());
            statement.setString(2, session.title());
            statement.setString(3, session.profileId());
            statement.setString(4, session.status().name());
            statement.setLong(5, toEpochNanos(session.createdAt()));
            setNullableInstant(statement, 6, session.startedAt());
            setNullableInstant(statement, 7, session.endedAt());
            statement.setString(8, writeJson(session.metadata()));
            statement.executeUpdate();
        } catch (SQLException e) {
            throw new IllegalStateException("Falha ao persistir sessão " + session.id(), e);
        }
    }

    public Optional<ConversationSession> findSession(UUID id) {
        try (Connection connection = dataSource.newConnection();
             PreparedStatement statement = connection.prepareStatement(SELECT_SESSION_BY_ID)) {
            statement.setString(1, id.toString());
            try (ResultSet resultSet = statement.executeQuery()) {
                return resultSet.next() ? Optional.of(mapSession(resultSet)) : Optional.empty();
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Falha ao consultar sessão " + id, e);
        }
    }

    public List<ConversationSession> findAllSessions() {
        try (Connection connection = dataSource.newConnection();
             PreparedStatement statement = connection.prepareStatement(SELECT_ALL_SESSIONS);
             ResultSet resultSet = statement.executeQuery()) {
            List<ConversationSession> sessions = new ArrayList<>();
            while (resultSet.next()) {
                sessions.add(mapSession(resultSet));
            }
            return sessions;
        } catch (SQLException e) {
            throw new IllegalStateException("Falha ao listar sessões persistidas", e);
        }
    }

    /** Sessões `ENDED`, da mais antiga para a mais nova por `ended_at` — usadas por {@link RetentionPolicy}. */
    public List<ConversationSession> findEndedSessionsOrderedByEndedAt() {
        try (Connection connection = dataSource.newConnection();
             PreparedStatement statement = connection.prepareStatement(SELECT_ENDED_SESSIONS_BY_ENDED_AT);
             ResultSet resultSet = statement.executeQuery()) {
            List<ConversationSession> sessions = new ArrayList<>();
            while (resultSet.next()) {
                sessions.add(mapSession(resultSet));
            }
            return sessions;
        } catch (SQLException e) {
            throw new IllegalStateException("Falha ao listar sessões encerradas para retenção", e);
        }
    }

    public void appendEvent(HubEvent event) {
        try (Connection connection = dataSource.newConnection();
             PreparedStatement statement = connection.prepareStatement(INSERT_EVENT)) {
            statement.setString(1, event.id().toString());
            statement.setString(2, event.sessionId().toString());
            statement.setString(3, event.type());
            statement.setString(4, event.source());
            statement.setLong(5, toEpochNanos(event.occurredAt()));
            statement.setLong(6, toEpochNanos(event.ingestedAt()));
            statement.setString(7, writeJson(event.payload()));
            statement.setString(8, writeJson(event.correlation()));
            statement.executeUpdate();
        } catch (SQLException e) {
            throw new IllegalStateException("Falha ao persistir evento " + event.id(), e);
        }
    }

    public List<HubEvent> findEvents(UUID sessionId) {
        try (Connection connection = dataSource.newConnection();
             PreparedStatement statement = connection.prepareStatement(SELECT_EVENTS_BY_SESSION)) {
            statement.setString(1, sessionId.toString());
            try (ResultSet resultSet = statement.executeQuery()) {
                List<HubEvent> events = new ArrayList<>();
                while (resultSet.next()) {
                    events.add(mapEvent(resultSet));
                }
                return events;
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Falha ao consultar eventos da sessão " + sessionId, e);
        }
    }

    /** Remove a sessão e todos os seus eventos em uma única transação (expurgo de retenção). */
    public void deleteSession(UUID id) {
        try (Connection connection = dataSource.newConnection()) {
            connection.setAutoCommit(false);
            try (PreparedStatement deleteEvents = connection.prepareStatement(DELETE_EVENTS_BY_SESSION);
                 PreparedStatement deleteSession = connection.prepareStatement(DELETE_SESSION_BY_ID)) {
                deleteEvents.setString(1, id.toString());
                deleteEvents.executeUpdate();
                deleteSession.setString(1, id.toString());
                deleteSession.executeUpdate();
                connection.commit();
            } catch (SQLException e) {
                connection.rollback();
                throw e;
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Falha ao expurgar sessão " + id, e);
        }
    }

    private ConversationSession mapSession(ResultSet resultSet) throws SQLException {
        return new ConversationSession(
                UUID.fromString(resultSet.getString("id")),
                resultSet.getString("title"),
                resultSet.getString("profile_id"),
                SessionStatus.valueOf(resultSet.getString("status")),
                fromEpochNanos(resultSet.getLong("created_at")),
                getNullableInstant(resultSet, "started_at"),
                getNullableInstant(resultSet, "ended_at"),
                readJsonMap(resultSet.getString("metadata_json")));
    }

    private HubEvent mapEvent(ResultSet resultSet) throws SQLException {
        return new HubEvent(
                UUID.fromString(resultSet.getString("event_id")),
                UUID.fromString(resultSet.getString("session_id")),
                resultSet.getString("type"),
                resultSet.getString("source"),
                fromEpochNanos(resultSet.getLong("occurred_at")),
                fromEpochNanos(resultSet.getLong("ingested_at")),
                readJsonMap(resultSet.getString("payload_json")),
                readJsonStringMap(resultSet.getString("correlation_json")));
    }

    private void setNullableInstant(PreparedStatement statement, int index, Instant value) throws SQLException {
        if (value == null) {
            statement.setNull(index, java.sql.Types.INTEGER);
        } else {
            statement.setLong(index, toEpochNanos(value));
        }
    }

    private Instant getNullableInstant(ResultSet resultSet, String column) throws SQLException {
        long nanos = resultSet.getLong(column);
        return resultSet.wasNull() ? null : fromEpochNanos(nanos);
    }

    /**
     * Nanossegundos desde a época — preserva a precisão total de {@link Instant#now()} (que no
     * Linux tem resolução de nanossegundos); {@code toEpochMilli()} truncaria e quebraria
     * {@code equals()} ao reidratar a partir do SQLite.
     */
    private static long toEpochNanos(Instant value) {
        return value.getEpochSecond() * 1_000_000_000L + value.getNano();
    }

    private static Instant fromEpochNanos(long epochNanos) {
        long seconds = Math.floorDiv(epochNanos, 1_000_000_000L);
        long nanoAdjustment = Math.floorMod(epochNanos, 1_000_000_000L);
        return Instant.ofEpochSecond(seconds, nanoAdjustment);
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            throw new IllegalStateException("Falha ao serializar valor do Memory Hub para JSON", e);
        }
    }

    private Map<String, Object> readJsonMap(String json) {
        try {
            return objectMapper.readValue(json, new TypeReference<LinkedHashMap<String, Object>>() {
            });
        } catch (Exception e) {
            throw new IllegalStateException("Falha ao desserializar JSON do Memory Hub: " + json, e);
        }
    }

    private Map<String, String> readJsonStringMap(String json) {
        try {
            return objectMapper.readValue(json, new TypeReference<LinkedHashMap<String, String>>() {
            });
        } catch (Exception e) {
            throw new IllegalStateException("Falha ao desserializar JSON do Memory Hub: " + json, e);
        }
    }
}
