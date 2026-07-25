package ai.assistanthub.core.provider;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.yaml.snakeyaml.Yaml;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/**
 * Constrói o trio {@link ProviderProfileStore}/{@link ProviderRegistry}/{@link InvocationService}
 * apontando para um perfil isolado por teste (mesmo padrão de {@code MemoryHubTestSupport}).
 */
public final class ProviderTestSupport {

    private ProviderTestSupport() {
    }

    public static ObjectMapper newObjectMapper() {
        return new ObjectMapper().findAndRegisterModules();
    }

    public static ProviderProfileValidator newValidator() {
        return new ProviderProfileValidator(newObjectMapper());
    }

    public static ProviderProfileStore newStore(Path directory, ProviderProfileValidator validator) {
        AiProviderHubProperties properties =
                new AiProviderHubProperties(directory.resolve("ai-providers-test.yaml").toString());
        return new ProviderProfileStore(properties, validator);
    }

    public static ProviderRegistry newRegistry(ProviderProfileStore store) {
        return new ProviderRegistry(store);
    }

    public static InvocationService newInvocationService(
            ProviderRegistry registry, ProviderAdapterFactory.TypedProviderAdapter... adapters) {
        return new InvocationService(registry, new ProviderAdapterFactory(List.of(adapters)));
    }

    /**
     * Grava o perfil direto no arquivo, sem passar por {@link ProviderProfileStore#save} — usado
     * para perfis de teste com {@link ProviderType#FAKE}, que {@link ProviderProfileValidator}
     * rejeitaria (não está no schema v1) se fosse validado normalmente.
     */
    public static void writeRawProfile(Path directory, ProviderProfile profile, ProviderProfileValidator validator) {
        Path file = directory.resolve("ai-providers-test.yaml");
        try {
            Files.createDirectories(file.getParent());
            try (BufferedWriter writer = Files.newBufferedWriter(file)) {
                new Yaml().dump(validator.toMap(profile), writer);
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
