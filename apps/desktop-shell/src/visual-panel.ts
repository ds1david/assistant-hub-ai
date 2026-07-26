// Painel Visual Context R4 P0 (issue #68) — consentimento + frames OCR (stub).
import { escapeHtml } from "./dom-utils";

export interface VisualFrameView {
  eventId: string;
  occurredAt: string;
  ocrText: string;
  masked?: boolean;
  source?: string;
  frameId?: string;
}

export interface VisualPanelState {
  sessionId: string | null;
  consent: boolean;
  draftOcr: string;
  frames: VisualFrameView[];
  error: string | null;
  busy: boolean;
}

export interface VisualPanelCallbacks {
  onConsentChange: (consent: boolean) => void;
  onDraftChange: (text: string) => void;
  onCapture: () => void;
  onRefresh: () => void;
}

export function renderVisualPanel(
  container: HTMLElement,
  state: VisualPanelState,
  callbacks: VisualPanelCallbacks,
): void {
  const disabled = !state.sessionId || state.busy;
  const captureDisabled = disabled || !state.consent;

  container.innerHTML = `
    <section class="visual-panel" data-testid="visual-panel">
      <header>
        <h2>Visual Context (R4)</h2>
        <p class="visual-hint">Captura com consentimento + OCR/descrição (P0 stub; sem gravação silenciosa)</p>
      </header>
      ${
        !state.sessionId
          ? `<p data-testid="visual-no-session">Selecione uma sessão para registrar frames.</p>`
          : ""
      }
      ${state.error ? `<p class="session-error" data-testid="visual-error">${escapeHtml(state.error)}</p>` : ""}
      <label class="visual-consent">
        <input type="checkbox" data-testid="visual-consent"
          ${state.consent ? "checked" : ""} ${!state.sessionId || state.busy ? "disabled" : ""} />
        Consentimento explícito para captura/OCR nesta sessão
      </label>
      <div class="visual-form">
        <textarea data-testid="visual-ocr-draft" rows="3"
          placeholder="Texto OCR / descrição do frame (fixture ou stub)"
          ${disabled ? "disabled" : ""}>${escapeHtml(state.draftOcr)}</textarea>
        <button type="button" data-testid="visual-capture" ${captureDisabled ? "disabled" : ""}>
          Registrar frame
        </button>
        <button type="button" data-testid="visual-refresh" ${disabled ? "disabled" : ""}>
          Atualizar lista
        </button>
      </div>
      <div data-testid="visual-frames">
        <h3>Frames (${state.frames.length})</h3>
        ${
          state.frames.length === 0
            ? `<p data-testid="visual-frames-empty">Nenhum frame.</p>`
            : `<ul class="visual-frame-list">${state.frames.map(renderFrame).join("")}</ul>`
        }
      </div>
    </section>
  `;

  container
    .querySelector<HTMLInputElement>('[data-testid="visual-consent"]')
    ?.addEventListener("change", (e) => {
      callbacks.onConsentChange((e.target as HTMLInputElement).checked);
    });
  container
    .querySelector<HTMLTextAreaElement>('[data-testid="visual-ocr-draft"]')
    ?.addEventListener("input", (e) => {
      callbacks.onDraftChange((e.target as HTMLTextAreaElement).value);
    });
  container
    .querySelector('[data-testid="visual-capture"]')
    ?.addEventListener("click", () => callbacks.onCapture());
  container
    .querySelector('[data-testid="visual-refresh"]')
    ?.addEventListener("click", () => callbacks.onRefresh());
}

function renderFrame(frame: VisualFrameView): string {
  return `<li data-testid="visual-frame" data-event-id="${escapeHtml(frame.eventId)}">
    <span class="visual-meta">${escapeHtml(frame.occurredAt)}${frame.masked ? " · masked" : ""}</span>
    <p>${escapeHtml(frame.ocrText)}</p>
  </li>`;
}
