package ai.assistanthub.core.provider;

import java.util.Collections;
import java.util.Map;
import java.util.Optional;
import java.util.function.Supplier;

/**
 * Request-scoped secret overrides (desktop {@code os:} store → session-core for one call).
 * Values MUST NOT be logged. Cleared after the call (issue #64).
 */
public final class SecretOverrideContext {

    private static final ThreadLocal<Map<String, String>> OVERRIDES = new ThreadLocal<>();

    private SecretOverrideContext() {
    }

    public static <T> T callWith(Map<String, String> overrides, Supplier<T> action) {
        Map<String, String> safe =
                overrides == null || overrides.isEmpty()
                        ? Map.of()
                        : Collections.unmodifiableMap(overrides);
        OVERRIDES.set(safe);
        try {
            return action.get();
        } finally {
            OVERRIDES.remove();
        }
    }

    public static Optional<String> resolve(String secretRef) {
        if (secretRef == null) {
            return Optional.empty();
        }
        Map<String, String> map = OVERRIDES.get();
        if (map == null) {
            return Optional.empty();
        }
        String value = map.get(secretRef);
        if (value == null || value.isBlank()) {
            return Optional.empty();
        }
        return Optional.of(value);
    }
}
