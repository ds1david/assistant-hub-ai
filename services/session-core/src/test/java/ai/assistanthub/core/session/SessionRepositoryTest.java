package ai.assistanthub.core.session;

import ai.assistanthub.core.memory.MemoryHubTestSupport;
import ai.assistanthub.sdk.HubEvent;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SessionRepositoryTest {

    @TempDir
    Path tempDir;

    @Test
    void storesSessionAndEvents() {
        SessionRepository repository = new SessionRepository(MemoryHubTestSupport.newStore(tempDir));
        ConversationSession session = repository.save(
                ConversationSession.create("Teste", "interview-technical", Map.of()));

        repository.append(HubEvent.now(session.id(), "transcript.partial.v1", "system", Map.of("text", "pergunta")));

        assertEquals(1, repository.events(session.id()).size());
    }

    /**
     * FR-003 / SC-001 / SC-002 (SF-021 T021): vários canais do feed WebSocket despacham em
     * threads distintas; o cache em memória não pode perder nem corromper eventos sob corrida.
     */
    @Test
    void concurrentAppendsOnSameSessionPreserveAllEvents() throws Exception {
        SessionRepository repository = new SessionRepository(MemoryHubTestSupport.newStore(tempDir));
        ConversationSession session = repository.save(
                ConversationSession.create("Concorrente", "interview-technical", Map.of()));

        int threads = 8;
        int eventsPerThread = 50;
        int total = threads * eventsPerThread;
        ExecutorService pool = Executors.newFixedThreadPool(threads);
        CountDownLatch start = new CountDownLatch(1);
        AtomicInteger failures = new AtomicInteger();
        List<Future<?>> futures = new ArrayList<>();

        try {
            for (int t = 0; t < threads; t++) {
                final int threadIndex = t;
                futures.add(pool.submit(() -> {
                    try {
                        start.await(5, TimeUnit.SECONDS);
                        for (int i = 0; i < eventsPerThread; i++) {
                            String channelId = "channel-" + threadIndex;
                            HubEvent event = new HubEvent(
                                    UUID.randomUUID(),
                                    session.id(),
                                    "transcript.final.v2",
                                    "transcription-service",
                                    null,
                                    null,
                                    Map.of("text", "t" + threadIndex + "-" + i, "latencyMs", 1),
                                    Map.of(
                                            "channelId", channelId,
                                            "sourceType", "microphone",
                                            "label", channelId));
                            repository.append(event);
                        }
                    } catch (Exception e) {
                        failures.incrementAndGet();
                        throw new RuntimeException(e);
                    }
                }));
            }

            start.countDown();
            for (Future<?> future : futures) {
                future.get(30, TimeUnit.SECONDS);
            }
        } finally {
            pool.shutdownNow();
        }

        assertEquals(0, failures.get(), "worker threads must not throw");
        List<HubEvent> stored = repository.events(session.id());
        assertEquals(total, stored.size(), "all concurrent appends must be retained in memory");

        Set<UUID> ids = new HashSet<>();
        for (HubEvent event : stored) {
            assertTrue(ids.add(event.id()), "event ids must be unique");
        }
        assertEquals(total, ids.size());
    }
}
