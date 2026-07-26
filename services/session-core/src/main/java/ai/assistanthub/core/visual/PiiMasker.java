package ai.assistanthub.core.visual;

import java.util.regex.Pattern;

/**
 * Deterministic PII masking for OCR text (R4 / issue #68). Does not log input/output.
 */
public final class PiiMasker {

    private static final Pattern EMAIL = Pattern.compile(
            "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}");
    private static final Pattern PHONE = Pattern.compile(
            "(?<!\\d)(?:\\+?\\d{1,3}[\\s.-]?)?(?:\\(?\\d{2,3}\\)?[\\s.-]?)?\\d{3,5}[\\s.-]?\\d{4}(?!\\d)");
    private static final Pattern CARD = Pattern.compile(
            "(?<!\\d)(?:\\d[ -]*?){13,19}(?!\\d)");

    private PiiMasker() {
    }

    public static MaskResult mask(String text) {
        if (text == null || text.isBlank()) {
            return new MaskResult("", false);
        }
        String out = text;
        boolean changed = false;
        String next = EMAIL.matcher(out).replaceAll("[email]");
        if (!next.equals(out)) {
            changed = true;
            out = next;
        }
        next = CARD.matcher(out).replaceAll("[card]");
        if (!next.equals(out)) {
            changed = true;
            out = next;
        }
        next = PHONE.matcher(out).replaceAll("[phone]");
        if (!next.equals(out)) {
            changed = true;
            out = next;
        }
        return new MaskResult(out, changed);
    }

    public record MaskResult(String text, boolean masked) {
    }
}
