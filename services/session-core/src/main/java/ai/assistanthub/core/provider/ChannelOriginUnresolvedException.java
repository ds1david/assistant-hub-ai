package ai.assistanthub.core.provider;

/**
 * Falha de contexto de sessão/origem de canal antes do loop de provedores (issue #40).
 * Não é {@link InvocationErrorType} — não aciona fallback de rota.
 */
public class ChannelOriginUnresolvedException extends RuntimeException {

    public ChannelOriginUnresolvedException(String message) {
        super(message);
    }
}
