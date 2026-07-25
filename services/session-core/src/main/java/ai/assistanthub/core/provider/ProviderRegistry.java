package ai.assistanthub.core.provider;

import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Estado em memória do {@link ProviderProfile} vigente, recarregado a cada escrita bem-sucedida
 * em {@link ProviderProfileStore} — sem exigir reinício do processo (FR-015).
 */
@Component
public class ProviderRegistry {

    private final ProviderProfileStore store;
    private final AtomicReference<ProviderProfile> current;

    public ProviderRegistry(ProviderProfileStore store) {
        this.store = store;
        this.current = new AtomicReference<>(store.load());
    }

    public ProviderProfile profile() {
        return current.get();
    }

    public List<Provider> providers() {
        return current.get().providers();
    }

    public Optional<Provider> findById(String id) {
        return providers().stream().filter(provider -> provider.id().equals(id)).findFirst();
    }

    public Optional<ProviderRoute> findRoute(String routeName) {
        return Optional.ofNullable(current.get().routes().get(routeName));
    }

    /** Recarrega o registry a partir do que está persistido em {@link ProviderProfileStore}. */
    public void reload() {
        current.set(store.load());
    }

    /**
     * Cria ou substitui (por {@code id}) um provedor no perfil vigente — valida, escreve
     * atomicamente e aplica o hot-reload na mesma chamada, sem exigir reinício (FR-015).
     */
    public synchronized Provider save(Provider provider) {
        List<Provider> providers = new ArrayList<>(current.get().providers());
        providers.removeIf(existing -> existing.id().equals(provider.id()));
        providers.add(provider);
        persistAndReload(new ProviderProfile(current.get().version(), providers, current.get().routes()));
        return provider;
    }

    /** @throws ProviderNotFoundException se {@code id} não existir. */
    public synchronized Provider setEnabled(String id, boolean enabled) {
        Provider existing = findById(id).orElseThrow(() -> new ProviderNotFoundException(id));
        Provider updated = new Provider(
                existing.id(), existing.label(), existing.type(), enabled, existing.baseUrl(),
                existing.authentication(), existing.defaults(), existing.capabilities());
        return save(updated);
    }

    /**
     * @throws ProviderNotFoundException se {@code id} não existir
     * @throws ProviderInUseException se {@code id} for referenciado por {@code primary} ou
     *         {@code fallbacks} de alguma rota do perfil vigente
     */
    public synchronized void remove(String id) {
        if (findById(id).isEmpty()) {
            throw new ProviderNotFoundException(id);
        }
        boolean referenced = current.get().routes().values().stream()
                .anyMatch(route -> id.equals(route.primary()) || route.fallbacks().contains(id));
        if (referenced) {
            throw new ProviderInUseException(id);
        }
        List<Provider> providers = new ArrayList<>(current.get().providers());
        providers.removeIf(existing -> existing.id().equals(id));
        persistAndReload(new ProviderProfile(current.get().version(), providers, current.get().routes()));
    }

    /** @throws ProviderProfileValidationException se o perfil resultante violar o schema/regras de negócio. */
    private void persistAndReload(ProviderProfile updated) {
        store.save(updated);
        current.set(updated);
    }
}
