package ai.assistanthub.core.provider;

import java.util.List;

/**
 * Espelha {@code $defs/route} do schema v1. {@code fallbacks} é tentada em ordem só quando o
 * {@code primary} falhar, expirar (timeout) ou retornar rate limit (FR-005).
 */
public record ProviderRoute(String primary, List<String> fallbacks) {

    public ProviderRoute {
        fallbacks = List.copyOf(fallbacks == null ? List.of() : fallbacks);
    }
}
