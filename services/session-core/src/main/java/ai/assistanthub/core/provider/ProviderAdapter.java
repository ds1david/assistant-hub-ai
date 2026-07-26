package ai.assistanthub.core.provider;

import java.util.function.BooleanSupplier;

/**
 * Contrato de invocação isolado por implementação de {@code type} (FR-001) — nenhum SDK de
 * fornecedor externo é permitido em uma implementação desta interface (P2).
 */
public interface ProviderAdapter {

    /** Verifica autenticação/modelo/timeout sem executar uma invocação completa de capacidade (FR-011). */
    ConnectionTestResult testConnection(Provider provider);

    /** Invoca o provedor para a capacidade/contexto de {@code request}, respeitando {@code defaults().timeoutMs()}. */
    AdapterOutcome invoke(Provider provider, InvocationRequest request);

    /**
     * Invocação em streaming (026). Default: uma chamada síncrona e um único chunk com o output.
     * {@code cancelled} true interrompe o envio de novos chunks (best-effort).
     */
    default AdapterOutcome invokeStream(
            Provider provider,
            InvocationRequest request,
            StreamChunkListener listener,
            BooleanSupplier cancelled) {
        if (cancelled.getAsBoolean()) {
            return AdapterOutcome.failure(InvocationErrorType.GENERIC, "invocação cancelada");
        }
        AdapterOutcome outcome = invoke(provider, request);
        if (outcome.success() && outcome.output() != null && !outcome.output().isEmpty()) {
            if (!cancelled.getAsBoolean()) {
                listener.onChunk(outcome.output());
            }
        }
        return outcome;
    }

    @FunctionalInterface
    interface StreamChunkListener {
        void onChunk(String text);
    }
}
