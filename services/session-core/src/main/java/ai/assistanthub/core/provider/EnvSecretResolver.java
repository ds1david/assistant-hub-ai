package ai.assistanthub.core.provider;

import org.springframework.stereotype.Component;

import java.util.Optional;

/**
 * Resolve {@code secretRef} no formato {@code env:VAR} a partir de variáveis de ambiente —
 * cobertura do ambiente WSL Developer (docs/security/provider-secrets.md). {@code os:...}
 * (armazenamento seguro do Windows) não é resolvido nesta fatia (Assumption da spec) — retorna
 * vazio para que o chamador trate como segredo não resolvido, não como erro de formato.
 */
@Component
public class EnvSecretResolver implements SecretResolver {

    private static final String ENV_PREFIX = "env:";

    @Override
    public Optional<String> resolve(String secretRef) {
        if (secretRef == null || !secretRef.startsWith(ENV_PREFIX)) {
            return Optional.empty();
        }
        String variableName = secretRef.substring(ENV_PREFIX.length());
        String value = System.getenv(variableName);
        return (value == null || value.isBlank()) ? Optional.empty() : Optional.of(value);
    }
}
