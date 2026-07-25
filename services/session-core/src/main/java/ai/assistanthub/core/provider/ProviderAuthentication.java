package ai.assistanthub.core.provider;

/**
 * Espelha {@code $defs/authentication} do schema v1. {@code secretRef} nunca contém o valor
 * resolvido do segredo, só o ponteiro ({@code env:VAR} ou {@code os:caminho}) — ver
 * docs/security/provider-secrets.md e specs/015-issue-37-ai-provider-hub/data-model.md.
 */
public record ProviderAuthentication(AuthenticationMode mode, String secretRef, String headerName) {
}
