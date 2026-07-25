package ai.assistanthub.core.provider;

/** {@link Provider} referenciado por uma {@link ProviderRoute} — não pode ser removido. */
public class ProviderInUseException extends RuntimeException {

    public ProviderInUseException(String id) {
        super("Provider referenciado por uma rota, não pode ser removido: " + id);
    }
}
