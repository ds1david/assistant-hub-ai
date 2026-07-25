package ai.assistanthub.core.provider;

/** Espelha {@code $defs/defaults} do schema v1. {@code timeoutMs} é o limite isolado por invocação (FR-003). */
public record ProviderDefaults(
        String model,
        Double temperature,
        Double topP,
        Integer maxTokens,
        int timeoutMs) {
}
