package ai.assistanthub.core.memory;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.nio.file.Path;

/** Constrói um {@link SessionPersistenceStore} apontando para um arquivo SQLite isolado por teste. */
public final class MemoryHubTestSupport {

    private MemoryHubTestSupport() {
    }

    public static SessionPersistenceStore newStore(Path directory) {
        return new SessionPersistenceStore(newDataSource(directory), newObjectMapper());
    }

    public static MemoryHubDataSource newDataSource(Path directory) {
        MemoryHubProperties properties =
                new MemoryHubProperties(directory.resolve("memory-hub-test.db").toString(), null);
        return new MemoryHubDataSource(properties);
    }

    public static ObjectMapper newObjectMapper() {
        return new ObjectMapper().findAndRegisterModules();
    }
}
