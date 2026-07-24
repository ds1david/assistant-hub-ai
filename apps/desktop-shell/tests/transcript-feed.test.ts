import { describe, expect, it } from "vitest";
import { renderTranscriptFeed } from "../src/transcript-feed";
import type { TranscriptFeedEntry } from "../src/api-client";

function entry(overrides: Partial<TranscriptFeedEntry>): TranscriptFeedEntry {
  return {
    eventId: "e1",
    channelId: "mic-1",
    sourceType: "microphone",
    label: "Microfone",
    text: "ola",
    kind: "Final",
    occurredAt: "2026-01-01T00:00:01Z",
    ...overrides,
  };
}

describe("renderTranscriptFeed", () => {
  it("renders entries in chronological order regardless of input order (SC-002)", () => {
    const container = document.createElement("div");
    const entries = [
      entry({ eventId: "e2", text: "segundo", occurredAt: "2026-01-01T00:00:05Z" }),
      entry({ eventId: "e1", text: "primeiro", occurredAt: "2026-01-01T00:00:01Z" }),
    ];

    renderTranscriptFeed(container, entries);

    const texts = Array.from(
      container.querySelectorAll('[data-testid="feed-entry"] .feed-text'),
    ).map((el) => el.textContent);
    expect(texts).toEqual(["primeiro", "segundo"]);
  });

  it("never mixes text from different channels into one entry (FR-004)", () => {
    const container = document.createElement("div");
    const entries = [
      entry({
        eventId: "e1",
        channelId: "mic-1",
        text: "do microfone",
        occurredAt: "2026-01-01T00:00:01Z",
      }),
      entry({
        eventId: "e2",
        channelId: "sys-1",
        label: "Sistema",
        text: "do sistema",
        occurredAt: "2026-01-01T00:00:02Z",
      }),
    ];

    renderTranscriptFeed(container, entries);

    const items = container.querySelectorAll('[data-testid="feed-entry"]');
    expect(items).toHaveLength(2);
    expect(items[0].getAttribute("data-channel-id")).toBe("mic-1");
    expect(items[0].querySelector(".feed-text")?.textContent).toBe("do microfone");
    expect(items[1].getAttribute("data-channel-id")).toBe("sys-1");
    expect(items[1].querySelector(".feed-text")?.textContent).toBe("do sistema");
  });

  it("escapes transcript text before injecting into the DOM", () => {
    const container = document.createElement("div");
    renderTranscriptFeed(container, [entry({ text: "<script>alert(1)</script>" })]);

    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector(".feed-text")?.textContent).toBe("<script>alert(1)</script>");
  });

  it("shows an empty state when there are no entries yet", () => {
    const container = document.createElement("div");
    renderTranscriptFeed(container, []);

    expect(container.querySelector('[data-testid="feed-empty"]')).not.toBeNull();
  });
});
