package ai.assistanthub.core.provider;

import jakarta.validation.constraints.NotBlank;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * REST do AI Provider Hub (FR-011/FR-012/FR-013) — ver
 * specs/015-issue-37-ai-provider-hub/contracts/ai-provider-api.md. Nenhuma resposta inclui o
 * valor resolvido de um segredo (FR-007/FR-014) — só {@code secretRef} (não sensível) ou
 * {@link SecretPreview#maskedValue()}.
 */
@RestController
@RequestMapping("/api/ai-providers")
public class AiProviderController {

    private final ProviderRegistry registry;
    private final InvocationService invocationService;
    private final SecretResolver secretResolver;
    private final ExecutorService streamExecutor = Executors.newCachedThreadPool();

    public AiProviderController(
            ProviderRegistry registry, InvocationService invocationService, SecretResolver secretResolver) {
        this.registry = registry;
        this.invocationService = invocationService;
        this.secretResolver = secretResolver;
    }

    @GetMapping
    public List<Provider> list() {
        return registry.providers();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Provider create(@RequestBody Provider provider) {
        if (registry.findById(provider.id()).isPresent()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Provider já existe: " + provider.id());
        }
        return registry.save(provider);
    }

    @PutMapping("/{id}")
    public Provider update(@PathVariable("id") String id, @RequestBody Provider provider) {
        registry.findById(id).orElseThrow(() -> new ProviderNotFoundException(id));
        Provider withPathId = new Provider(
                id, provider.label(), provider.type(), provider.enabled(), provider.baseUrl(),
                provider.authentication(), provider.defaults(), provider.capabilities());
        return registry.save(withPathId);
    }

    @PatchMapping("/{id}/enabled")
    public Provider setEnabled(@PathVariable("id") String id, @RequestBody SetEnabledRequest request) {
        return registry.setEnabled(id, request.enabled());
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable("id") String id) {
        registry.remove(id);
    }

    @GetMapping("/{id}/secret-preview")
    public SecretPreview secretPreview(@PathVariable("id") String id) {
        Provider provider = registry.findById(id).orElseThrow(() -> new ProviderNotFoundException(id));
        ProviderAuthentication authentication = provider.authentication();
        if (authentication == null || authentication.mode() == AuthenticationMode.NONE) {
            return new SecretPreview(id, null);
        }
        Optional<String> secret = secretResolver.resolve(authentication.secretRef());
        return new SecretPreview(id, secret.map(AiProviderController::mask).orElse(null));
    }

    @PostMapping("/{id}/test")
    public ConnectionTestResult test(
            @PathVariable("id") String id,
            @RequestBody(required = false) SecretOverridesBody body) {
        Provider provider = registry.findById(id).orElseThrow(() -> new ProviderNotFoundException(id));
        Map<String, String> overrides =
                body != null && body.secretOverrides() != null ? body.secretOverrides() : Map.of();
        return SecretOverrideContext.callWith(overrides, () -> invocationService.testConnection(provider));
    }

    /** Descoberta de modelos (027) — OpenAI-compatible {@code GET /models}. */
    @GetMapping("/{id}/models")
    public ModelsDiscoveryResult listModels(@PathVariable("id") String id) {
        return invocationService.listModels(id);
    }

    @PostMapping("/invoke")
    public InvocationResult invoke(@RequestBody InvokeRequest request) {
        Map<String, String> overrides =
                request.secretOverrides() != null ? request.secretOverrides() : Map.of();
        return SecretOverrideContext.callWith(
                overrides,
                () -> invocationService.invoke(
                        request.route(),
                        new InvocationRequest(
                                request.sessionId(),
                                request.channelId(),
                                request.capability(),
                                request.input())));
    }

    /**
     * Streaming SSE (026): eventos {@code chunk} e terminal {@code done}/{@code error}.
     * Desconexão do cliente cancela a geração (FR-007).
     */
    @PostMapping(value = "/invoke/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter invokeStream(@RequestBody InvokeRequest request) {
        SseEmitter emitter = new SseEmitter(300_000L);
        AtomicBoolean cancelled = new AtomicBoolean(false);
        emitter.onCompletion(() -> cancelled.set(true));
        emitter.onTimeout(() -> cancelled.set(true));
        emitter.onError(ex -> cancelled.set(true));

        InvocationRequest invocationRequest = new InvocationRequest(
                request.sessionId(), request.channelId(), request.capability(), request.input());

        Map<String, String> streamOverrides =
                request.secretOverrides() != null ? request.secretOverrides() : Map.of();
        streamExecutor.execute(() -> {
            try {
                SecretOverrideContext.callWith(streamOverrides, () -> {
                    invocationService.invokeStream(
                            request.route(),
                            invocationRequest,
                            new StreamSink() {
                                @Override
                                public void onChunk(String text) {
                                    try {
                                        emitter.send(SseEmitter.event().name("chunk").data(Map.of("text", text)));
                                    } catch (IOException e) {
                                        cancelled.set(true);
                                    }
                                }

                                @Override
                                public void onTerminal(InvocationResult result) {
                                    try {
                                        String event = result.success() ? "done" : "error";
                                        emitter.send(SseEmitter.event().name(event).data(result));
                                        emitter.complete();
                                    } catch (IOException e) {
                                        emitter.completeWithError(e);
                                    }
                                }
                            },
                            cancelled::get);
                    return null;
                });
            } catch (Exception e) {
                emitter.completeWithError(e);
            }
        });
        return emitter;
    }

    @GetMapping("/circuit-status")
    public List<ProviderCircuitSnapshot> circuitStatus() {
        return invocationService.circuitSnapshots();
    }

    /** Só usado para exibição — nunca o valor completo (FR-014): 3 primeiros + 4 últimos caracteres. */
    private static String mask(String secret) {
        if (secret.length() <= 7) {
            return "...";
        }
        return secret.substring(0, 3) + "..." + secret.substring(secret.length() - 4);
    }

    @ExceptionHandler(ProviderNotFoundException.class)
    public ResponseEntity<Map<String, String>> handleNotFound(ProviderNotFoundException e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("error", e.getMessage()));
    }

    @ExceptionHandler(RouteNotFoundException.class)
    public ResponseEntity<Map<String, String>> handleRouteNotFound(RouteNotFoundException e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("error", e.getMessage()));
    }

    @ExceptionHandler(ProviderInUseException.class)
    public ResponseEntity<Map<String, String>> handleInUse(ProviderInUseException e) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of("error", e.getMessage()));
    }

    @ExceptionHandler(ProviderProfileValidationException.class)
    public ResponseEntity<Map<String, Object>> handleValidation(ProviderProfileValidationException e) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", "perfil inválido", "details", e.errors()));
    }

    @ExceptionHandler(UnsupportedProviderTypeException.class)
    public ResponseEntity<Map<String, String>> handleUnsupportedType(UnsupportedProviderTypeException e) {
        return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY).body(Map.of("error", e.getMessage()));
    }

    /** Origem de canal não resolvível / UUID inválido com channelId (issue #40) — não aciona fallback. */
    @ExceptionHandler(ChannelOriginUnresolvedException.class)
    public ResponseEntity<Map<String, String>> handleChannelOriginUnresolved(ChannelOriginUnresolvedException e) {
        return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY).body(Map.of("error", e.getMessage()));
    }

    public record SetEnabledRequest(boolean enabled) {
    }

    /**
     * Entrada de invoke — sem {@code sourceType}: origem é resolvida no servidor a partir da sessão.
     * {@code secretOverrides} (opcional): mapa secretRef → valor para esta chamada (desktop os:); nunca logado.
     */
    public record InvokeRequest(
            @NotBlank String sessionId,
            String channelId,
            @NotBlank String route,
            @NotBlank String capability,
            @NotBlank String input,
            Map<String, String> secretOverrides) {
    }

    /** Body opcional de POST …/test com overrides de segredo (issue #64). */
    public record SecretOverridesBody(Map<String, String> secretOverrides) {
    }
}

