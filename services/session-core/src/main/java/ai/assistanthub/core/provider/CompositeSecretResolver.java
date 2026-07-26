package ai.assistanthub.core.provider;

import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Component;

import java.util.Optional;

/**
 * Resolve order: (1) request {@link SecretOverrideContext} for {@code os:} from desktop,
 * (2) {@link EnvSecretResolver} for {@code env:VAR}. Never logs values (#64 / P9).
 */
@Component
@Primary
public class CompositeSecretResolver implements SecretResolver {

    private final EnvSecretResolver envSecretResolver;

    public CompositeSecretResolver(EnvSecretResolver envSecretResolver) {
        this.envSecretResolver = envSecretResolver;
    }

    @Override
    public Optional<String> resolve(String secretRef) {
        Optional<String> override = SecretOverrideContext.resolve(secretRef);
        if (override.isPresent()) {
            return override;
        }
        return envSecretResolver.resolve(secretRef);
    }
}
