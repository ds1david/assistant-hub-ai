// Painel do agent Windows — sessionId UI↔agent, mismatch, restart CTA (020).
import type { AgentStatus } from "./api-client";
import { escapeHtml } from "./dom-utils";
import { resolveAlignment, type AlignmentState } from "./session-alignment";

export interface AgentPanelCallbacks {
  onStart: () => void;
  onStop: () => void;
  onRestart: () => void;
}

export interface AgentPanelView {
  status: AgentStatus;
  activeSessionId: string | null;
}

export function renderAgentPanel(
  container: HTMLElement,
  view: AgentPanelView | AgentStatus,
  callbacks: AgentPanelCallbacks | (Omit<AgentPanelCallbacks, "onRestart"> & { onRestart?: () => void }),
): void {
  // Compat: testes legados passavam só AgentStatus.
  const status: AgentStatus =
    "status" in view && view.status ? view.status : (view as AgentStatus);
  const activeSessionId =
    "activeSessionId" in view ? view.activeSessionId : null;
  const onRestart = callbacks.onRestart ?? (() => {});

  const alignment = resolveAlignment(activeSessionId, {
    running: status.running,
    agentSessionId: status.agentSessionId ?? null,
  });

  const statusLabel = status.running ? "ativo" : "parado";
  const errorHtml = status.lastError
    ? `<p class="agent-error" data-testid="agent-error">${escapeHtml(status.lastError)}</p>`
    : "";

  const uiSessionHtml = activeSessionId
    ? `<p class="agent-ui-session" data-testid="ui-session-id">Sessão ativa (UI): <code>${escapeHtml(activeSessionId)}</code></p>`
    : `<p class="agent-ui-session" data-testid="ui-session-id">Nenhuma sessão ativa — selecione ou crie uma.</p>`;

  const agentSessionLabel = !status.running
    ? "parado"
    : status.agentSessionId
      ? status.agentSessionId
      : "desconhecida";
  const agentSessionHtml = `<p class="agent-session" data-testid="agent-session-id">Sessão do agent: <code>${escapeHtml(agentSessionLabel)}</code></p>`;

  const mismatchHtml =
    alignment === "mismatched"
      ? `<p class="agent-mismatch" data-testid="session-mismatch-banner" role="alert">
          Sessão do agent diferente da sessão ativa. Use «Reiniciar agent com sessão ativa»
          (modo direto) ou pare o agent manualmente e inicie com o id da UI.
        </p>`
      : "";

  let actionHtml = "";
  const canStart =
    !status.running &&
    status.controlMode === "Direct" &&
    Boolean(activeSessionId);
  const canStop = status.running && status.controlMode === "Direct";
  const canRestart =
    status.running &&
    status.controlMode === "Direct" &&
    alignment === "mismatched" &&
    Boolean(activeSessionId);

  if (!activeSessionId && !status.running) {
    actionHtml =
      '<p class="agent-no-session" data-testid="agent-no-session-hint">Selecione ou crie uma sessão para iniciar o agent com o id correto.</p>';
  } else if (canStop) {
    actionHtml =
      '<button type="button" data-testid="agent-stop-button">Parar agent</button>';
    if (canRestart) {
      actionHtml +=
        ' <button type="button" data-testid="agent-restart-active-button">Reiniciar agent com sessão ativa</button>';
    }
  } else if (canStart) {
    actionHtml =
      '<button type="button" data-testid="agent-start-button">Iniciar agent</button>';
  } else if (status.running && status.controlMode === "Guided") {
    actionHtml =
      '<p class="agent-guidance" data-testid="agent-guidance">Rode manualmente: ' +
      `<code>${escapeHtml(status.guidanceCommand)}</code></p>` +
      '<p class="agent-manual-stop" data-testid="agent-manual-stop-hint">' +
      "Agent iniciado fora do shell: pare o processo manualmente e então inicie com o comando acima " +
      "(sessionId da UI). O shell não encerra processos externos.</p>";
  } else {
    actionHtml =
      '<p class="agent-guidance" data-testid="agent-guidance">Rode manualmente: ' +
      `<code>${escapeHtml(status.guidanceCommand)}</code></p>`;
  }

  container.innerHTML = `
    <section class="agent-panel-inner" data-testid="agent-panel-root" data-alignment="${alignment}">
      <p class="agent-status" data-testid="agent-status" data-running="${status.running}">
        Agent Windows: ${statusLabel}
      </p>
      ${uiSessionHtml}
      ${agentSessionHtml}
      ${mismatchHtml}
      ${errorHtml}
      ${actionHtml}
    </section>
  `;

  container.querySelector('[data-testid="agent-start-button"]')?.addEventListener("click", () => {
    callbacks.onStart();
  });
  container.querySelector('[data-testid="agent-stop-button"]')?.addEventListener("click", () => {
    callbacks.onStop();
  });
  container
    .querySelector('[data-testid="agent-restart-active-button"]')
    ?.addEventListener("click", () => {
      onRestart();
    });
}

export type { AlignmentState };
