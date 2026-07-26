package ai.assistanthub.core.visual;

import ai.assistanthub.core.session.SessionRepository;
import ai.assistanthub.sdk.HubEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Ingest and list visual frames as HubEvents {@code visual.frame.v1} (issue #68).
 */
@Service
public class VisualFrameService {

    public static final String EVENT_TYPE = "visual.frame.v1";
    public static final String SOURCE = "visual-context";

    private static final Logger LOGGER = LoggerFactory.getLogger(VisualFrameService.class);

    private final SessionRepository sessionRepository;
    private final OcrEngine ocrEngine;

    public VisualFrameService(SessionRepository sessionRepository, OcrEngine ocrEngine) {
        this.sessionRepository = sessionRepository;
        this.ocrEngine = ocrEngine;
    }

    public Map<String, Object> ingest(
            UUID sessionId,
            boolean consent,
            String fallbackText,
            byte[] imageBytes,
            String source,
            String linkedEventId,
            Integer width,
            Integer height,
            String contentType) {
        sessionRepository
                .findById(sessionId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Session not found"));
        if (!consent) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "consent required for visual capture");
        }

        OcrEngine.OcrResult ocr = ocrEngine.recognize(imageBytes, fallbackText);
        PiiMasker.MaskResult mask = PiiMasker.mask(ocr.text());

        UUID frameId = UUID.randomUUID();
        Instant capturedAt = Instant.now();
        String sha = imageBytes != null && imageBytes.length > 0 ? sha256Hex(imageBytes) : null;

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", EVENT_TYPE);
        payload.put("sessionId", sessionId.toString());
        payload.put("frameId", frameId.toString());
        payload.put("capturedAt", capturedAt.toString());
        payload.put("consent", true);
        payload.put("ocrText", mask.text());
        payload.put("ocrEngine", ocr.engineId());
        payload.put("masked", mask.masked());
        payload.put("source", source != null && !source.isBlank() ? source : "shell");
        // P0: do not persist raw pixels in hub event (privacy + size).
        payload.put("imageStored", false);
        // HubEvent payload is Map.copyOf — null values are forbidden.
        putIfPresent(payload, "linkedEventId", linkedEventId);
        putIfPresent(payload, "contentType", contentType);
        putIfPresent(payload, "width", width);
        putIfPresent(payload, "height", height);
        putIfPresent(payload, "sha256", sha);

        HubEvent event = HubEvent.now(sessionId, EVENT_TYPE, SOURCE, payload);
        sessionRepository.append(event);

        // P9: never log ocrText or image bytes
        LOGGER.info(
                "visual-frame ingested sessionId={} frameId={} eventId={} engine={} masked={} imageBytes={}",
                sessionId,
                frameId,
                event.id(),
                ocr.engineId(),
                mask.masked(),
                imageBytes == null ? 0 : imageBytes.length);

        return toPublicView(event);
    }

    public List<Map<String, Object>> list(UUID sessionId) {
        sessionRepository
                .findById(sessionId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Session not found"));
        List<Map<String, Object>> out = new ArrayList<>();
        for (HubEvent event : sessionRepository.events(sessionId)) {
            if (EVENT_TYPE.equals(event.type())) {
                out.add(toPublicView(event));
            }
        }
        return out;
    }

    private static Map<String, Object> toPublicView(HubEvent event) {
        Map<String, Object> view = new LinkedHashMap<>();
        view.put("eventId", event.id().toString());
        view.put("sessionId", event.sessionId().toString());
        view.put("type", event.type());
        view.put("occurredAt", event.occurredAt().toString());
        view.put("payload", event.payload());
        return view;
    }

    private static void putIfPresent(Map<String, Object> map, String key, Object value) {
        if (value != null) {
            map.put(key, value);
        }
    }

    private static String sha256Hex(byte[] data) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(data));
        } catch (NoSuchAlgorithmException e) {
            return HexFormat.of().formatHex(Integer.toHexString(data.length).getBytes(StandardCharsets.UTF_8));
        }
    }
}
