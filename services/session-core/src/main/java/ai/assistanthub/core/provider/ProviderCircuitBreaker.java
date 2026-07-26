package ai.assistanthub.core.provider;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Circuit breaker in-memory por {@code providerId} (026). Falhas consecutivas abrem o circuito;
 * após {@code openDurationMs} permite half-open com uma tentativa.
 */
@Component
public class ProviderCircuitBreaker {

    private final int failureThreshold;
    private final long openDurationMs;
    private final Clock clock;
    private final Map<String, Entry> entries = new ConcurrentHashMap<>();

    public ProviderCircuitBreaker(
            @Value("${session-core.ai-provider-hub.circuit-failure-threshold:5}") int failureThreshold,
            @Value("${session-core.ai-provider-hub.circuit-open-ms:30000}") long openDurationMs) {
        this(failureThreshold, openDurationMs, Clock.systemUTC());
    }

    /** Testes: clock injetável. */
    public ProviderCircuitBreaker(int failureThreshold, long openDurationMs, Clock clock) {
        this.failureThreshold = Math.max(1, failureThreshold);
        this.openDurationMs = Math.max(1L, openDurationMs);
        this.clock = clock;
    }

    /**
     * @return {@code true} se o provedor pode ser chamado agora (CLOSED ou transição para HALF_OPEN)
     */
    public boolean allowCall(String providerId) {
        Entry entry = entries.computeIfAbsent(providerId, ignored -> new Entry());
        synchronized (entry) {
            long now = clock.millis();
            if (entry.state == CircuitState.OPEN) {
                if (now >= entry.openUntilEpochMs) {
                    entry.state = CircuitState.HALF_OPEN;
                    return true;
                }
                return false;
            }
            return true; // CLOSED or HALF_OPEN
        }
    }

    public void recordSuccess(String providerId) {
        Entry entry = entries.computeIfAbsent(providerId, ignored -> new Entry());
        synchronized (entry) {
            entry.consecutiveFailures = 0;
            entry.state = CircuitState.CLOSED;
            entry.openUntilEpochMs = 0L;
        }
    }

    /**
     * Contabiliza falha de saúde do provedor. {@link InvocationErrorType#CAPABILITY_MISMATCH}
     * e {@link InvocationErrorType#CIRCUIT_OPEN} não devem ser passados aqui.
     */
    public void recordFailure(String providerId) {
        Entry entry = entries.computeIfAbsent(providerId, ignored -> new Entry());
        synchronized (entry) {
            entry.consecutiveFailures++;
            if (entry.state == CircuitState.HALF_OPEN
                    || entry.consecutiveFailures >= failureThreshold) {
                entry.state = CircuitState.OPEN;
                entry.openUntilEpochMs = clock.millis() + openDurationMs;
            }
        }
    }

    public CircuitState stateOf(String providerId) {
        Entry entry = entries.get(providerId);
        if (entry == null) {
            return CircuitState.CLOSED;
        }
        synchronized (entry) {
            long now = clock.millis();
            if (entry.state == CircuitState.OPEN && now >= entry.openUntilEpochMs) {
                return CircuitState.HALF_OPEN; // observável; allowCall faz a transição
            }
            return entry.state;
        }
    }

    public List<ProviderCircuitSnapshot> snapshots() {
        List<ProviderCircuitSnapshot> list = new ArrayList<>();
        for (Map.Entry<String, Entry> mapEntry : entries.entrySet()) {
            Entry entry = mapEntry.getValue();
            synchronized (entry) {
                CircuitState state = entry.state;
                Long openUntil = state == CircuitState.OPEN ? entry.openUntilEpochMs : null;
                list.add(new ProviderCircuitSnapshot(
                        mapEntry.getKey(), state, entry.consecutiveFailures, openUntil));
            }
        }
        return list;
    }

    private static final class Entry {
        CircuitState state = CircuitState.CLOSED;
        int consecutiveFailures;
        long openUntilEpochMs;
    }
}
