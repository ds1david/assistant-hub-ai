// UI do painel Diagnóstico (issue #67).
import type { DiagnosticSnapshot } from "./diagnostics";
import { escapeHtml } from "./dom-utils";

export interface DiagnosticsPanelState {
  snapshot: DiagnosticSnapshot | null;
  busy: boolean;
  error: string | null;
  copyFeedback: string | null;
}

export interface DiagnosticsPanelCallbacks {
  onRefresh: () => void;
  onCopyReport: () => void;
}

export function renderDiagnosticsPanel(
  container: HTMLElement,
  state: DiagnosticsPanelState,
  callbacks: DiagnosticsPanelCallbacks,
): void {
  const snap = state.snapshot;
  container.innerHTML = `
    <section class="diagnostics-panel" data-testid="diagnostics-panel">
      <header>
        <h2>Diagnóstico</h2>
        <p class="diag-hint">Saúde do stack local (session-core, STT, agent) — sem secrets</p>
      </header>
      <div class="diag-actions">
        <button type="button" data-testid="diag-refresh" ${state.busy ? "disabled" : ""}>
          ${state.busy ? "Atualizando…" : "Atualizar"}
        </button>
        <button type="button" data-testid="diag-copy" ${!snap || state.busy ? "disabled" : ""}>
          Copiar relatório
        </button>
        ${state.copyFeedback ? `<span data-testid="diag-copy-feedback">${escapeHtml(state.copyFeedback)}</span>` : ""}
      </div>
      ${state.error ? `<p class="session-error" data-testid="diag-error">${escapeHtml(state.error)}</p>` : ""}
      ${
        !snap
          ? `<p data-testid="diag-empty">Clique em Atualizar para coletar o estado.</p>`
          : renderSnapshot(snap)
      }
    </section>
  `;

  container.querySelector('[data-testid="diag-refresh"]')?.addEventListener("click", () => {
    callbacks.onRefresh();
  });
  container.querySelector('[data-testid="diag-copy"]')?.addEventListener("click", () => {
    callbacks.onCopyReport();
  });
}

function renderSnapshot(snap: DiagnosticSnapshot): string {
  const rows = snap.checks
    .map(
      (c) => `
    <li data-testid="diag-check" data-check-id="${escapeHtml(c.id)}" data-status="${escapeHtml(c.status)}">
      <strong class="diag-status diag-status-${escapeHtml(c.status)}">${escapeHtml(c.status.toUpperCase())}</strong>
      <span>${escapeHtml(c.label)}</span>
      <p class="diag-detail">${escapeHtml(c.detail)}</p>
      ${c.nextStep ? `<p class="diag-next" data-testid="diag-next">→ ${escapeHtml(c.nextStep)}</p>` : ""}
    </li>`,
    )
    .join("");
  return `
    <p class="diag-meta" data-testid="diag-generated">Gerado: ${escapeHtml(snap.generatedAt)}</p>
    <ul class="diag-check-list" data-testid="diag-check-list">${rows}</ul>
  `;
}
