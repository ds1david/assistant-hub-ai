import { describe, expect, it, vi } from "vitest";
import { renderAgentPanel } from "../src/agent-panel";
import type { AgentStatus } from "../src/api-client";

describe("renderAgentPanel", () => {
  it("shows a direct start action when stopped and control is direct (FR-006/FR-007)", () => {
    const container = document.createElement("div");
    const status: AgentStatus = {
      running: false,
      controlMode: "Direct",
      guidanceCommand: "assistant-hub-audio run --session s1 --profile perfil.yaml",
      lastError: null,
    };
    const onStart = vi.fn();

    renderAgentPanel(container, status, { onStart, onStop: vi.fn() });
    container.querySelector<HTMLButtonElement>('[data-testid="agent-start-button"]')?.click();

    expect(onStart).toHaveBeenCalledOnce();
  });

  it("shows guided textual instruction when control mode is not direct (FR-007)", () => {
    const container = document.createElement("div");
    const status: AgentStatus = {
      running: false,
      controlMode: "Guided",
      guidanceCommand: "assistant-hub-audio run --session s1 --profile perfil.yaml",
      lastError: null,
    };

    renderAgentPanel(container, status, { onStart: vi.fn(), onStop: vi.fn() });

    const guidance = container.querySelector('[data-testid="agent-guidance"]');
    expect(guidance).not.toBeNull();
    expect(guidance?.textContent).toContain(
      "assistant-hub-audio run --session s1 --profile perfil.yaml",
    );
    expect(container.querySelector('[data-testid="agent-start-button"]')).toBeNull();
  });

  it("shows a specific error message, never a generic one, when present (FR-008)", () => {
    const container = document.createElement("div");
    const status: AgentStatus = {
      running: false,
      controlMode: "Direct",
      guidanceCommand: "assistant-hub-audio run --session s1 --profile perfil.yaml",
      lastError: "binário assistant-hub-audio não encontrado",
    };

    renderAgentPanel(container, status, { onStart: vi.fn(), onStop: vi.fn() });

    expect(container.querySelector('[data-testid="agent-error"]')?.textContent).toBe(
      "binário assistant-hub-audio não encontrado",
    );
  });
});
