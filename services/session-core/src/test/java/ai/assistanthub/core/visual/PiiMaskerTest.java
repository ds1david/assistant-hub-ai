package ai.assistanthub.core.visual;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class PiiMaskerTest {

    @Test
    void masksEmailAndLeavesNormalText() {
        PiiMasker.MaskResult r = PiiMasker.mask("Contact jane.doe@example.com about Spring");
        assertThat(r.masked()).isTrue();
        assertThat(r.text()).contains("[email]");
        assertThat(r.text()).doesNotContain("jane.doe@example.com");
        assertThat(r.text()).contains("Spring");
    }

    @Test
    void masksCardLikeDigits() {
        PiiMasker.MaskResult r = PiiMasker.mask("card 4111111111111111 ok");
        assertThat(r.masked()).isTrue();
        assertThat(r.text()).contains("[card]");
        assertThat(r.text()).doesNotContain("4111111111111111");
    }

    @Test
    void emptyUnchanged() {
        assertThat(PiiMasker.mask("").masked()).isFalse();
        assertThat(PiiMasker.mask("hello world").masked()).isFalse();
    }
}
