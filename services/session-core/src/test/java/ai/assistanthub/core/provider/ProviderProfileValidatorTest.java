package ai.assistanthub.core.provider;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ProviderProfileValidatorTest {

    private final ProviderProfileValidator validator = new ProviderProfileValidator(new ObjectMapper());

    private Provider provider(String id) {
        return new Provider(
                id, "Fake " + id, ProviderType.OPENAI_COMPATIBLE, true,
                "http://fake.invalid",
                new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                new ProviderDefaults("fake-model", null, null, null, 5000),
                Set.of("chat"));
    }

    @Test
    void acceptsValidProfile() {
        ProviderProfile profile = new ProviderProfile(1, List.of(provider("fake-1")), Map.of());

        assertThatCode(() -> validator.validate(profile)).doesNotThrowAnyException();
    }

    @Test
    void rejectsProfileMissingRequiredField() {
        Provider invalid = new Provider(
                "fake-1", "Fake", ProviderType.OPENAI_COMPATIBLE, true,
                null, // baseUrl obrigatório pelo schema
                new ProviderAuthentication(AuthenticationMode.NONE, null, null),
                new ProviderDefaults("fake-model", null, null, null, 5000),
                Set.of("chat"));
        ProviderProfile profile = new ProviderProfile(1, List.of(invalid), Map.of());

        assertThatThrownBy(() -> validator.validate(profile))
                .isInstanceOf(ProviderProfileValidationException.class);
    }

    @Test
    void rejectsDuplicateProviderId() {
        ProviderProfile profile = new ProviderProfile(1, List.of(provider("dup"), provider("dup")), Map.of());

        assertThatThrownBy(() -> validator.validate(profile))
                .isInstanceOf(ProviderProfileValidationException.class)
                .satisfies(exception -> assertThat(((ProviderProfileValidationException) exception).errors())
                        .anyMatch(message -> message.contains("duplicado")));
    }

    @Test
    void rejectsRouteReferencingUnknownProvider() {
        ProviderProfile profile = new ProviderProfile(
                1,
                List.of(provider("fake-1")),
                Map.of("chat-route", new ProviderRoute("does-not-exist", List.of())));

        assertThatThrownBy(() -> validator.validate(profile))
                .isInstanceOf(ProviderProfileValidationException.class)
                .satisfies(exception -> assertThat(((ProviderProfileValidationException) exception).errors())
                        .anyMatch(message -> message.contains("does-not-exist")));
    }

    @Test
    void rejectsRouteReferencingUnknownFallback() {
        ProviderProfile profile = new ProviderProfile(
                1,
                List.of(provider("fake-1")),
                Map.of("chat-route", new ProviderRoute("fake-1", List.of("missing-fallback"))));

        assertThatThrownBy(() -> validator.validate(profile))
                .isInstanceOf(ProviderProfileValidationException.class)
                .satisfies(exception -> assertThat(((ProviderProfileValidationException) exception).errors())
                        .anyMatch(message -> message.contains("missing-fallback")));
    }
}
