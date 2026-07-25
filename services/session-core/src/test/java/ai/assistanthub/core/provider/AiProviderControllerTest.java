package ai.assistanthub.core.provider;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.Optional;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Prova US2: os endpoints de {@link AiProviderController} respondem conforme
 * contracts/ai-provider-api.md, sem cliente desktop — construído diretamente (sem MockMvc),
 * mesmo estilo de teste direto já usado no restante do módulo.
 */
class AiProviderControllerTest {

    @TempDir
    Path tempDir;

    private AiProviderController controller;

    @BeforeEach
    void setUp() {
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        ProviderProfileStore store = ProviderTestSupport.newStore(tempDir, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(store);
        InvocationService invocationService =
                ProviderTestSupport.newInvocationService(registry, new OpenAiCompatibleAdapter(
                        ProviderTestSupport.newObjectMapper(), secretRef -> Optional.of("super-secret-value")));
        controller = new AiProviderController(registry, invocationService, secretRef -> Optional.of("super-secret-value"));
    }

    private Provider provider(String id) {
        return new Provider(
                id, "Real", ProviderType.OPENAI_COMPATIBLE, true, "http://fake.invalid",
                new ProviderAuthentication(AuthenticationMode.BEARER, "env:FAKE_VAR", null),
                new ProviderDefaults("gpt-test", null, null, null, 3000),
                Set.of("chat"));
    }

    @Test
    void createsAndListsProvider() {
        controller.create(provider("real-1"));

        assertThat(controller.list()).extracting(Provider::id).containsExactly("real-1");
    }

    @Test
    void rejectsCreateWhenIdAlreadyExists() {
        controller.create(provider("real-1"));

        assertThatThrownBy(() -> controller.create(provider("real-1")))
                .isInstanceOf(org.springframework.web.server.ResponseStatusException.class);
    }

    @Test
    void setsEnabledFlag() {
        controller.create(provider("real-1"));

        Provider updated = controller.setEnabled("real-1", new AiProviderController.SetEnabledRequest(false));

        assertThat(updated.enabled()).isFalse();
    }

    @Test
    void deletesProviderKeepingOthers() {
        controller.create(provider("real-1"));
        controller.create(provider("real-2"));

        controller.delete("real-1");

        assertThat(controller.list()).extracting(Provider::id).containsExactly("real-2");
    }

    @Test
    void rejectsDeletingTheOnlyRemainingProvider() {
        // contracts/ai-provider-profile.v1.schema.json exige providers.minItems=1 (P4, schema não
        // alterado) — remover o único provedor deixaria o perfil inválido, então a mutação é
        // rejeitada em vez de gravar um arquivo que violaria o próprio contrato.
        controller.create(provider("real-1"));

        assertThatThrownBy(() -> controller.delete("real-1"))
                .isInstanceOf(ProviderProfileValidationException.class);
    }

    @Test
    void secretPreviewNeverReturnsFullValue() {
        controller.create(provider("real-1"));

        SecretPreview preview = controller.secretPreview("real-1");

        assertThat(preview.maskedValue()).isNotNull().doesNotContain("super-secret-value");
    }
}
