package ai.assistanthub.core.provider;

/**
 * Contexto de sessão/transcript necessário para uma invocação (FR-004 / issue #40) —
 * {@code channelId} pode ser {@code null} quando a capacidade não está associada a um canal
 * específico. A origem do canal ({@code sourceType}) <strong>não</strong> é enviada pelo
 * chamador: o servidor a resolve a partir de eventos da sessão (FR-010).
 */
public record InvocationRequest(String sessionId, String channelId, String capability, String input) {
}
