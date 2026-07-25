package ai.assistanthub.core.provider;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** Caminho do perfil declarativo de provedores (R6, issue #37) — ver data-model.md. */
@ConfigurationProperties(prefix = "session-core.ai-provider-hub")
public record AiProviderHubProperties(String path) {

    private static final String DEFAULT_PATH = "config/ai-providers.yaml";

    public AiProviderHubProperties {
        path = (path == null || path.isBlank()) ? DEFAULT_PATH : path;
    }
}
