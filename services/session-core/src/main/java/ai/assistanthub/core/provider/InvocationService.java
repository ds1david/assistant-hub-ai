package ai.assistanthub.core.provider;

import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.function.Supplier;

/**
 * Testa conexão e invoca provedores de forma isolada por {@code timeoutMs} (FR-003), com
 * fallback ordenado percorrendo {@code primary}/{@code fallbacks[]} (FR-005) — qualquer falha
 * (autenticação, modelo, timeout, rate limit, genérica ou incompatibilidade de capacidade)
 * aciona o próximo candidato da rota, nunca invoca um provedor {@code enabled: false}, e nunca
 * propaga uma exceção não tratada que derrubaria o session-core (US4).
 */
@Component
public class InvocationService {

    private static final Logger LOGGER = LoggerFactory.getLogger(InvocationService.class);

    private final ProviderRegistry registry;
    private final ProviderAdapterFactory adapterFactory;
    private final ExecutorService executor = Executors.newCachedThreadPool();

    public InvocationService(ProviderRegistry registry, ProviderAdapterFactory adapterFactory) {
        this.registry = registry;
        this.adapterFactory = adapterFactory;
    }

    /** @throws UnsupportedProviderTypeException se {@code provider.type()} não tiver adaptador disponível. */
    public ConnectionTestResult testConnection(Provider provider) {
        ProviderAdapter adapter = adapterFactory.resolve(provider)
                .orElseThrow(() -> new UnsupportedProviderTypeException(provider));

        return runWithTimeout(
                () -> adapter.testConnection(provider),
                provider.defaults().timeoutMs(),
                () -> ConnectionTestResult.failure(
                        provider.id(), InvocationErrorType.TIMEOUT,
                        "timeout após " + provider.defaults().timeoutMs() + "ms"));
    }

    /** @throws RouteNotFoundException se {@code routeName} não existir no perfil vigente. */
    public InvocationResult invoke(String routeName, InvocationRequest request) {
        ProviderRoute route = registry.findRoute(routeName)
                .orElseThrow(() -> new RouteNotFoundException(routeName));

        List<String> candidateIds = new ArrayList<>();
        candidateIds.add(route.primary());
        candidateIds.addAll(route.fallbacks());

        InvocationResult lastFailure = null;
        for (String candidateId : candidateIds) {
            Optional<Provider> maybeProvider = registry.findById(candidateId);
            // provedor removido desde a validação da rota, ou enabled=false: nunca invocado (FR-005)
            if (maybeProvider.isEmpty() || !maybeProvider.get().enabled()) {
                continue;
            }

            InvocationResult attempt = attempt(maybeProvider.get(), request);
            if (attempt.success()) {
                return attempt;
            }
            lastFailure = attempt;
        }

        if (lastFailure != null) {
            return lastFailure;
        }
        return new InvocationResult(
                route.primary(), null, request.capability(), request.sessionId(), request.channelId(),
                false, InvocationErrorType.GENERIC,
                null, "nenhum provedor habilitado disponível para a rota '" + routeName + "'",
                0, Instant.now());
    }

    private InvocationResult attempt(Provider provider, InvocationRequest request) {
        long startedAt = System.nanoTime();

        if (!provider.capabilities().contains(request.capability())) {
            return failureResult(provider, request, InvocationErrorType.CAPABILITY_MISMATCH,
                    "capacidade '" + request.capability() + "' não suportada por " + provider.id(), startedAt);
        }

        Optional<ProviderAdapter> adapter = adapterFactory.resolve(provider);
        if (adapter.isEmpty()) {
            return failureResult(provider, request, InvocationErrorType.GENERIC,
                    "nenhum adaptador disponível para o type '" + provider.type().wireValue() + "'", startedAt);
        }

        AdapterOutcome outcome = runWithTimeout(
                () -> adapter.get().invoke(provider, request),
                provider.defaults().timeoutMs(),
                () -> AdapterOutcome.failure(
                        InvocationErrorType.TIMEOUT, "timeout após " + provider.defaults().timeoutMs() + "ms"));

        InvocationResult result = new InvocationResult(
                provider.id(), provider.defaults().model(), request.capability(), request.sessionId(),
                request.channelId(), outcome.success(), outcome.errorType(), outcome.output(), outcome.message(),
                elapsedMs(startedAt), Instant.now());
        logInvocation(result);
        return result;
    }

    /**
     * Métrica por invocação (FR-008) — só `providerId`/`model`/`capability`/`sessionId`/
     * `channelId`/`latencyMs`/resultado; {@code output}/{@code message} nunca entram no log
     * porque podem conter texto de transcript ou detalhe de erro do provedor, e nenhum dos dois
     * é segredo, mas nenhum campo de segredo/autenticação passa por aqui de qualquer forma (P9).
     */
    private void logInvocation(InvocationResult result) {
        LOGGER.info(
                "ai-provider-invocation providerId={} model={} capability={} sessionId={} channelId={} "
                        + "success={} errorType={} latencyMs={}",
                result.providerId(), result.model(), result.capability(), result.sessionId(), result.channelId(),
                result.success(), result.errorType(), result.latencyMs());
    }

    private InvocationResult failureResult(
            Provider provider, InvocationRequest request, InvocationErrorType errorType, String message, long startedAt) {
        return new InvocationResult(
                provider.id(), provider.defaults().model(), request.capability(), request.sessionId(),
                request.channelId(), false, errorType, null, message, elapsedMs(startedAt), Instant.now());
    }

    private <T> T runWithTimeout(Supplier<T> action, int timeoutMs, Supplier<T> onTimeout) {
        Future<T> future = executor.submit(action::get);
        try {
            return future.get(timeoutMs, TimeUnit.MILLISECONDS);
        } catch (TimeoutException e) {
            future.cancel(true);
            return onTimeout.get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Invocação interrompida", e);
        } catch (ExecutionException e) {
            throw new IllegalStateException("Falha inesperada ao chamar o adaptador", e.getCause());
        }
    }

    private static long elapsedMs(long startedAtNanos) {
        return (System.nanoTime() - startedAtNanos) / 1_000_000;
    }

    @PreDestroy
    void shutdown() {
        executor.shutdownNow();
    }
}
