package ai.assistanthub.core.visual;

/**
 * Pluggable OCR / UI description (R4). Implementations must not log image bytes or full text.
 */
public interface OcrEngine {

    /**
     * @param imageBytes optional PNG/JPEG bytes; may be null when {@code fallbackText} is set
     * @param fallbackText operator- or fixture-provided description when no real OCR
     */
    OcrResult recognize(byte[] imageBytes, String fallbackText);

    record OcrResult(String text, String engineId) {
    }
}
