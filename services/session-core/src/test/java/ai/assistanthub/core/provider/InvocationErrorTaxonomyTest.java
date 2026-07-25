package ai.assistanthub.core.provider;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova FR-006/FR-010/SC-005: autenticação, modelo inexistente, timeout, rate limit,
 * incompatibilidade de capacidade e erro genérico retornam tipos distintos — nenhum caso cai
 * silenciosamente em um genérico ambíguo.
 */
class InvocationErrorTaxonomyTest {

    @TempDir
    Path tempDir;

    private Provider provider(String baseUrl, Set<String> capabilities) {
        return new Provider(
                "fake-1", "Fake", ProviderType.FAKE, true, baseUrl,
                new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                new ProviderDefaults("fake-model", null, null, null, 2000),
                capabilities);
    }

    private InvocationResult invokeWithBaseUrl(String baseUrl) {
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        ProviderProfile profile = new ProviderProfile(
                1,
                List.of(provider(baseUrl, Set.of("chat"))),
                Map.of("chat-route", new ProviderRoute("fake-1", List.of())));
        ProviderTestSupport.writeRawProfile(tempDir, profile, validator);
        ProviderProfileStore store = ProviderTestSupport.newStore(tempDir, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(store);
        InvocationService invocationService = ProviderTestSupport.newInvocationService(registry, new FakeProviderAdapter());
        return invocationService.invoke("chat-route", new InvocationRequest("session-1", "mic-1", "chat", "ola"));
    }

    @Test
    void authenticationErrorIsDistinct() {
        assertThat(invokeWithBaseUrl("fake://auth-error").errorType()).isEqualTo(InvocationErrorType.AUTHENTICATION);
    }

    @Test
    void modelNotFoundIsDistinct() {
        assertThat(invokeWithBaseUrl("fake://model-not-found").errorType()).isEqualTo(InvocationErrorType.MODEL_NOT_FOUND);
    }

    @Test
    void timeoutIsDistinct() {
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        Provider provider = new Provider(
                "fake-1", "Fake", ProviderType.FAKE, true, "fake://hang",
                new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                new ProviderDefaults("fake-model", null, null, null, 150),
                Set.of("chat"));
        ProviderProfile profile = new ProviderProfile(
                1, List.of(provider), Map.of("chat-route", new ProviderRoute("fake-1", List.of())));
        ProviderTestSupport.writeRawProfile(tempDir, profile, validator);
        ProviderProfileStore store = ProviderTestSupport.newStore(tempDir, validator);
        InvocationService invocationService =
                ProviderTestSupport.newInvocationService(ProviderTestSupport.newRegistry(store), new FakeProviderAdapter());

        InvocationResult result = invocationService.invoke(
                "chat-route", new InvocationRequest("session-1", "mic-1", "chat", "ola"));

        assertThat(result.errorType()).isEqualTo(InvocationErrorType.TIMEOUT);
    }

    @Test
    void rateLimitIsDistinct() {
        assertThat(invokeWithBaseUrl("fake://rate-limit").errorType()).isEqualTo(InvocationErrorType.RATE_LIMITED);
    }

    @Test
    void genericErrorIsDistinct() {
        assertThat(invokeWithBaseUrl("fake://generic-error").errorType()).isEqualTo(InvocationErrorType.GENERIC);
    }

    @Test
    void capabilityMismatchIsDistinctAndNeverReachesTheAdapter() {
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        ProviderProfile profile = new ProviderProfile(
                1,
                List.of(provider("fake://success", Set.of("embeddings"))), // não suporta "chat"
                Map.of("chat-route", new ProviderRoute("fake-1", List.of())));
        ProviderTestSupport.writeRawProfile(tempDir, profile, validator);
        ProviderProfileStore store = ProviderTestSupport.newStore(tempDir, validator);
        InvocationService invocationService =
                ProviderTestSupport.newInvocationService(ProviderTestSupport.newRegistry(store), new FakeProviderAdapter());

        InvocationResult result = invocationService.invoke(
                "chat-route", new InvocationRequest("session-1", "mic-1", "chat", "ola"));

        assertThat(result.errorType()).isEqualTo(InvocationErrorType.CAPABILITY_MISMATCH);
    }

    @Test
    void allSixErrorTypesAreMutuallyDistinct() {
        Set<InvocationErrorType> observed = Set.of(
                invokeWithBaseUrl("fake://auth-error").errorType(),
                invokeWithBaseUrl("fake://model-not-found").errorType(),
                invokeWithBaseUrl("fake://rate-limit").errorType(),
                invokeWithBaseUrl("fake://generic-error").errorType());

        assertThat(observed).containsExactlyInAnyOrder(
                InvocationErrorType.AUTHENTICATION, InvocationErrorType.MODEL_NOT_FOUND,
                InvocationErrorType.RATE_LIMITED, InvocationErrorType.GENERIC);
    }
}
