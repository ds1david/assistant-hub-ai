package ai.assistanthub.core.memory;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.time.Duration;

/**
 * Caminho do arquivo SQLite local e política de retenção do Memory Hub (issue #29 / R3).
 * Na ausência de {@code retention.max-age}/{@code retention.max-sessions}, a retenção é
 * indefinida — ver specs/013-issue-29-memory-hub-persistence/data-model.md.
 */
@ConfigurationProperties(prefix = "session-core.memory-hub")
public record MemoryHubProperties(String path, Retention retention) {

    private static final String DEFAULT_PATH = "data/session-core/memory-hub.db";

    public MemoryHubProperties {
        path = (path == null || path.isBlank()) ? DEFAULT_PATH : path;
        retention = retention == null ? new Retention(null, null) : retention;
    }

    public record Retention(Duration maxAge, Integer maxSessions) {
    }
}
