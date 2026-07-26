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
    const fullId = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
    renderSessionPicker(
      container,
      {
        sessions: [session(fullId, "Sessão local")],
        activeSessionId: fullId,
        error: null,
      },
      { onSelect, onCreate: vi.fn() },
    );
    expect(container.querySelector('[data-testid="session-active-id"]')?.textContent).toContain(
      fullId,
    );
    const item = container.querySelector<HTMLButtonElement>('[data-testid="session-item"]');
    expect(item?.getAttribute("data-session-id")).toBe(fullId);
    item?.click();
    expect(onSelect).toHaveBeenCalledWith(fullId);
  });

  it("fires onSelect with full id when list has one item and active is null (SC-001)", () => {
    const container = document.createElement("div");
    const onSelect = vi.fn();
    const fullId = "11111111-2222-3333-4444-555555555555";
    renderSessionPicker(
      container,
      { sessions: [session(fullId, "Única")], activeSessionId: null, error: null },
      { onSelect, onCreate: vi.fn() },
    );
    expect(container.querySelector('[data-testid="session-active-id"]')?.textContent).toMatch(
      /Nenhuma sessão selecionada/i,
    );
    container.querySelector<HTMLButtonElement>('[data-testid="session-item"]')?.click();
    expect(onSelect).toHaveBeenCalledWith(fullId);
  });

  it("marks only the active item as selected when switching S→T", () => {
    const container = document.createElement("div");
    const s = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
    const t = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff";
    renderSessionPicker(
      container,
      { sessions: [session(s, "S"), session(t, "T")], activeSessionId: t, error: null },
      { onSelect: vi.fn(), onCreate: vi.fn() },
    );
    const items = container.querySelectorAll('[data-testid="session-item"]');
    expect(items).toHaveLength(2);
    expect(items[0].closest("li")?.classList.contains("session-selected")).toBe(false);
    expect(items[1].closest("li")?.classList.contains("session-selected")).toBe(true);
    expect(container.querySelector('[data-testid="session-active-id"]')?.textContent).toContain(t);
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
