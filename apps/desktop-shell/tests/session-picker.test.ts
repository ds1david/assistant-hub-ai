import { describe, expect, it, vi } from "vitest";
import { renderSessionPicker } from "../src/session-picker";
import type { SessionSummary } from "../src/api-client";

function session(id: string, title: string): SessionSummary {
  return {
    id,
    title,
    profileId: "interview-technical",
    status: "CREATED",
    createdAt: "2026-01-01T00:00:00Z",
    startedAt: null,
    endedAt: null,
  };
}

describe("renderSessionPicker", () => {
  it("shows empty list and create button", () => {
    const container = document.createElement("div");
    const onCreate = vi.fn();
    renderSessionPicker(
      container,
      { sessions: [], activeSessionId: null, error: null },
      { onSelect: vi.fn(), onCreate },
    );
    expect(container.querySelector('[data-testid="session-list-empty"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="session-create"]')).toBeTruthy();
    container.querySelector<HTMLButtonElement>('[data-testid="session-create"]')?.click();
    expect(onCreate).toHaveBeenCalled();
  });

  it("selects session and shows active id", () => {
    const container = document.createElement("div");
    const onSelect = vi.fn();
    renderSessionPicker(
      container,
      {
        sessions: [session("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "Sessão local")],
        activeSessionId: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        error: null,
      },
      { onSelect, onCreate: vi.fn() },
    );
    expect(container.querySelector('[data-testid="session-active-id"]')?.textContent).toContain(
      "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    );
    container.querySelector<HTMLButtonElement>('[data-testid="session-item"]')?.click();
    expect(onSelect).toHaveBeenCalledWith("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee");
  });

  it("shows list error", () => {
    const container = document.createElement("div");
    renderSessionPicker(
      container,
      { sessions: [], activeSessionId: null, error: "core down" },
      { onSelect: vi.fn(), onCreate: vi.fn() },
    );
    expect(container.querySelector('[data-testid="session-list-error"]')?.textContent).toContain(
      "core down",
    );
  });
});
