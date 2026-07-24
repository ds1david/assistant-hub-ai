// Painel do agent Windows — US3 (FR-006/FR-007/FR-008). Renderização pura + callbacks
// injetados para start/stop, testável sem Tauri real.
import type { AgentStatus } from "./api-client";
import { escapeHtml } from "./dom-utils";

export interface AgentPanelCallbacks {
  onStart: () => void;
  onStop: () => void;
}

export function renderAgentPanel(
  container: HTMLElement,
  status: AgentStatus,
  callbacks: AgentPanelCallbacks,
): void {
  const statusLabel = status.running ? "ativo" : "parado";
  const errorHtml = status.lastError
    ? `<p class="agent-error" data-testid="agent-error">${escapeHtml(status.lastError)}</p>`
    : "";

  let actionHtml: string;
  if (status.running && status.controlMode === "Direct") {
    actionHtml = '<button type="button" data-testid="agent-stop-button">Parar agent</button>';
  } else if (!status.running && status.controlMode === "Direct") {
    actionHtml = '<button type="button" data-testid="agent-start-button">Iniciar agent</button>';
  } else {
    // ControlMode "Guided" — orientação textual reproduzível (FR-007).
    actionHtml =
      '<p class="agent-guidance" data-testid="agent-guidance">Rode manualmente: ' +
      `<code>${escapeHtml(status.guidanceCommand)}</code></p>`;
  }

  container.innerHTML = `
    <p class="agent-status" data-testid="agent-status" data-running="${status.running}">
      Agent Windows: ${statusLabel}
    </p>
    ${errorHtml}
    ${actionHtml}
  `;

  container.querySelector('[data-testid="agent-start-button"]')?.addEventListener("click", () => {
    callbacks.onStart();
  });
  container.querySelector('[data-testid="agent-stop-button"]')?.addEventListener("click", () => {
    callbacks.onStop();
  });
}
