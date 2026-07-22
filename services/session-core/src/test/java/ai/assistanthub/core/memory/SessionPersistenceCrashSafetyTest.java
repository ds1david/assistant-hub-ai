package ai.assistanthub.core.memory;

import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.sdk.HubEvent;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova FR-009 (edge case de US1): uma gravação de evento interrompida antes do commit não pode
 * corromper nem apagar os eventos já persistidos anteriormente. O "crash" é simulado abrindo uma
 * conexão JDBC crua, iniciando uma transação, inserindo um evento e fechando a conexão sem
 * commitar — o motor SQLite deve descartar a transação inacabada.
 */
class SessionPersistenceCrashSafetyTest {

    @TempDir
    Path tempDir;

    @Test
    void interruptedEventWriteDoesNotCorruptPreviouslyPersistedEvents() throws Exception {
        MemoryHubDataSource dataSource = MemoryHubTestSupport.newDataSource(tempDir);
        SessionPersistenceStore store = new SessionPersistenceStore(dataSource, MemoryHubTestSupport.newObjectMapper());

        ConversationSession session = ConversationSession.create("Crash", "interview-technical", Map.of());
        store.saveSession(session);

        HubEvent committed = HubEvent.now(session.id(), "transcript.final.v2", "transcription-service",
                Map.of("text", "evento gravado com sucesso"));
        store.appendEvent(committed);

        simulateCrashDuringEventWrite(dataSource, session.id());

        List<HubEvent> events = store.findEvents(session.id());
        assertThat(events).hasSize(1);
        assertThat(events.get(0).id()).isEqualTo(committed.id());
    }

    /** Abre uma transação, insere um evento, mas fecha a conexão sem commit — simula um crash. */
    private static void simulateCrashDuringEventWrite(MemoryHubDataSource dataSource, UUID sessionId)
            throws Exception {
        try (Connection rawConnection = dataSource.newConnection()) {
            rawConnection.setAutoCommit(false);
            try (PreparedStatement statement = rawConnection.prepareStatement("""
                    INSERT INTO session_events
                        (event_id, session_id, type, source, occurred_at, ingested_at, payload_json, correlation_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """)) {
                statement.setString(1, UUID.randomUUID().toString());
                statement.setString(2, sessionId.toString());
                statement.setString(3, "transcript.final.v2");
                statement.setString(4, "transcription-service");
                statement.setLong(5, Instant.now().toEpochMilli());
                statement.setLong(6, Instant.now().toEpochMilli());
                statement.setString(7, "{}");
                statement.setString(8, "{}");
                statement.executeUpdate();
            }
            // Sem commit — a conexão fecha em seguida (try-with-resources), simulando o processo
            // sendo encerrado a meio da transação.
        }
    }
}
