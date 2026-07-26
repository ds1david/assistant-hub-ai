package ai.assistanthub.core.memory;

import ai.assistanthub.sdk.HubEvent;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Extração determinística de decisões/ações/compromissos a partir de {@code payload.text}
 * (issue #65). Sem LLM/GPU — palavras-chave pt/en.
 */
public final class HeuristicMemoryExtractor {

    private HeuristicMemoryExtractor() {
    }

    public static List<MemoryItem> extract(List<HubEvent> events) {
        List<MemoryItem> items = new ArrayList<>();
        for (HubEvent event : events) {
            String text = textOf(event);
            if (text == null || text.isBlank()) {
                continue;
            }
            MemoryItemKind kind = classify(text);
            if (kind == null) {
                continue;
            }
            items.add(new MemoryItem(
                    kind,
                    text.trim(),
                    event.id(),
                    sourceTypeOf(event),
                    event.occurredAt()));
        }
        return items;
    }

    static MemoryItemKind classify(String text) {
        String lower = text.toLowerCase(Locale.ROOT);
        // Commitment first (more specific phrases)
        if (containsAny(lower,
                "me comprometo",
                "eu me comprometo",
                "prazo até",
                "deadline",
                "entrego até",
                "i commit to",
                "i will deliver by",
                "by friday",
                "até sexta")) {
            return MemoryItemKind.COMMITMENT;
        }
        if (containsAny(lower,
                "decidimos",
                "decidiu-se",
                "ficou decidido",
                "we decided",
                "we agreed",
                "agreement:",
                "decisão:",
                "a decisão é")) {
            return MemoryItemKind.DECISION;
        }
        if (containsAny(lower,
                "vamos ",
                "ação:",
                "action item",
                "action:",
                "todo:",
                "to-do:",
                "precisa fazer",
                "we need to",
                "next step",
                "próximo passo",
                "tarefa:")) {
            return MemoryItemKind.ACTION;
        }
        return null;
    }

    static String textOf(HubEvent event) {
        Map<String, Object> payload = event.payload();
        Object text = payload.get("text");
        return text == null ? null : String.valueOf(text);
    }

    static String sourceTypeOf(HubEvent event) {
        Map<String, String> correlation = event.correlation();
        if (correlation == null) {
            return null;
        }
        return correlation.get("sourceType");
    }

    private static boolean containsAny(String lower, String... needles) {
        for (String n : needles) {
            if (lower.contains(n)) {
                return true;
            }
        }
        return false;
    }
}
