package ai.assistanthub.core.provider;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/** Espelha o enum {@code authentication.mode} de contracts/ai-provider-profile.v1.schema.json. */
public enum AuthenticationMode {
    NONE("none"),
    BEARER("bearer"),
    API_KEY("api-key");

    private final String wireValue;

    AuthenticationMode(String wireValue) {
        this.wireValue = wireValue;
    }

    @JsonValue
    public String wireValue() {
        return wireValue;
    }

    @JsonCreator
    public static AuthenticationMode fromWireValue(String wireValue) {
        for (AuthenticationMode mode : values()) {
            if (mode.wireValue.equals(wireValue)) {
                return mode;
            }
        }
        throw new IllegalArgumentException("modo de autenticação desconhecido: " + wireValue);
    }
}
