package ai.assistanthub.core.provider;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class CompositeSecretResolverTest {

    @Test
    void prefersRequestOverrideForOsRef() {
        CompositeSecretResolver resolver = new CompositeSecretResolver(new EnvSecretResolver());
        String ref = "os:assistant-hub/providers/p1";
        assertThat(resolver.resolve(ref)).isEmpty();

        String value = SecretOverrideContext.callWith(
                Map.of(ref, "sk-from-desktop"),
                () -> resolver.resolve(ref).orElse(null));
        assertThat(value).isEqualTo("sk-from-desktop");
        // cleared after call
        assertThat(resolver.resolve(ref)).isEmpty();
    }

    @Test
    void stillResolvesEnv() {
        CompositeSecretResolver resolver = new CompositeSecretResolver(new EnvSecretResolver());
        // env without variable → empty (no throw)
        assertThat(resolver.resolve("env:ASSISTANT_HUB_TEST_NO_SUCH_VAR_XYZ")).isEmpty();
    }
}
