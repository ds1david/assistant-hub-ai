package ai.assistanthub.core.provider;

import java.util.List;
import java.util.Map;

/**
 * Documento raiz de {@code contracts/ai-provider-profile.v1.schema.json} — {@code version} é
 * sempre {@code 1} nesta fatia (FR-002).
 */
public record ProviderProfile(int version, List<Provider> providers, Map<String, ProviderRoute> routes) {

    public ProviderProfile {
        providers = List.copyOf(providers == null ? List.of() : providers);
        routes = Map.copyOf(routes == null ? Map.of() : routes);
    }

    public static ProviderProfile empty() {
        return new ProviderProfile(1, List.of(), Map.of());
    }
}
