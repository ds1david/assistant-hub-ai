package ai.assistanthub.core.transcript;

import com.fasterxml.jackson.databind.JsonNode;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.Set;

/**
 * Valida o JSON bruto recebido do feed de transcrição contra
 * contracts/transcript-event.v2.schema.json (fonte única, P4) — sem duplicar as regras do
 * contrato em código Java.
 */
@Component
public class TranscriptEventValidator {

    private static final String SCHEMA_RESOURCE = "/contracts/transcript-event.v2.schema.json";

    private final JsonSchema schema;

    public TranscriptEventValidator() {
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

    public Set<ValidationMessage> validate(JsonNode event) {
        return schema.validate(event);
    }
}
