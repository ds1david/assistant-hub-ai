package ai.assistanthub.core.provider;

/**
 * Contrato de invocação isolado por implementação de {@code type} (FR-001) — nenhum SDK de
 * fornecedor externo é permitido em uma implementação desta interface (P2).
 */
public interface ProviderAdapter {

    /** Verifica autenticação/modelo/timeout sem executar uma invocação completa de capacidade (FR-011). */
    ConnectionTestResult testConnection(Provider provider);

    /** Invoca o provedor para a capacidade/contexto de {@code request}, respeitando {@code defaults().timeoutMs()}. */
    AdapterOutcome invoke(Provider provider, InvocationRequest request);
}
