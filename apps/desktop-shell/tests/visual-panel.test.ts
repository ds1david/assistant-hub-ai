import { describe, expect, it, vi } from "vitest";
import { renderVisualPanel } from "../src/visual-panel";

describe("renderVisualPanel", () => {
  it("disables capture without consent", () => {
    const container = document.createElement("div");
    renderVisualPanel(
      container,
      {
        sessionId: "s1",
        consent: false,
        draftOcr: "hello",
        frames: [],
        error: null,
        busy: false,
      },
      {
        onConsentChange: vi.fn(),
        onDraftChange: vi.fn(),
        onCapture: vi.fn(),
        onRefresh: vi.fn(),
      },
    );
    expect(
      container.querySelector<HTMLButtonElement>('[data-testid="visual-capture"]')?.disabled,
    ).toBe(true);
  });

  it("wires capture when consent on", () => {
    const container = document.createElement("div");
    const onCapture = vi.fn();
    renderVisualPanel(
      container,
      {
        sessionId: "s1",
        consent: true,
        draftOcr: "Decidimos usar Spring",
        frames: [
          {
            eventId: "e1",
            occurredAt: "2026-07-26T12:00:00Z",
            ocrText: "text",
            masked: false,
          },
        ],
        error: null,
        busy: false,
      },
      {
        onConsentChange: vi.fn(),
        onDraftChange: vi.fn(),
        onCapture,
        onRefresh: vi.fn(),
      },
    );
    expect(container.querySelector('[data-testid="visual-frame"]')).toBeTruthy();
    container.querySelector<HTMLButtonElement>('[data-testid="visual-capture"]')?.click();
    expect(onCapture).toHaveBeenCalled();
  });
});
