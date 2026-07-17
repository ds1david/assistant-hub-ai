package ai.assistanthub.sdk;

import java.util.Map;

public interface PluginContext {
    EventPublisher eventPublisher();
    Map<String, Object> configuration();
}
