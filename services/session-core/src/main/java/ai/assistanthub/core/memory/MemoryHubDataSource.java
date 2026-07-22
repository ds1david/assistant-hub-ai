package ai.assistanthub.core.memory;

import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;

/**
 * Abre o arquivo SQLite local do Memory Hub (issue #29 / R3) e garante o schema de
 * {@code sessions}/{@code session_events} antes de qualquer leitura/escrita — ver
 * specs/013-issue-29-memory-hub-persistence/data-model.md.
 */
@Component
public class MemoryHubDataSource {

    private final String jdbcUrl;

    public MemoryHubDataSource(MemoryHubProperties properties) {
        Path dbPath = Path.of(properties.path()).toAbsolutePath();
        Path parent = dbPath.getParent();
        if (parent != null) {
            try {
                Files.createDirectories(parent);
            } catch (IOException e) {
                throw new UncheckedIOException("Falha ao criar diretório do Memory Hub: " + parent, e);
            }
        }
        this.jdbcUrl = "jdbc:sqlite:" + dbPath;
        initializeSchema();
    }

    /** Abre uma conexão nova — SQLite é um arquivo local, abrir/fechar por operação é barato e simples. */
    public Connection newConnection() throws SQLException {
        return DriverManager.getConnection(jdbcUrl);
    }

    private void initializeSchema() {
        try (Connection connection = DriverManager.getConnection(jdbcUrl);
             Statement statement = connection.createStatement()) {
            statement.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        profile_id TEXT,
                        status TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        started_at INTEGER,
                        ended_at INTEGER,
                        metadata_json TEXT NOT NULL
                    )
                    """);
            statement.execute("""
                    CREATE TABLE IF NOT EXISTS session_events (
                        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT NOT NULL UNIQUE,
                        session_id TEXT NOT NULL REFERENCES sessions(id),
                        type TEXT NOT NULL,
                        source TEXT NOT NULL,
                        occurred_at INTEGER NOT NULL,
                        ingested_at INTEGER NOT NULL,
                        payload_json TEXT NOT NULL,
                        correlation_json TEXT NOT NULL
                    )
                    """);
            statement.execute(
                    "CREATE INDEX IF NOT EXISTS idx_session_events_session_id ON session_events(session_id, sequence)");
        } catch (SQLException e) {
            throw new IllegalStateException("Falha ao inicializar schema do Memory Hub em " + jdbcUrl, e);
        }
    }
}
