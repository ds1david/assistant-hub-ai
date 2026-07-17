package ai.assistanthub.sdk;

import java.util.Map;
import java.util.Objects;
import java.util.Set;

public record PluginDescriptor(
        String id,
        String name,
        String version,
        String minimumSdkVersion,
        Set<Capability> capabilities,
        Set<String> requiredPermissions,
        Map<String, Object> configurationSchema) {

    public PluginDescriptor {
        Objects.requireNonNull(id, "id");
        Objects.requireNonNull(name, "name");
        Objects.requireNonNull(version, "version");
        Objects.requireNonNull(minimumSdkVersion, "minimumSdkVersion");
        capabilities = Set.copyOf(capabilities == null ? Set.of() : capabilities);
        requiredPermissions = Set.copyOf(requiredPermissions == null ? Set.of() : requiredPermissions);
        configurationSchema = Map.copyOf(configurationSchema == null ? Map.of() : configurationSchema);
    }
}
