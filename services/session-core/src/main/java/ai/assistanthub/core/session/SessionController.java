package ai.assistanthub.core.session;

import ai.assistanthub.sdk.ConversationProfile;
import ai.assistanthub.sdk.HubEvent;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api")
public class SessionController {
    private final SessionRepository repository;

    public SessionController(SessionRepository repository) {
        this.repository = repository;
    }

    @GetMapping("/profiles")
    public List<ConversationProfile> profiles() {
        return List.of(
                new ConversationProfile("interview-technical", "Entrevista técnica", 1,
                        List.of("audio-capture-windows", "stt-faster-whisper"),
                        List.of("technical-interviewer", "answer-coach"), Map.of()),
                new ConversationProfile("product-refinement", "Refinamento de produto", 1,
                        List.of("audio-capture-windows", "stt-faster-whisper"),
                        List.of("product-owner", "technical-lead"), Map.of())
        );
    }

    @PostMapping("/sessions")
    @ResponseStatus(HttpStatus.CREATED)
    public ConversationSession create(@Valid @RequestBody CreateSessionRequest request) {
        return repository.save(ConversationSession.create(request.title(), request.profileId(), request.metadata()));
    }

    @GetMapping("/sessions/{id}")
    public ConversationSession get(@PathVariable UUID id) {
        return repository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Session not found"));
    }

    @PostMapping("/sessions/{id}/events")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public HubEvent append(@PathVariable UUID id, @RequestBody AppendEventRequest request) {
        repository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Session not found"));
        HubEvent event = HubEvent.now(id, request.type(), request.source(), request.payload());
        repository.append(event);
        return event;
    }

    @GetMapping("/sessions/{id}/events")
    public List<HubEvent> events(@PathVariable UUID id) {
        repository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Session not found"));
        return repository.events(id);
    }

    public record CreateSessionRequest(
            @NotBlank String title,
            @NotBlank String profileId,
            Map<String, Object> metadata) {
    }

    public record AppendEventRequest(
            @NotBlank String type,
            @NotBlank String source,
            Map<String, Object> payload) {
    }
}
