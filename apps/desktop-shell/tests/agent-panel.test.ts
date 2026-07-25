import { describe, expect, it, vi } from "vitest";
import { renderAgentPanel } from "../src/agent-panel";
import type { AgentStatus } from "../src/api-client";

function baseStatus(over: Partial<AgentStatus> = {}): AgentStatus {
  return {
    running: false,
    controlMode: "Direct",
    guidanceCommand: "assistant-hub-audio run --session s1 --profile perfil.yaml",
    lastError: null,
    agentSessionId: null,
    agentSessionSource: "unknown",
    ...over,
  };
}

describe("renderAgentPanel", () => {
  it("shows start when stopped + Direct + active session (I1 / FR-001)", () => {
    const container = document.createElement("div");
    const onStart = vi.fn();
    renderAgentPanel(
      container,
      { status: baseStatus({ running: false, controlMode: "Direct" }), activeSessionId: "s1" },
      { onStart, onStop: vi.fn(), onRestart: vi.fn() },
    );
    container.querySelector<HTMLButtonElement>('[data-testid="agent-start-button"]')?.click();
    expect(onStart).toHaveBeenCalledOnce();
    expect(container.querySelector('[data-testid="ui-session-id"]')?.textContent).toContain("s1");
  });

  it("hides start and shows hint when no active session", () => {
    const container = document.createElement("div");
    renderAgentPanel(
      container,
      { status: baseStatus({ running: false, controlMode: "Direct" }), activeSessionId: null },
      { onStart: vi.fn(), onStop: vi.fn(), onRestart: vi.fn() },
    );
    expect(container.querySelector('[data-testid="agent-start-button"]')).toBeNull();
    expect(container.querySelector('[data-testid="agent-no-session-hint"]')).not.toBeNull();
  });

  it("shows mismatch banner and restart CTA when Direct + mismatched (FR-007/016)", () => {
    const container = document.createElement("div");
    const onRestart = vi.fn();
    renderAgentPanel(
      container,
      {
        status: baseStatus({
          running: true,
          controlMode: "Direct",
          agentSessionId: "old",
          agentSessionSource: "managed",
        }),
        activeSessionId: "new",
      },
      { onStart: vi.fn(), onStop: vi.fn(), onRestart },
    );
    expect(container.querySelector('[data-testid="session-mismatch-banner"]')).not.toBeNull();
    container
      .querySelector<HTMLButtonElement>('[data-testid="agent-restart-active-button"]')
      ?.click();
    expect(onRestart).toHaveBeenCalledOnce();
  });

  it("shows mismatch for cmdline-sourced agent session (FR-011b / I5)", () => {
    const container = document.createElement("div");
    renderAgentPanel(
      container,
      {
        status: baseStatus({
          running: true,
          controlMode: "Guided",
          agentSessionId: "from-ps",
          agentSessionSource: "cmdline",
        }),
        activeSessionId: "from-ui",
      },
      { onStart: vi.fn(), onStop: vi.fn(), onRestart: vi.fn() },
    );
    expect(container.querySelector('[data-testid="session-mismatch-banner"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="agent-session-id"]')?.textContent).toContain(
      "from-ps",
    );
  });

  it("does not show mismatch when ids match", () => {
    const container = document.createElement("div");
    renderAgentPanel(
      container,
      {
        status: baseStatus({
          running: true,
          controlMode: "Direct",
          agentSessionId: "same",
        }),
        activeSessionId: "same",
      },
      { onStart: vi.fn(), onStop: vi.fn(), onRestart: vi.fn() },
    );
    expect(container.querySelector('[data-testid="session-mismatch-banner"]')).toBeNull();
    expect(container.querySelector('[data-testid="agent-restart-active-button"]')).toBeNull();
  });

  it("does not show mismatch banner when agent is stopped", () => {
    const container = document.createElement("div");
    renderAgentPanel(
      container,
      {
        status: baseStatus({ running: false, agentSessionId: "x" }),
        activeSessionId: "y",
      },
      { onStart: vi.fn(), onStop: vi.fn(), onRestart: vi.fn() },
    );
    expect(container.querySelector('[data-testid="session-mismatch-banner"]')).toBeNull();
  });

  it("shows guided recovery without force-kill restart when running Guided (FR-015)", () => {
    const container = document.createElement("div");
    renderAgentPanel(
      container,
      {
        status: baseStatus({
          running: true,
          controlMode: "Guided",
          agentSessionId: "ext",
          guidanceCommand: "assistant-hub-audio run --session ui-id --profile perfil.yaml",
        }),
        activeSessionId: "ui-id",
      },
      { onStart: vi.fn(), onStop: vi.fn(), onRestart: vi.fn() },
    );
    expect(container.querySelector('[data-testid="agent-guidance"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="agent-manual-stop-hint"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="agent-restart-active-button"]')).toBeNull();
    expect(container.querySelector('[data-testid="agent-stop-button"]')).toBeNull();
  });

  it("shows a specific error message when present (FR-008 legacy)", () => {
    const container = document.createElement("div");
    renderAgentPanel(
      container,
      {
        status: baseStatus({
          lastError: "binário assistant-hub-audio não encontrado",
        }),
        activeSessionId: "s1",
      },
      { onStart: vi.fn(), onStop: vi.fn(), onRestart: vi.fn() },
    );
    expect(container.querySelector('[data-testid="agent-error"]')?.textContent).toBe(
      "binário assistant-hub-audio não encontrado",
    );
  });
});
