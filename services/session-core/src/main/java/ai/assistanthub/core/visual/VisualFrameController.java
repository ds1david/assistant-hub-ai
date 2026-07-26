package ai.assistanthub.core.visual;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * REST visual frames (R4 / issue #68).
 */
@RestController
@RequestMapping("/api/sessions/{sessionId}/visual-frames")
public class VisualFrameController {

    private final VisualFrameService visualFrameService;

    public VisualFrameController(VisualFrameService visualFrameService) {
        this.visualFrameService = visualFrameService;
    }

    @GetMapping
    public List<Map<String, Object>> list(@PathVariable("sessionId") UUID sessionId) {
        return visualFrameService.list(sessionId);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> create(
            @PathVariable("sessionId") UUID sessionId, @RequestBody CreateVisualFrameRequest body) {
        byte[] image = null;
        if (body.imageBase64() != null && !body.imageBase64().isBlank()) {
            try {
                image = Base64.getDecoder().decode(body.imageBase64());
            } catch (IllegalArgumentException e) {
                throw new org.springframework.web.server.ResponseStatusException(
                        HttpStatus.BAD_REQUEST, "invalid imageBase64");
            }
        }
        return visualFrameService.ingest(
                sessionId,
                body.consent(),
                body.ocrText(),
                image,
                body.source(),
                body.linkedEventId(),
                body.width(),
                body.height(),
                body.contentType());
    }

    /**
     * @param consent required true
     * @param ocrText optional fallback / fixture text for FakeOcrEngine
     * @param imageBase64 optional; not stored in P0, only hashed/OCR-stubbed
     */
    public record CreateVisualFrameRequest(
            boolean consent,
            String ocrText,
            String imageBase64,
            String source,
            String linkedEventId,
            Integer width,
            Integer height,
            String contentType) {
    }
}
