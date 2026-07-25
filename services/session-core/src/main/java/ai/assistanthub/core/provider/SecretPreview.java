package ai.assistanthub.core.provider;

/**
 * Prévia mascarada de um segredo resolvido (FR-014) — {@code maskedValue} nunca é o valor
 * completo; {@code null} quando {@code authentication.mode == none} ou o segredo não pôde ser
 * resolvido.
 */
public record SecretPreview(String providerId, String maskedValue) {
}
