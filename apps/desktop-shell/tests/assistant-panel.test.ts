import { describe, expect, it, vi } from "vitest";
import { renderAssistantPanel } from "../src/assistant-panel";
import type { AssistantAutoView } from "../src/assistant-auto";
import { DEFAULT_ASSISTANT_PREFS } from "../src/assistant-prefs";

const emptyView: AssistantAutoView = {
  enabled: false,
  prefs: { ...DEFAULT_ASSISTANT_PREFS, enabledSourceTypes: ["system"] },
  turns: [],
  conflict: null,
  busy: false,
};

const callbacks = () => ({
  onToggleEnabled: vi.fn(),
  onToggleOrigin: vi.fn(),
  onInputModeChange: vi.fn(),
  onResolveConflict: vi.fn(),
});

describe("renderAssistantPanel", () => {
  it("renders empty guidance when there are no turns", () => {
    const container = document.createElement("div");
    renderAssistantPanel(container, emptyView, callbacks());
    expect(container.querySelector('[data-testid="assistant-empty"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="assistant-origin-system"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="assistant-input-mode"]')).toBeTruthy();
  });

  it("renders conflict actions and wires cancel/wait", () => {
    const container = document.createElement("div");
    const cbs = callbacks();
    const view: AssistantAutoView = {
      enabled: true,
      prefs: { autoEnabled: true, enabledSourceTypes: ["system"], inputMode: "question-only" },
      busy: true,
      turns: [
        {
          id: "t1",
          question: "P1?",
          eventId: "e1",
          channelId: null,
          status: "running",
          answer: null,
          error: null,
          providerId: null,
          latencyMs: null,
        },
      ],
      conflict: {
        runningTurnId: "t1",
        runningQuestion: "P1?",
        incoming: { eventId: "e2", text: "P2?", channelId: null, sourceType: "system" },
      },
    };

    renderAssistantPanel(container, view, cbs);

    expect(container.querySelector('[data-testid="assistant-conflict"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="assistant-conflict-running"]')?.textContent).toContain(
      "P1?",
    );
    container.querySelector<HTMLButtonElement>('[data-testid="assistant-conflict-cancel"]')?.click();
    expect(cbs.onResolveConflict).toHaveBeenCalledWith("cancel");
  });

  it("shows completed answer and queued status", () => {
    const container = document.createElement("div");
    renderAssistantPanel(
      container,
      {
        ...emptyView,
        turns: [
          {
            id: "t1",
            question: "Como faz?",
            eventId: "e1",
            channelId: "sys",
            status: "done",
            answer: "Assim.",
            error: null,
            providerId: "openai-gpt",
            latencyMs: 42,
          },
          {
            id: "t2",
            question: "E agora?",
            eventId: "e2",
            channelId: "sys",
            status: "queued",
            answer: null,
            error: null,
            providerId: null,
            latencyMs: null,
          },
        ],
      },
      callbacks(),
    );
    expect(container.querySelector('[data-testid="assistant-answer"]')?.textContent).toBe("Assim.");
    const turns = container.querySelectorAll('[data-testid="assistant-turn"]');
    // mais recente primeiro → t2 (queued) no topo
    expect(turns[0].getAttribute("data-status")).toBe("queued");
    expect(turns[1].getAttribute("data-status")).toBe("done");
  });

  it("escapes HTML in question/answer", () => {
    const container = document.createElement("div");
    renderAssistantPanel(
      container,
      {
        ...emptyView,
        turns: [
          {
            id: "t1",
            question: "<script>alert(1)</script>",
            eventId: "e1",
            channelId: null,
            status: "done",
            answer: "<b>x</b>",
            error: null,
            providerId: null,
            latencyMs: null,
          },
        ],
      },
      callbacks(),
    );
    expect(container.innerHTML).toContain("&lt;script&gt;");
    expect(container.innerHTML).not.toContain("<script>alert");
  });

  it("disables controls when controlsDisabled", () => {
    const container = document.createElement("div");
    renderAssistantPanel(
      container,
      {
        ...emptyView,
        controlsDisabled: true,
        sessionHint: "sem sessão",
      },
      callbacks(),
    );
    expect(container.querySelector<HTMLInputElement>('[data-testid="assistant-enabled"]')?.disabled).toBe(
      true,
    );
    expect(container.querySelector('[data-testid="assistant-session-hint"]')?.textContent).toContain(
      "sem sessão",
    );
  });

  it("wires origin and input mode callbacks", () => {
    const container = document.createElement("div");
    const cbs = callbacks();
    renderAssistantPanel(container, emptyView, cbs);
    const mic = container.querySelector<HTMLInputElement>('[data-testid="assistant-origin-microphone"]');
    if (mic) {
      mic.checked = true;
      mic.dispatchEvent(new Event("change"));
    }
    expect(cbs.onToggleOrigin).toHaveBeenCalledWith("microphone", true);
    const select = container.querySelector<HTMLSelectElement>('[data-testid="assistant-input-mode"]');
    if (select) {
      select.value = "question-only";
      select.dispatchEvent(new Event("change"));
    }
    expect(cbs.onInputModeChange).toHaveBeenCalledWith("question-only");
  });

  it("labels prior turn as concluded when no longer running (T042)", () => {
    const container = document.createElement("div");
    renderAssistantPanel(
      container,
      {
        enabled: true,
        prefs: { autoEnabled: true, enabledSourceTypes: ["system"], inputMode: "question-only" },
        busy: false,
        turns: [
          {
            id: "t1",
            question: "P1?",
            eventId: "e1",
            channelId: null,
            status: "done",
            answer: "ok",
            error: null,
            providerId: null,
            latencyMs: 1,
          },
        ],
        conflict: {
          runningTurnId: "t1",
          runningQuestion: "P1?",
          incoming: { eventId: "e2", text: "P2?", channelId: null, sourceType: "system" },
        },
      },
      callbacks(),
    );
    const conflict = container.querySelector('[data-testid="assistant-conflict"]');
    expect(conflict?.getAttribute("data-prior-status")).toBe("done");
    expect(container.querySelector('[data-testid="assistant-conflict-running"]')?.textContent).toContain(
      "Anterior concluída",
    );
    expect(container.querySelector('[data-testid="assistant-conflict-running"]')?.textContent).not.toContain(
      "Em execução",
    );
  });
});
