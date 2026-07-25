package ai.assistanthub.core.provider;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * Espelha o enum {@code type} de {@code $defs/provider} em contracts/ai-provider-profile.v1.schema.json,
 * mais {@link #FAKE} — um valor interno (fora do schema v1, por isso nunca aceito por
 * {@link ProviderProfileValidator} em um perfil real) usado só para construir o
 * {@link FakeProviderAdapter} diretamente em código de teste (FR-009), sem exigir SDK/rede
 * externa nem passar pela validação do perfil declarativo.
 */
public enum ProviderType {
    OPENAI_COMPATIBLE("openai-compatible"),
    ANTHROPIC("anthropic"),
    GEMINI("gemini"),
    CUSTOM_HTTP("custom-http"),
    FAKE("fake");

    private final String wireValue;

    ProviderType(String wireValue) {
        this.wireValue = wireValue;
    }

    @JsonValue
    public String wireValue() {
        return wireValue;
    }

    @JsonCreator
    public static ProviderType fromWireValue(String wireValue) {
        for (ProviderType type : values()) {
            if (type.wireValue.equals(wireValue)) {
                return type;
            }
        }
        throw new IllegalArgumentException("type de provedor desconhecido: " + wireValue);
    }
}
