package ai.assistanthub.sdk;

public interface HubPlugin extends AutoCloseable {
    PluginDescriptor descriptor();

    void start(PluginContext context);

    default void stop() {
        // Optional lifecycle hook.
    }

    @Override
    default void close() {
        stop();
    }
}
