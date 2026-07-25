package ai.assistanthub.core.provider;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova US1: um perfil com um provedor fake habilitado é invocado para a capacidade {@code chat}
 * no contexto de uma sessão, sem rede e sem qualquer alteração de código do core (FR-001/FR-004/FR-009).
 */
class FakeProviderInvocationTest {

    @TempDir
    Path tempDir;

    private Provider fakeProvider(String id, String baseUrl) {
        return new Provider(
                id, "Fake", ProviderType.FAKE, true, baseUrl,
                new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                new ProviderDefaults("fake-model", null, null, null, 2000),
                Set.of("chat"));
    }

    @Test
    void invokesFakeProviderForChatCapability() {
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        ProviderProfile profile = new ProviderProfile(
                1,
                List.of(fakeProvider("fake-1", "fake://success")),
                Map.of("chat-route", new ProviderRoute("fake-1", List.of())));
        ProviderTestSupport.writeRawProfile(tempDir, profile, validator);

        ProviderProfileStore store = ProviderTestSupport.newStore(tempDir, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(store);
        InvocationService invocationService = ProviderTestSupport.newInvocationService(registry, new FakeProviderAdapter());

        InvocationResult result = invocationService.invoke(
                "chat-route", new InvocationRequest("session-1", null, "chat", "ola"));

        assertThat(result.success()).isTrue();
        assertThat(result.providerId()).isEqualTo("fake-1");
        assertThat(result.model()).isEqualTo("fake-model");
        assertThat(result.output()).contains("ola");
        assertThat(result.errorType()).isNull();
    }

    @Test
    void rejectsCapabilityNotSupportedByProvider() {
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        Provider provider = new Provider(
                "fake-1", "Fake", ProviderType.FAKE, true, "fake://success",
                new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                new ProviderDefaults("fake-model", null, null, null, 2000),
                Set.of("embeddings")); // não suporta "chat"
        ProviderProfile profile = new ProviderProfile(
                1, List.of(provider), Map.of("chat-route", new ProviderRoute("fake-1", List.of())));
        ProviderTestSupport.writeRawProfile(tempDir, profile, validator);

        ProviderProfileStore store = ProviderTestSupport.newStore(tempDir, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(store);
        InvocationService invocationService = ProviderTestSupport.newInvocationService(registry, new FakeProviderAdapter());

        InvocationResult result = invocationService.invoke(
                "chat-route", new InvocationRequest("session-1", null, "chat", "ola"));

        assertThat(result.success()).isFalse();
        assertThat(result.errorType()).isEqualTo(InvocationErrorType.CAPABILITY_MISMATCH);
    }
}
