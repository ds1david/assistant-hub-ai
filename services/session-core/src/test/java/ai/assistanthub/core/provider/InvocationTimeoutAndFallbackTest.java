package ai.assistanthub.core.provider;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova US4 (FR-003/FR-005): timeout e rate limit acionam fallback quando configurado; rota sem
 * fallback retorna erro tipado; provedor {@code enabled: false} nunca é invocado — o
 * session-core nunca propaga uma exceção não tratada para o chamador.
 */
class InvocationTimeoutAndFallbackTest {

    @TempDir
    Path tempDir;

    private Provider provider(String id, boolean enabled, String baseUrl) {
        return new Provider(
                id, "Fake " + id, ProviderType.FAKE, enabled, baseUrl,
                new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                new ProviderDefaults("fake-model", null, null, null, 150), // timeout curto — teste rápido
                Set.of("chat"));
    }

    private InvocationService serviceFor(ProviderProfile profile) {
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        ProviderTestSupport.writeRawProfile(tempDir, profile, validator);
        ProviderProfileStore store = ProviderTestSupport.newStore(tempDir, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(store);
        return ProviderTestSupport.newInvocationService(registry, new FakeProviderAdapter());
    }

    @Test
    void timeoutTriggersFallbackWhenConfigured() {
        ProviderProfile profile = new ProviderProfile(
                1,
                List.of(provider("primary", true, "fake://hang"), provider("fallback", true, "fake://success")),
                Map.of("chat-route", new ProviderRoute("primary", List.of("fallback"))));

        InvocationResult result = serviceFor(profile).invoke(
                "chat-route", new InvocationRequest("session-1", null, "chat", "ola"));

        assertThat(result.success()).isTrue();
        assertThat(result.providerId()).isEqualTo("fallback");
    }

    @Test
    void timeoutWithoutFallbackReturnsTypedTimeoutError() {
        ProviderProfile profile = new ProviderProfile(
                1,
                List.of(provider("primary", true, "fake://hang")),
                Map.of("chat-route", new ProviderRoute("primary", List.of())));

        InvocationResult result = serviceFor(profile).invoke(
                "chat-route", new InvocationRequest("session-1", null, "chat", "ola"));

        assertThat(result.success()).isFalse();
        assertThat(result.errorType()).isEqualTo(InvocationErrorType.TIMEOUT);
    }

    @Test
    void rateLimitTriggersFallbackWhenConfigured() {
        ProviderProfile profile = new ProviderProfile(
                1,
                List.of(
                        provider("primary", true, "fake://rate-limit"),
                        provider("fallback", true, "fake://success")),
                Map.of("chat-route", new ProviderRoute("primary", List.of("fallback"))));

        InvocationResult result = serviceFor(profile).invoke(
                "chat-route", new InvocationRequest("session-1", null, "chat", "ola"));

        assertThat(result.success()).isTrue();
        assertThat(result.providerId()).isEqualTo("fallback");
    }

    @Test
    void disabledProviderIsNeverInvokedEvenAsPrimary() {
        ProviderProfile profile = new ProviderProfile(
                1,
                List.of(
                        provider("primary", false, "fake://success"), // enabled=false
                        provider("fallback", true, "fake://success")),
                Map.of("chat-route", new ProviderRoute("primary", List.of("fallback"))));

        InvocationResult result = serviceFor(profile).invoke(
                "chat-route", new InvocationRequest("session-1", null, "chat", "ola"));

        assertThat(result.success()).isTrue();
        assertThat(result.providerId()).isEqualTo("fallback");
    }

    @Test
    void routeWithOnlyDisabledCandidatesFailsExplicitlyWithoutThrowing() {
        ProviderProfile profile = new ProviderProfile(
                1,
                List.of(provider("primary", false, "fake://success")),
                Map.of("chat-route", new ProviderRoute("primary", List.of())));

        InvocationResult result = serviceFor(profile).invoke(
                "chat-route", new InvocationRequest("session-1", null, "chat", "ola"));

        assertThat(result.success()).isFalse();
        assertThat(result.message()).contains("nenhum provedor habilitado");
    }
}
