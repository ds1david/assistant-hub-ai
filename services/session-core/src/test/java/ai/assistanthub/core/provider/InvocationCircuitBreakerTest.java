package ai.assistanthub.core.provider;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.time.Clock;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 026 US1: primary com falhas repetidas abre breaker e deixa de ser chamado; fallback atende.
 */
class InvocationCircuitBreakerTest {

    @TempDir
    Path tempDir;

    private Provider provider(String id, String baseUrl) {
        return new Provider(
                id, "Fake " + id, ProviderType.FAKE, true, baseUrl,
                new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                new ProviderDefaults("fake-model", null, null, null, 500),
                Set.of("chat"));
    }

    @Test
    void openBreakerSkipsPrimaryAndUsesFallback() {
        ProviderCircuitBreaker breaker = new ProviderCircuitBreaker(2, 60_000L, Clock.systemUTC());
        ProviderProfile profile = new ProviderProfile(
                1,
                List.of(
                        provider("primary", "fake://generic-error"),
                        provider("fallback", "fake://success")),
                Map.of("chat-route", new ProviderRoute("primary", List.of("fallback"))));

        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        ProviderTestSupport.writeRawProfile(tempDir, profile, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(ProviderTestSupport.newStore(tempDir, validator));
        InvocationService service = ProviderTestSupport.newInvocationService(
                registry, ProviderTestSupport.newSessionRepository(tempDir), breaker, new FakeProviderAdapter());

        // 2 falhas no primary → OPEN
        assertThat(service.invoke("chat-route", new InvocationRequest("s1", null, "chat", "a")).providerId())
                .isEqualTo("fallback");
        assertThat(service.invoke("chat-route", new InvocationRequest("s1", null, "chat", "b")).providerId())
                .isEqualTo("fallback");
        assertThat(breaker.stateOf("primary")).isEqualTo(CircuitState.OPEN);

        CountingAdapter counting = new CountingAdapter(new FakeProviderAdapter());
        InvocationService service2 = ProviderTestSupport.newInvocationService(
                registry, ProviderTestSupport.newSessionRepository(tempDir), breaker, counting);

        InvocationResult third = service2.invoke("chat-route", new InvocationRequest("s1", null, "chat", "c"));
        assertThat(third.success()).isTrue();
        assertThat(third.providerId()).isEqualTo("fallback");
        assertThat(counting.invocationsFor("primary")).isZero();
        assertThat(counting.invocationsFor("fallback")).isEqualTo(1);
    }

    /** Conta invokes por providerId. */
    static final class CountingAdapter implements ProviderAdapterFactory.TypedProviderAdapter {
        private final FakeProviderAdapter delegate;
        private final AtomicInteger primary = new AtomicInteger();
        private final AtomicInteger fallback = new AtomicInteger();
        private final AtomicInteger other = new AtomicInteger();

        CountingAdapter(FakeProviderAdapter delegate) {
            this.delegate = delegate;
        }

        int invocationsFor(String id) {
            return switch (id) {
                case "primary" -> primary.get();
                case "fallback" -> fallback.get();
                default -> other.get();
            };
        }

        @Override
        public ProviderType supportedType() {
            return ProviderType.FAKE;
        }

        @Override
        public ConnectionTestResult testConnection(Provider provider) {
            return delegate.testConnection(provider);
        }

        @Override
        public AdapterOutcome invoke(Provider provider, InvocationRequest request) {
            switch (provider.id()) {
                case "primary" -> primary.incrementAndGet();
                case "fallback" -> fallback.incrementAndGet();
                default -> other.incrementAndGet();
            }
            return delegate.invoke(provider, request);
        }
    }
}
