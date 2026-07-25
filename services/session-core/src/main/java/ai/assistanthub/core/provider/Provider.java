package ai.assistanthub.core.provider;

import java.util.Set;

/**
 * Espelha {@code $defs/provider} de contracts/ai-provider-profile.v1.schema.json — fonte única
 * de verdade do formato (P4); esta classe não duplica regras de validação (ver
 * {@link ProviderProfileValidator}).
 */
public record Provider(
        String id,
        String label,
        ProviderType type,
        boolean enabled,
        String baseUrl,
        ProviderAuthentication authentication,
        ProviderDefaults defaults,
        Set<String> capabilities) {

    public Provider {
        capabilities = Set.copyOf(capabilities == null ? Set.of() : capabilities);
    }
}
