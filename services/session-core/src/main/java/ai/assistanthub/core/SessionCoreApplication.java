package ai.assistanthub.core;

import ai.assistanthub.core.transcript.TranscriptIngestionProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties(TranscriptIngestionProperties.class)
public class SessionCoreApplication {
    public static void main(String[] args) {
        SpringApplication.run(SessionCoreApplication.class, args);
    }
}
