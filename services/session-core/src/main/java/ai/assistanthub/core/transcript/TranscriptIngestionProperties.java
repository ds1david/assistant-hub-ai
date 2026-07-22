package ai.assistanthub.core.transcript;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "session-core.transcript-ingestion")
public record TranscriptIngestionProperties(String feedUrl) {
}
