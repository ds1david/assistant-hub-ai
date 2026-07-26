// Painel Memory Hub R3.2 — busca + decisões/ações (issue #65).
import { escapeHtml } from "./dom-utils";

export interface MemorySearchHit {
  eventId: string;
  type: string;
  text: string;
  sourceType?: string | null;
  channelId?: string | null;
  occurredAt: string;
}

export interface MemoryItem {
  kind: string;
  text: string;
  eventId: string;
  sourceType?: string | null;
  occurredAt: string;
}

export interface MemoryPanelState {
  sessionId: string | null;
  query: string;
  sourceTypeFilter: "" | "system" | "microphone";
  hits: MemorySearchHit[];
  items: MemoryItem[];
  error: string | null;
  busy: boolean;
}

export interface MemoryPanelCallbacks {
  onSearch: (query: string, sourceType: "" | "system" | "microphone") => void;
  onRefreshItems: () => void;
}

export function renderMemoryPanel(
  container: HTMLElement,
  state: MemoryPanelState,
  callbacks: MemoryPanelCallbacks,
): void {
  const disabled = !state.sessionId || state.busy;
  const disabledAttr = disabled ? "disabled" : "";

  container.innerHTML = `
    <section class="memory-panel" data-testid="memory-panel">
      <header>
        <h2>Memory Hub</h2>
        <p class="memory-hint">Busca e decisões/ações da sessão ativa (R3.2)</p>
      </header>
      ${
        !state.sessionId
          ? `<p data-testid="memory-no-session">Selecione uma sessão para buscar no histórico.</p>`
          : ""
      }
      ${state.error ? `<p class="session-error" data-testid="memory-error">${escapeHtml(state.error)}</p>` : ""}
      <div class="memory-search-row">
        <input type="search" data-testid="memory-search-input" placeholder="Buscar no transcript…"
          value="${escapeHtml(state.query)}" ${disabledAttr} />
        <select data-testid="memory-source-filter" ${disabledAttr}>
          <option value="" ${state.sourceTypeFilter === "" ? "selected" : ""}>todas as origens</option>
          <option value="system" ${state.sourceTypeFilter === "system" ? "selected" : ""}>system</option>
          <option value="microphone" ${state.sourceTypeFilter === "microphone" ? "selected" : ""}>microphone</option>
        </select>
        <button type="button" data-testid="memory-search-button" ${disabledAttr}>Buscar</button>
        <button type="button" data-testid="memory-refresh-items" ${disabledAttr}>Atualizar itens</button>
      </div>
      <div data-testid="memory-hits">
        <h3>Resultados (${state.hits.length})</h3>
        ${
          state.hits.length === 0
            ? `<p data-testid="memory-hits-empty">Nenhum hit.</p>`
            : `<ul class="memory-hit-list">${state.hits.map(renderHit).join("")}</ul>`
        }
      </div>
      <div data-testid="memory-items">
        <h3>Decisões / ações / compromissos (${state.items.length})</h3>
        ${
          state.items.length === 0
            ? `<p data-testid="memory-items-empty">Nenhum item extraído.</p>`
            : `<ul class="memory-item-list">${state.items.map(renderItem).join("")}</ul>`
        }
      </div>
    </section>
  `;

  const runSearch = () => {
    const q =
      container.querySelector<HTMLInputElement>('[data-testid="memory-search-input"]')?.value ?? "";
    const st = (container.querySelector<HTMLSelectElement>('[data-testid="memory-source-filter"]')
      ?.value ?? "") as "" | "system" | "microphone";
    callbacks.onSearch(q, st);
  };

  container
    .querySelector('[data-testid="memory-search-button"]')
    ?.addEventListener("click", runSearch);
  container
    .querySelector('[data-testid="memory-search-input"]')
    ?.addEventListener("keydown", (e) => {
      if ((e as KeyboardEvent).key === "Enter") {
        runSearch();
      }
    });
  container
    .querySelector('[data-testid="memory-refresh-items"]')
    ?.addEventListener("click", () => callbacks.onRefreshItems());
}

function renderHit(hit: MemorySearchHit): string {
  return `<li data-testid="memory-hit" data-event-id="${escapeHtml(hit.eventId)}">
    <span class="memory-meta">${escapeHtml(hit.sourceType ?? "?")} · ${escapeHtml(hit.occurredAt)}</span>
    <p>${escapeHtml(hit.text)}</p>
  </li>`;
}

function renderItem(item: MemoryItem): string {
  return `<li data-testid="memory-item" data-kind="${escapeHtml(item.kind)}">
    <strong>${escapeHtml(item.kind)}</strong>
    <p>${escapeHtml(item.text)}</p>
  </li>`;
}
