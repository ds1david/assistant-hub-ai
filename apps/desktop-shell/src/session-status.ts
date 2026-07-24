// Painel de status de sessão/canais — US1 (FR-001/FR-002/FR-009). Função de renderização pura
// (sem chamar api-client diretamente) para ser testável isoladamente com fixtures.
import type { ChannelStatusView, SessionStatusResponse } from "./api-client";
import { escapeHtml } from "./dom-utils";

export function renderSessionStatus(container: HTMLElement, response: SessionStatusResponse): void {
  const { status, channels } = response;

  if (status.connectivity === "Disconnected") {
    container.innerHTML =
      '<p class="status status-disconnected" data-testid="status-disconnected">' +
      "Não foi possível conectar ao session-core.</p>";
    return;
  }

  if (typeof status.connectivity === "object" && "Error" in status.connectivity) {
    container.innerHTML =
      '<p class="status status-error" data-testid="status-error">' +
      `Erro ao consultar o session-core: ${escapeHtml(status.connectivity.Error)}</p>`;
    return;
  }

  if (!status.session) {
    container.innerHTML =
      '<p class="status status-empty" data-testid="status-empty">Sem sessão ativa.</p>';
    return;
  }

  const channelsHtml = channels.map(renderChannelItem).join("");
  container.innerHTML = `
    <p class="status status-active" data-testid="status-active">
      Sessão: ${escapeHtml(status.session.title)} (${escapeHtml(status.session.status)})
    </p>
    <ul class="channels" data-testid="channel-list">${channelsHtml}</ul>
  `;
}

function renderChannelItem(channel: ChannelStatusView): string {
  const label = channel.label ?? channel.channelId;
  return (
    `<li data-testid="channel-item" data-channel-id="${escapeHtml(channel.channelId)}">` +
    `<strong>${escapeHtml(label)}</strong> ` +
    `<span class="source-type">${escapeHtml(channel.sourceType ?? "")}</span>` +
    "</li>"
  );
}
