package ai.assistanthub.core.provider;

import com.fasterxml.jackson.annotation.JsonInclude.Include;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Valida um {@link ProviderProfile} contra contracts/ai-provider-profile.v1.schema.json (fonte
 * única, P4) e contra regras de negócio que o JSON Schema não expressa sozinho: {@code id} de
 * provedor único e rotas sem referência pendente a um {@code id} inexistente (FR-002, Edge
 * Cases da spec).
 */
@Component
public class ProviderProfileValidator {

    private static final String SCHEMA_RESOURCE = "/contracts/ai-provider-profile.v1.schema.json";

    private final JsonSchema schema;
    private final ObjectMapper objectMapper;

    public ProviderProfileValidator(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper.copy().setSerializationInclusion(Include.NON_NULL);
        JsonSchemaFactory factory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012);
        try (InputStream in = getClass().getResourceAsStream(SCHEMA_RESOURCE)) {
            if (in == null) {
                throw new IllegalStateException("Schema não encontrado no classpath: " + SCHEMA_RESOURCE);
            }
            this.schema = factory.getSchema(in);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /** @throws ProviderProfileValidationException se o perfil violar o schema ou as regras de negócio acima. */
    public void validate(ProviderProfile profile) {
        List<String> errors = new ArrayList<>();

        JsonNode profileJson = objectMapper.valueToTree(profile);
        for (ValidationMessage message : schema.validate(profileJson)) {
            errors.add(message.getMessage());
        }

        Set<String> providerIds = new HashSet<>();
        for (Provider provider : profile.providers()) {
            if (!providerIds.add(provider.id())) {
                errors.add("id de provedor duplicado: " + provider.id());
            }
        }

        for (Map.Entry<String, ProviderRoute> entry : profile.routes().entrySet()) {
            ProviderRoute route = entry.getValue();
            if (route.primary() != null && !providerIds.contains(route.primary())) {
                errors.add("rota '" + entry.getKey() + "' referencia provider inexistente: " + route.primary());
            }
            for (String fallbackId : route.fallbacks()) {
                if (!providerIds.contains(fallbackId)) {
                    errors.add("rota '" + entry.getKey() + "' referencia fallback inexistente: " + fallbackId);
                }
            }
        }

        if (!errors.isEmpty()) {
            throw new ProviderProfileValidationException(errors);
        }
    }

    /** Usado por {@link ProviderProfileStore} para converter o perfil validado em um mapa serializável em YAML. */
    Map<String, Object> toMap(ProviderProfile profile) {
        return objectMapper.convertValue(profile, new TypeReference<Map<String, Object>>() {
        });
    }

    /** Usado por {@link ProviderProfileStore} para converter o mapa lido do YAML de volta em um perfil tipado. */
    ProviderProfile fromMap(Map<String, Object> raw) {
        return objectMapper.convertValue(raw, ProviderProfile.class);
    }
}
