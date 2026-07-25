package ai.assistanthub.core.provider;

import java.util.List;

/** Erro de validação específico (FR-002) — {@link #errors()} lista cada violação encontrada. */
public class ProviderProfileValidationException extends RuntimeException {

    private final List<String> errors;

    public ProviderProfileValidationException(List<String> errors) {
        super("Perfil de provedores inválido: " + String.join("; ", errors));
        this.errors = List.copyOf(errors);
    }

    public List<String> errors() {
        return errors;
    }
}
