package ai.assistanthub.core.provider;

/** Nenhum {@link Provider} com esse {@code id} existe no perfil vigente. */
public class ProviderNotFoundException extends RuntimeException {

    public ProviderNotFoundException(String id) {
        super("Provider não encontrado: " + id);
    }
}
