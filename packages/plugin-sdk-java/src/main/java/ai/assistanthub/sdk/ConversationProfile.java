package ai.assistanthub.sdk;

import java.util.List;
import java.util.Map;
import java.util.Objects;

public record ConversationProfile(
        String id,
        String displayName,
        int version,
        List<String> enabledPlugins,
        List<String> personas,
        Map<String, Object> policies) {

    public ConversationProfile {
        Objects.requireNonNull(id, "id");
        Objects.requireNonNull(displayName, "displayName");
        enabledPlugins = List.copyOf(enabledPlugins == null ? List.of() : enabledPlugins);
        personas = List.copyOf(personas == null ? List.of() : personas);
        policies = Map.copyOf(policies == null ? Map.of() : policies);
    }
}
