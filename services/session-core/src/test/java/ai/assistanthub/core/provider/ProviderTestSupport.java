package ai.assistanthub.core.provider;

import ai.assistanthub.core.memory.MemoryHubTestSupport;
import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.core.session.SessionRepository;
import ai.assistanthub.sdk.HubEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.yaml.snakeyaml.Yaml;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

/**
 * Constrói o trio {@link ProviderProfileStore}/{@link ProviderRegistry}/{@link InvocationService}
 * apontando para um perfil isolado por teste (mesmo padrão de {@code MemoryHubTestSupport}).
 */
public final class ProviderTestSupport {

    private ProviderTestSupport() {
    }

    public static ObjectMapper newObjectMapper() {
        return new ObjectMapper().findAndRegisterModules();
    }

    public static ProviderProfileValidator newValidator() {
        return new ProviderProfileValidator(newObjectMapper());
    }

    public static ProviderProfileStore newStore(Path directory, ProviderProfileValidator validator) {
        AiProviderHubProperties properties =
                new AiProviderHubProperties(directory.resolve("ai-providers-test.yaml").toString());
        return new ProviderProfileStore(properties, validator);
    }

    public static ProviderRegistry newRegistry(ProviderProfileStore store) {
        return new ProviderRegistry(store);
    }

    public static SessionRepository newSessionRepository(Path directory) {
        return new SessionRepository(MemoryHubTestSupport.newStore(directory));
    }

    public static ChannelOriginResolver newOriginResolver(SessionRepository sessionRepository) {
        return new ChannelOriginResolver(sessionRepository);
    }

    /**
     * {@link InvocationService} com {@link SessionRepository} vazio (só seguro para invokes
     * sem {@code channelId}).
     */
    public static InvocationService newInvocationService(
            ProviderRegistry registry, ProviderAdapterFactory.TypedProviderAdapter... adapters) {
        try {
            Path dir = Files.createTempDirectory("provider-test-empty-");
            return newInvocationService(registry, newSessionRepository(dir), adapters);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    public static InvocationService newInvocationService(
            ProviderRegistry registry,
            SessionRepository sessionRepository,
            ProviderAdapterFactory.TypedProviderAdapter... adapters) {
        return new InvocationService(
                registry,
                new ProviderAdapterFactory(List.of(adapters)),
                newOriginResolver(sessionRepository));
    }

    /**
     * Cria sessão + evento de transcript com origem canônica; devolve o UUID da sessão como string
     * para uso em {@link InvocationRequest#sessionId()} quando há {@code channelId}.
     */
    public static String seedChannelOrigin(
            SessionRepository sessionRepository, String channelId, String sourceType) {
        ConversationSession session = ConversationSession.create("teste-origem", "test", Map.of());
        sessionRepository.save(session);
        Map<String, String> correlation = Map.of(
                "channelId", channelId,
                "sourceType", sourceType,
                "label", channelId,
                "device.index", "",
                "device.name", "",
                "device.endpointId", "");
        HubEvent base = HubEvent.now(session.id(), "transcript.final.v2", "transcription-service",
                Map.of("text", "fixture"));
        HubEvent event = new HubEvent(
                base.id(), base.sessionId(), base.type(), base.source(),
                base.occurredAt(), base.ingestedAt(), base.payload(), correlation);
        sessionRepository.append(event);
        return session.id().toString();
    }

    /**
     * Grava o perfil direto no arquivo, sem passar por {@link ProviderProfileStore#save} — usado
     * para perfis de teste com {@link ProviderType#FAKE}, que {@link ProviderProfileValidator}
     * rejeitaria (não está no schema v1) se fosse validado normalmente.
     */
    public static void writeRawProfile(Path directory, ProviderProfile profile, ProviderProfileValidator validator) {
        Path file = directory.resolve("ai-providers-test.yaml");
        try {
            Files.createDirectories(file.getParent());
            try (BufferedWriter writer = Files.newBufferedWriter(file)) {
                new Yaml().dump(validator.toMap(profile), writer);
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
