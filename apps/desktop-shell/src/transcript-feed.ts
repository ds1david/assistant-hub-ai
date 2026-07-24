// Painel de feed de transcript — US2 (FR-003/FR-004/FR-005). Renderização pura, ordenada
// cronologicamente, cada entrada marcada com o canal de origem — nunca combina texto de canais
// diferentes em uma mesma entrada (SC-002).
import type { TranscriptFeedEntry } from "./api-client";
import { escapeHtml } from "./dom-utils";

export function renderTranscriptFeed(container: HTMLElement, entries: TranscriptFeedEntry[]): void {
  if (entries.length === 0) {
    container.innerHTML =
      '<p class="feed-empty" data-testid="feed-empty">Nenhum trecho de transcript ainda.</p>';
    return;
  }

  const sorted = [...entries].sort((a, b) => a.occurredAt.localeCompare(b.occurredAt));
  container.innerHTML =
    '<ol class="feed" data-testid="feed-list">' + sorted.map(renderFeedEntry).join("") + "</ol>";
}

function renderFeedEntry(entry: TranscriptFeedEntry): string {
  const channelLabel = entry.label ?? entry.channelId ?? "canal desconhecido";
  return (
    '<li data-testid="feed-entry" ' +
    `data-channel-id="${escapeHtml(entry.channelId ?? "")}" ` +
    `data-kind="${entry.kind}">` +
    `<span class="feed-channel">${escapeHtml(channelLabel)}</span>` +
    `<span class="feed-text">${escapeHtml(entry.text)}</span>` +
    "</li>"
  );
}
