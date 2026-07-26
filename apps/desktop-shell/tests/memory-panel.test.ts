import { describe, expect, it, vi } from "vitest";
import { renderMemoryPanel, type MemoryPanelState } from "../src/memory-panel";

const baseState: MemoryPanelState = {
  sessionId: "s1",
  query: "",
  sourceTypeFilter: "",
  hits: [],
  items: [],
  error: null,
  busy: false,
};

describe("renderMemoryPanel", () => {
  it("shows no-session hint when sessionId is null", () => {
    const container = document.createElement("div");
    renderMemoryPanel(
      container,
      { ...baseState, sessionId: null },
      { onSearch: vi.fn(), onRefreshItems: vi.fn() },
    );
    expect(container.querySelector('[data-testid="memory-no-session"]')).toBeTruthy();
  });

  it("renders hits and items", () => {
    const container = document.createElement("div");
    renderMemoryPanel(
      container,
      {
        ...baseState,
        hits: [
          {
            eventId: "e1",
            type: "transcript.final.v2",
            text: "Spring Boot",
            sourceType: "system",
            channelId: "c1",
            occurredAt: "2026-07-26T10:00:00Z",
          },
        ],
        items: [
          {
            kind: "DECISION",
            text: "Decidimos usar Postgres",
            eventId: "e2",
            sourceType: "system",
            occurredAt: "2026-07-26T10:10:00Z",
          },
        ],
      },
      { onSearch: vi.fn(), onRefreshItems: vi.fn() },
    );
    expect(container.querySelector('[data-testid="memory-hit"]')?.textContent).toContain("Spring");
    expect(container.querySelector('[data-testid="memory-item"]')?.textContent).toContain("DECISION");
  });

  it("wires search button", () => {
    const container = document.createElement("div");
    const onSearch = vi.fn();
    renderMemoryPanel(container, baseState, { onSearch, onRefreshItems: vi.fn() });
    const input = container.querySelector<HTMLInputElement>('[data-testid="memory-search-input"]')!;
    input.value = "java";
    container.querySelector<HTMLButtonElement>('[data-testid="memory-search-button"]')?.click();
    expect(onSearch).toHaveBeenCalledWith("java", "");
  });
});
