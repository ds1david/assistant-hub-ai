package ai.assistanthub.core.provider;

/** Nenhuma {@code route} com esse nome existe no perfil vigente. */
public class RouteNotFoundException extends RuntimeException {

    public RouteNotFoundException(String routeName) {
        super("Rota não encontrada: " + routeName);
    }
}
