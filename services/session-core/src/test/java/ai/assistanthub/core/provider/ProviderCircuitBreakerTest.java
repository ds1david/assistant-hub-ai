package ai.assistanthub.core.provider;

import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;

class ProviderCircuitBreakerTest {

    @Test
    void opensAfterConsecutiveFailuresAndBlocksCalls() {
        MutableClock clock = new MutableClock(1_000_000L);
        ProviderCircuitBreaker breaker = new ProviderCircuitBreaker(3, 10_000L, clock);

        assertThat(breaker.allowCall("p1")).isTrue();
        breaker.recordFailure("p1");
        breaker.recordFailure("p1");
        assertThat(breaker.stateOf("p1")).isEqualTo(CircuitState.CLOSED);
        breaker.recordFailure("p1");
        assertThat(breaker.stateOf("p1")).isEqualTo(CircuitState.OPEN);
        assertThat(breaker.allowCall("p1")).isFalse();
    }

    @Test
    void halfOpenAfterOpenDurationThenSuccessCloses() {
        MutableClock clock = new MutableClock(0L);
        ProviderCircuitBreaker breaker = new ProviderCircuitBreaker(2, 5_000L, clock);

        breaker.recordFailure("p1");
        breaker.recordFailure("p1");
        assertThat(breaker.allowCall("p1")).isFalse();

        clock.advance(5_001L);
        assertThat(breaker.allowCall("p1")).isTrue();
        assertThat(breaker.stateOf("p1")).isEqualTo(CircuitState.HALF_OPEN);

        breaker.recordSuccess("p1");
        assertThat(breaker.stateOf("p1")).isEqualTo(CircuitState.CLOSED);
        assertThat(breaker.allowCall("p1")).isTrue();
    }

    @Test
    void halfOpenFailureReopens() {
        MutableClock clock = new MutableClock(0L);
        ProviderCircuitBreaker breaker = new ProviderCircuitBreaker(1, 1_000L, clock);

        breaker.recordFailure("p1");
        assertThat(breaker.allowCall("p1")).isFalse();
        clock.advance(1_001L);
        assertThat(breaker.allowCall("p1")).isTrue();
        breaker.recordFailure("p1");
        assertThat(breaker.stateOf("p1")).isEqualTo(CircuitState.OPEN);
        assertThat(breaker.allowCall("p1")).isFalse();
    }

    static final class MutableClock extends Clock {
        private long millis;

        MutableClock(long millis) {
            this.millis = millis;
        }

        void advance(long delta) {
            millis += delta;
        }

        @Override
        public ZoneOffset getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(java.time.ZoneId zone) {
            return this;
        }

        @Override
        public Instant instant() {
            return Instant.ofEpochMilli(millis);
        }

        @Override
        public long millis() {
            return millis;
        }
    }
}
