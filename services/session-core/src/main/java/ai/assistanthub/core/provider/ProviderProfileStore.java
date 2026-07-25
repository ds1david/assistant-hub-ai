package ai.assistanthub.core.provider;

import org.springframework.stereotype.Component;
import org.yaml.snakeyaml.DumperOptions;
import org.yaml.snakeyaml.Yaml;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Map;

/**
 * Lê/escreve o perfil declarativo de provedores em {@code config/ai-providers.yaml} (caminho
 * configurável via {@link AiProviderHubProperties}). Escrita é atômica (arquivo temporário no
 * mesmo diretório + rename) — uma escrita interrompida nunca deixa o arquivo em estado
 * parcialmente corrompido (data-model.md § Persistência).
 */
@Component
public class ProviderProfileStore {

    private final Path profilePath;
    private final ProviderProfileValidator validator;
    private final Yaml yaml;

    public ProviderProfileStore(AiProviderHubProperties properties, ProviderProfileValidator validator) {
        this.profilePath = Path.of(properties.path()).toAbsolutePath();
        this.validator = validator;
        DumperOptions options = new DumperOptions();
        options.setDefaultFlowStyle(DumperOptions.FlowStyle.BLOCK);
        this.yaml = new Yaml(options);
    }

    /** Retorna um perfil vazio (sem provedores) se o arquivo ainda não existir. */
    public synchronized ProviderProfile load() {
        if (!Files.exists(profilePath)) {
            return ProviderProfile.empty();
        }
        try (InputStream in = Files.newInputStream(profilePath)) {
            Map<String, Object> raw = yaml.load(in);
            return raw == null ? ProviderProfile.empty() : validator.fromMap(raw);
        } catch (IOException e) {
            throw new UncheckedIOException("Falha ao ler o perfil de provedores em " + profilePath, e);
        }
    }

    /** @throws ProviderProfileValidationException se o perfil não passar em {@link ProviderProfileValidator}. */
    public synchronized void save(ProviderProfile profile) {
        validator.validate(profile);
        Path parent = profilePath.getParent();
        try {
            if (parent != null) {
                Files.createDirectories(parent);
            }
            Path tempFile = Files.createTempFile(parent, "ai-providers-", ".yaml.tmp");
            try (BufferedWriter writer = Files.newBufferedWriter(tempFile)) {
                yaml.dump(validator.toMap(profile), writer);
            }
            Files.move(tempFile, profilePath, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            throw new UncheckedIOException("Falha ao gravar o perfil de provedores em " + profilePath, e);
        }
    }
}
