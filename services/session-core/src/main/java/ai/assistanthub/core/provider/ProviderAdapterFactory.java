package ai.assistanthub.core.provider;

import org.springframework.stereotype.Component;

import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Despacha por {@link Provider#type()}. Um {@code type} sem adaptador disponível (ex.:
 * {@code anthropic}, {@code gemini}, {@code custom-http} nesta fatia) resulta em
 * {@link #resolve(Provider)} vazio — o chamador rejeita a invocação com um erro de validação
 * claro, sem tentar chamar a rede (Edge Case da spec).
 */
@Component
public class ProviderAdapterFactory {

    private final Map<ProviderType, ProviderAdapter> adaptersByType;

    public ProviderAdapterFactory(List<TypedProviderAdapter> adapters) {
        this.adaptersByType = new EnumMap<>(ProviderType.class);
        for (TypedProviderAdapter adapter : adapters) {
            adaptersByType.put(adapter.supportedType(), adapter);
        }
    }

    public Optional<ProviderAdapter> resolve(Provider provider) {
        return Optional.ofNullable(adaptersByType.get(provider.type()));
    }

    /** Implementada por cada {@link ProviderAdapter} concreto para se anunciar ao factory. */
    public interface TypedProviderAdapter extends ProviderAdapter {
        ProviderType supportedType();
    }
}
