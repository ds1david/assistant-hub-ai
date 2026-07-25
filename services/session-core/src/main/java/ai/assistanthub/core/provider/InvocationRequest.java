package ai.assistanthub.core.provider;

/**
 * Contexto de sessão/transcript necessário para uma invocação (FR-004) — {@code channelId} pode
 * ser {@code null} quando a capacidade não está associada a um canal específico.
 */
public record InvocationRequest(String sessionId, String channelId, String capability, String input) {
}
