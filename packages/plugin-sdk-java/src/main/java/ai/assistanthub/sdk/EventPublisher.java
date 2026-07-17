package ai.assistanthub.sdk;

@FunctionalInterface
public interface EventPublisher {
    void publish(HubEvent event);
}
