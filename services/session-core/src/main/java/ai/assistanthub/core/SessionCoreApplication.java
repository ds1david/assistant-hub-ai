package ai.assistanthub.core;

import ai.assistanthub.core.memory.MemoryHubProperties;
import ai.assistanthub.core.provider.AiProviderHubProperties;
import ai.assistanthub.core.transcript.TranscriptIngestionProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties({TranscriptIngestionProperties.class, MemoryHubProperties.class, AiProviderHubProperties.class})
public class SessionCoreApplication {
    public static void main(String[] args) {
        SpringApplication.run(SessionCoreApplication.class, args);
    }
}
