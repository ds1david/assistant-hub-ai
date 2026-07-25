package ai.assistanthub.core.provider;

import java.util.Optional;

/**
 * Resolve um {@code secretRef} (FR-007) sem nunca logar nem expor o valor resolvido fora do
 * processo Java — implementações não devem chamar {@code toString()}/logger no valor retornado.
 */
public interface SecretResolver {

    /** {@code secretRef} no formato {@code env:VAR} ou {@code os:caminho}; vazio se não puder ser resolvido. */
    Optional<String> resolve(String secretRef);
}
