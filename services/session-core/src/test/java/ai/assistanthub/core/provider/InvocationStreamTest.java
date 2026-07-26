package ai.assistanthub.core.provider;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

/** 026 US2: stream multi-chunk e cancel. */
class InvocationStreamTest {

    @TempDir
    Path tempDir;

    private Provider streamProvider() {
        return new Provider(
                "streamer", "Fake stream", ProviderType.FAKE, true, "fake://stream",
                new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                new ProviderDefaults("fake-model", null, null, null, 5_000),
                Set.of("chat"));
    }

    private InvocationService service(Provider provider) {
        ProviderProfile profile = new ProviderProfile(
                1, List.of(provider), Map.of("chat-route", new ProviderRoute(provider.id(), List.of())));
        ProviderProfileValidator validator = ProviderTestSupport.newValidator();
        ProviderTestSupport.writeRawProfile(tempDir, profile, validator);
        ProviderRegistry registry = ProviderTestSupport.newRegistry(ProviderTestSupport.newStore(tempDir, validator));
        return ProviderTestSupport.newInvocationService(registry, new FakeProviderAdapter());
    }

    @Test
    void streamEmitsMultipleChunksAndDone() {
        InvocationService service = service(streamProvider());
        List<String> chunks = new ArrayList<>();
        AtomicReference<InvocationResult> terminal = new AtomicReference<>();

        service.invokeStream(
                "chat-route",
                new InvocationRequest("session-1", null, "chat", "ola mundo"),
                new StreamSink() {
                    @Override
                    public void onChunk(String text) {
                        chunks.add(text);
                    }

                    @Override
                    public void onTerminal(InvocationResult result) {
                        terminal.set(result);
                    }
                },
                () -> false);

        assertThat(chunks.size()).isGreaterThanOrEqualTo(2);
        assertThat(terminal.get()).isNotNull();
        assertThat(terminal.get().success()).isTrue();
        assertThat(terminal.get().output()).contains("ola mundo");
        assertThat(String.join("", chunks)).isEqualTo(terminal.get().output());
    }

    @Test
    void cancelStopsWithoutThrowing() {
        InvocationService service = service(streamProvider());
        AtomicBoolean cancel = new AtomicBoolean(false);
        List<String> chunks = new ArrayList<>();
        AtomicReference<InvocationResult> terminal = new AtomicReference<>();

        service.invokeStream(
                "chat-route",
                new InvocationRequest("session-1", null, "chat", "um dois tres quatro cinco seis"),
                new StreamSink() {
                    @Override
                    public void onChunk(String text) {
                        chunks.add(text);
                        if (chunks.size() >= 1) {
                            cancel.set(true);
                        }
                    }

                    @Override
                    public void onTerminal(InvocationResult result) {
                        terminal.set(result);
                    }
                },
                cancel::get);

        assertThat(terminal.get()).isNotNull();
        // cancel or success — must complete without exception; often cancelled mid-stream
        assertThat(terminal.get().success() || terminal.get().errorType() != null).isTrue();
    }
}
