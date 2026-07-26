package ai.assistanthub.core.provider;

/**
 * Receptor de invocação em streaming (026). Implementações MUST tolerar cancelamento e MUST NOT
 * logar o texto completo como se fosse métrica de segredo.
 */
public interface StreamSink {

    void onChunk(String text);

    void onTerminal(InvocationResult result);
}
