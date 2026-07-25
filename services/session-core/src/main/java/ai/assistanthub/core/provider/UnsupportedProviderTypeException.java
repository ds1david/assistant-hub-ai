package ai.assistanthub.core.provider;

/** {@code type} aceito pelo schema mas sem {@link ProviderAdapter} disponível (Edge Case da spec). */
public class UnsupportedProviderTypeException extends RuntimeException {

    public UnsupportedProviderTypeException(Provider provider) {
        super("Nenhum adaptador disponível para o type '" + provider.type().wireValue()
                + "' (provider " + provider.id() + ")");
    }
}
