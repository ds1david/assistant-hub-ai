package ai.assistanthub.core.provider;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Prova FR-015: uma mutação (criar/editar/habilitar-desabilitar) é refletida na próxima leitura
 * do registry sem reiniciar o processo.
 */
class ProviderRegistryHotReloadTest {

    @TempDir
    Path tempDir;

    private Provider provider(String id, boolean enabled) {
        return new Provider(
                id, "Real", ProviderType.OPENAI_COMPATIBLE, enabled, "http://fake.invalid",
                new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                new ProviderDefaults("gpt-test", null, null, null, 3000),
                Set.of("chat"));
    }

    @Test
    void createIsVisibleInTheSameRegistryInstanceImmediately() {
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        ProviderProfileStore store = ProviderTestSupport.newStore(tempDir, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(store);

        assertThat(registry.findById("real-1")).isEmpty();

        registry.save(provider("real-1", true));

        assertThat(registry.findById("real-1")).isPresent();
    }

    @Test
    void enabledToggleIsVisibleWithoutRestartingTheProcess() {
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        ProviderProfileStore store = ProviderTestSupport.newStore(tempDir, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(store);
        registry.save(provider("real-1", true));

        registry.setEnabled("real-1", false);

        assertThat(registry.findById("real-1")).get().extracting(Provider::enabled).isEqualTo(false);
    }

    @Test
    void mutationPersistsAcrossANewRegistryInstanceOverTheSameFile() {
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        ProviderProfileStore firstStore = ProviderTestSupport.newStore(tempDir, validator);
        ProviderRegistry firstRegistry = ProviderTestSupport.newRegistry(firstStore);
        firstRegistry.save(provider("real-1", true));

        // Simula um segundo processo/instância lendo o mesmo arquivo (não apenas cache em memória).
        ProviderProfileStore secondStore = ProviderTestSupport.newStore(tempDir, validator);
        ProviderRegistry secondRegistry = ProviderTestSupport.newRegistry(secondStore);

        assertThat(secondRegistry.findById("real-1")).isPresent();
    }
}
