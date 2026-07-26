package ai.assistanthub.core.provider;

/** Modelo descoberto via API do provedor (027 / OpenAI-compatible {@code /models}). */
public record ModelInfo(String id, String ownedBy) {
}
