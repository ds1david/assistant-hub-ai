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
 * Origem de canal ({@code sourceType}) é resolvida antes do loop de provedores (issue #40).
 */
@Component
public class InvocationService {

    private static final Logger LOGGER = LoggerFactory.getLogger(InvocationService.class);

    private final ProviderRegistry registry;
    private final ProviderAdapterFactory adapterFactory;
    private final ChannelOriginResolver originResolver;
    private final ExecutorService executor = Executors.newCachedThreadPool();

    public InvocationService(
            ProviderRegistry registry,
            ProviderAdapterFactory adapterFactory,
            ChannelOriginResolver originResolver) {
        this.registry = registry;
        this.adapterFactory = adapterFactory;
        this.originResolver = originResolver;
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

    /**
     * @throws RouteNotFoundException se {@code routeName} não existir no perfil vigente.
     * @throws ChannelOriginUnresolvedException se {@code channelId} presente e origem não resolvível.
     */
    public InvocationResult invoke(String routeName, InvocationRequest request) {
        String resolvedSourceType = resolveSourceTypeIfNeeded(request);

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

            InvocationResult attempt = attempt(maybeProvider.get(), request, resolvedSourceType);
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
                resolvedSourceType, false, InvocationErrorType.GENERIC,
                null, "nenhum provedor habilitado disponível para a rota '" + routeName + "'",
                0, Instant.now());
    }

    private String resolveSourceTypeIfNeeded(InvocationRequest request) {
        String channelId = request.channelId();
        if (channelId == null || channelId.isBlank()) {
            return null;
        }
        return originResolver.resolve(request.sessionId(), channelId);
    }

    private InvocationResult attempt(Provider provider, InvocationRequest request, String sourceType) {
        long startedAt = System.nanoTime();

        if (!provider.capabilities().contains(request.capability())) {
            return failureResult(provider, request, sourceType, InvocationErrorType.CAPABILITY_MISMATCH,
                    "capacidade '" + request.capability() + "' não suportada por " + provider.id(), startedAt);
        }

        Optional<ProviderAdapter> adapter = adapterFactory.resolve(provider);
        if (adapter.isEmpty()) {
            return failureResult(provider, request, sourceType, InvocationErrorType.GENERIC,
                    "nenhum adaptador disponível para o type '" + provider.type().wireValue() + "'", startedAt);
        }

        AdapterOutcome outcome = runWithTimeout(
                () -> adapter.get().invoke(provider, request),
                provider.defaults().timeoutMs(),
                () -> AdapterOutcome.failure(
                        InvocationErrorType.TIMEOUT, "timeout após " + provider.defaults().timeoutMs() + "ms"));

        InvocationResult result = new InvocationResult(
                provider.id(), provider.defaults().model(), request.capability(), request.sessionId(),
                request.channelId(), sourceType, outcome.success(), outcome.errorType(), outcome.output(),
                outcome.message(), elapsedMs(startedAt), Instant.now());
        logInvocation(result);
        return result;
    }

    /**
     * Métrica por invocação (FR-008 / issue #40 FR-012) — {@code providerId}/{@code model}/
     * {@code capability}/{@code sessionId}/{@code channelId}/{@code sourceType}/{@code latencyMs}/
     * resultado; {@code output}/{@code message} nunca entram no log (P9).
     */
    private void logInvocation(InvocationResult result) {
        LOGGER.info(
                "ai-provider-invocation providerId={} model={} capability={} sessionId={} channelId={} "
                        + "sourceType={} success={} errorType={} latencyMs={}",
                result.providerId(), result.model(), result.capability(), result.sessionId(), result.channelId(),
                result.sourceType(), result.success(), result.errorType(), result.latencyMs());
    }

    private InvocationResult failureResult(
            Provider provider,
            InvocationRequest request,
            String sourceType,
            InvocationErrorType errorType,
            String message,
            long startedAt) {
        InvocationResult result = new InvocationResult(
                provider.id(), provider.defaults().model(), request.capability(), request.sessionId(),
                request.channelId(), sourceType, false, errorType, null, message, elapsedMs(startedAt), Instant.now());
        logInvocation(result);
        return result;
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
