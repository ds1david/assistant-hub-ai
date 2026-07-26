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
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.BooleanSupplier;
import java.util.function.Supplier;

/**
 * Testa conexão e invoca provedores de forma isolada por {@code timeoutMs} (FR-003), com
 * fallback ordenado (FR-005) e circuit breaker por provedor (026). Streaming via
 * {@link #invokeStream}. Origem de canal ({@code sourceType}) é resolvida antes do loop
 * (issue #40).
 */
@Component
public class InvocationService {

    private static final Logger LOGGER = LoggerFactory.getLogger(InvocationService.class);

    private final ProviderRegistry registry;
    private final ProviderAdapterFactory adapterFactory;
    private final ChannelOriginResolver originResolver;
    private final ProviderCircuitBreaker circuitBreaker;
    private final ExecutorService executor = Executors.newCachedThreadPool();

    public InvocationService(
            ProviderRegistry registry,
            ProviderAdapterFactory adapterFactory,
            ChannelOriginResolver originResolver,
            ProviderCircuitBreaker circuitBreaker) {
        this.registry = registry;
        this.adapterFactory = adapterFactory;
        this.originResolver = originResolver;
        this.circuitBreaker = circuitBreaker;
    }

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
        List<String> candidateIds = candidateIds(routeName);

        InvocationResult lastFailure = null;
        for (String candidateId : candidateIds) {
            Optional<Provider> maybeProvider = registry.findById(candidateId);
            if (maybeProvider.isEmpty() || !maybeProvider.get().enabled()) {
                continue;
            }
            Provider provider = maybeProvider.get();

            if (!circuitBreaker.allowCall(provider.id())) {
                lastFailure = failureResult(
                        provider, request, resolvedSourceType, InvocationErrorType.CIRCUIT_OPEN,
                        "circuit breaker OPEN para " + provider.id(), System.nanoTime());
                continue;
            }

            InvocationResult attempt = attempt(provider, request, resolvedSourceType);
            applyBreaker(provider.id(), attempt);
            if (attempt.success()) {
                return attempt;
            }
            lastFailure = attempt;
        }

        if (lastFailure != null) {
            return lastFailure;
        }
        return new InvocationResult(
                routeName, null, request.capability(), request.sessionId(), request.channelId(),
                resolvedSourceType, false, InvocationErrorType.GENERIC,
                null, "nenhum provedor habilitado disponível para a rota '" + routeName + "'",
                0, Instant.now());
    }

    /**
     * Invocação em streaming (026). Emite chunks no {@link StreamSink} e um terminal
     * {@link InvocationResult}. Respeita breaker e fallback de rota.
     */
    public void invokeStream(String routeName, InvocationRequest request, StreamSink sink, BooleanSupplier cancelled) {
        String resolvedSourceType = resolveSourceTypeIfNeeded(request);
        List<String> candidateIds = candidateIds(routeName);

        InvocationResult lastFailure = null;
        for (String candidateId : candidateIds) {
            if (cancelled.getAsBoolean()) {
                sink.onTerminal(cancelledResult(request, resolvedSourceType, candidateId));
                return;
            }
            Optional<Provider> maybeProvider = registry.findById(candidateId);
            if (maybeProvider.isEmpty() || !maybeProvider.get().enabled()) {
                continue;
            }
            Provider provider = maybeProvider.get();

            if (!circuitBreaker.allowCall(provider.id())) {
                lastFailure = failureResult(
                        provider, request, resolvedSourceType, InvocationErrorType.CIRCUIT_OPEN,
                        "circuit breaker OPEN para " + provider.id(), System.nanoTime());
                continue;
            }

            InvocationResult attempt = attemptStream(provider, request, resolvedSourceType, sink, cancelled);
            applyBreaker(provider.id(), attempt);
            if (attempt.success() || cancelled.getAsBoolean()) {
                sink.onTerminal(attempt);
                return;
            }
            lastFailure = attempt;
        }

        if (lastFailure != null) {
            sink.onTerminal(lastFailure);
            return;
        }
        sink.onTerminal(new InvocationResult(
                routeName, null, request.capability(), request.sessionId(), request.channelId(),
                resolvedSourceType, false, InvocationErrorType.GENERIC,
                null, "nenhum provedor habilitado disponível para a rota '" + routeName + "'",
                0, Instant.now()));
    }

    public List<ProviderCircuitSnapshot> circuitSnapshots() {
        return circuitBreaker.snapshots();
    }

    private List<String> candidateIds(String routeName) {
        ProviderRoute route = registry.findRoute(routeName)
                .orElseThrow(() -> new RouteNotFoundException(routeName));
        List<String> candidateIds = new ArrayList<>();
        candidateIds.add(route.primary());
        candidateIds.addAll(route.fallbacks());
        return candidateIds;
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

    private InvocationResult attemptStream(
            Provider provider,
            InvocationRequest request,
            String sourceType,
            StreamSink sink,
            BooleanSupplier cancelled) {
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

        StringBuilder assembled = new StringBuilder();
        AtomicBoolean localCancel = new AtomicBoolean(false);
        BooleanSupplier combined = () -> cancelled.getAsBoolean() || localCancel.get();

        try {
            Future<AdapterOutcome> future = executor.submit(() -> adapter.get().invokeStream(
                    provider,
                    request,
                    text -> {
                        if (!combined.getAsBoolean()) {
                            assembled.append(text);
                            sink.onChunk(text);
                        }
                    },
                    combined));
            AdapterOutcome outcome = future.get(provider.defaults().timeoutMs(), TimeUnit.MILLISECONDS);
            if (cancelled.getAsBoolean()) {
                localCancel.set(true);
                future.cancel(true);
                InvocationResult cancelledResult = failureResult(
                        provider, request, sourceType, InvocationErrorType.GENERIC,
                        "invocação cancelada", startedAt);
                // success=false; do not record as provider health failure if cancelled by client
                return cancelledResult;
            }
            String output = outcome.success()
                    ? (assembled.length() > 0 ? assembled.toString() : outcome.output())
                    : null;
            InvocationResult result = new InvocationResult(
                    provider.id(), provider.defaults().model(), request.capability(), request.sessionId(),
                    request.channelId(), sourceType, outcome.success(), outcome.errorType(), output,
                    outcome.message(), elapsedMs(startedAt), Instant.now());
            logInvocation(result);
            return result;
        } catch (TimeoutException e) {
            localCancel.set(true);
            return failureResult(provider, request, sourceType, InvocationErrorType.TIMEOUT,
                    "timeout após " + provider.defaults().timeoutMs() + "ms", startedAt);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return failureResult(provider, request, sourceType, InvocationErrorType.GENERIC,
                    "invocação interrompida", startedAt);
        } catch (ExecutionException e) {
            return failureResult(provider, request, sourceType, InvocationErrorType.GENERIC,
                    e.getCause() != null ? e.getCause().toString() : e.toString(), startedAt);
        }
    }

    private void applyBreaker(String providerId, InvocationResult result) {
        if (result.success()) {
            circuitBreaker.recordSuccess(providerId);
            return;
        }
        InvocationErrorType type = result.errorType();
        if (type == null
                || type == InvocationErrorType.CAPABILITY_MISMATCH
                || type == InvocationErrorType.CIRCUIT_OPEN) {
            return;
        }
        // Client cancel is GENERIC with message "invocação cancelada" — do not open breaker
        if (type == InvocationErrorType.GENERIC
                && result.message() != null
                && result.message().contains("cancelad")) {
            return;
        }
        circuitBreaker.recordFailure(providerId);
    }

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

    private InvocationResult cancelledResult(InvocationRequest request, String sourceType, String providerId) {
        return new InvocationResult(
                providerId, null, request.capability(), request.sessionId(), request.channelId(),
                sourceType, false, InvocationErrorType.GENERIC, null, "invocação cancelada", 0, Instant.now());
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
