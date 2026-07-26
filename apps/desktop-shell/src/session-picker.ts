// Lista / criar / selecionar sessão (FR-026 / FR-027 / FR-028 / 021).
import type { SessionSummary } from "./api-client";
import { escapeHtml } from "./dom-utils";
import { isSelectableSessionId } from "./session-selection";

export interface SessionPickerView {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  error: string | null;
  busy?: boolean;
}

export interface SessionPickerCallbacks {
  onSelect: (sessionId: string) => void;
  onCreate: () => void;
  onRefresh?: () => void;
}

export function renderSessionPicker(
  container: HTMLElement,
  view: SessionPickerView,
  callbacks: SessionPickerCallbacks,
): void {
  const active = view.activeSessionId
    ? `<p data-testid="session-active-id">Sessão ativa: <code>${escapeHtml(view.activeSessionId)}</code></p>`
    : `<p data-testid="session-active-id" class="session-none">Nenhuma sessão selecionada — escolha ou crie uma.</p>`;

  const error = view.error
    ? `<p class="session-error" data-testid="session-list-error">${escapeHtml(view.error)}</p>`
    : "";

  const items =
    view.sessions.length === 0
      ? `<li class="session-empty" data-testid="session-list-empty">Lista vazia. Crie uma nova sessão.</li>`
      : view.sessions
          .map((s) => {
            const selected = s.id === view.activeSessionId ? "session-selected" : "";
            const title = escapeHtml(s.title || "(sem título)");
            return `<li class="${selected}">
              <button type="button" data-action="select" data-session-id="${escapeHtml(s.id)}"
                data-testid="session-item">
                ${title} <code>${escapeHtml(s.id.slice(0, 8))}…</code>
              </button>
            </li>`;
          })
          .join("");

  container.innerHTML = `
    <section class="session-picker" data-testid="session-picker" aria-label="Sessões">
      <header>
        <h2>Sessão</h2>
        <div class="session-actions">
          <button type="button" data-action="create" data-testid="session-create"
            ${view.busy ? "disabled" : ""}>Criar sessão</button>
          ${
            callbacks.onRefresh
              ? `<button type="button" data-action="refresh" data-testid="session-refresh">Atualizar lista</button>`
              : ""
          }
        </div>
      </header>
      ${active}
      ${error}
      <ul class="session-list" data-testid="session-list">${items}</ul>
    </section>
  `;

  container.querySelector('[data-action="create"]')?.addEventListener("click", () => {
    callbacks.onCreate();
  });
  container.querySelector('[data-action="refresh"]')?.addEventListener("click", () => {
    callbacks.onRefresh?.();
  });
  container.querySelectorAll<HTMLButtonElement>('[data-action="select"]').forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-session-id");
      if (id && isSelectableSessionId(id)) {
        callbacks.onSelect(id);
      }
    });
  });
}
