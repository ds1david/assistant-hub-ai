package ai.assistanthub.core.visual;

import org.springframework.stereotype.Component;

/**
 * Deterministic OCR stub for tests and P0 without GPU/Tesseract.
 * Uses fallbackText, or a fixed marker when only image bytes are present.
 */
@Component
public class FakeOcrEngine implements OcrEngine {

    public static final String ENGINE_ID = "fake";

    @Override
    public OcrResult recognize(byte[] imageBytes, String fallbackText) {
        if (fallbackText != null && !fallbackText.isBlank()) {
            return new OcrResult(fallbackText.trim(), ENGINE_ID);
        }
        if (imageBytes != null && imageBytes.length > 0) {
            return new OcrResult("[image " + imageBytes.length + " bytes — OCR stub]", ENGINE_ID);
        }
        return new OcrResult("", ENGINE_ID);
    }
}
