// Painel do assistente automático — Q&A, origens, modo de entrada, conflito cancelar/aguardar.
import type { AssistantAutoView, AssistantTurn, ConflictChoice } from "./assistant-auto";
import type { CanonicalSourceType, InputMode } from "./assistant-prefs";
import { escapeHtml } from "./dom-utils";

export interface AssistantPanelCallbacks {
  onToggleEnabled: (enabled: boolean) => void;
  onToggleOrigin: (origin: CanonicalSourceType, enabled: boolean) => void;
  onInputModeChange: (mode: InputMode) => void;
  onResolveConflict: (choice: ConflictChoice) => void;
}

export function renderAssistantPanel(
  container: HTMLElement,
  view: AssistantAutoView,
  callbacks: AssistantPanelCallbacks,
): void {
  const disabled = Boolean(view.controlsDisabled);
  const disabledAttr = disabled ? "disabled" : "";
  const prefs = view.prefs ?? {
    autoEnabled: view.enabled,
    enabledSourceTypes: ["system"] as CanonicalSourceType[],
    inputMode: "question-plus-recent-context" as InputMode,
  };
  const systemOn = prefs.enabledSourceTypes.includes("system");
  const micOn = prefs.enabledSourceTypes.includes("microphone");

  container.innerHTML = `
    <section class="assistant-panel" data-testid="assistant-panel">
      <header class="assistant-header">
        <h2>Assistente (respostas automáticas)</h2>
        <label class="assistant-toggle">
          <input type="checkbox" data-testid="assistant-enabled" data-action="toggle-enabled"
            ${prefs.autoEnabled ? "checked" : ""} ${disabledAttr} />
          automático
        </label>
        ${view.busy ? `<span class="assistant-busy" data-testid="assistant-busy">respondendo…</span>` : ""}
      </header>
      ${
        view.sessionHint
          ? `<p class="assistant-hint" data-testid="assistant-session-hint">${escapeHtml(view.sessionHint)}</p>`
          : ""
      }
      <div class="assistant-prefs" data-testid="assistant-prefs">
        <fieldset class="assistant-origins" ${disabledAttr ? "disabled" : ""}>
          <legend>Origens que disparam</legend>
          <label>
            <input type="checkbox" data-testid="assistant-origin-system" data-action="origin-system"
              ${systemOn ? "checked" : ""} ${disabledAttr} />
            sistema
          </label>
          <label>
            <input type="checkbox" data-testid="assistant-origin-microphone" data-action="origin-microphone"
              ${micOn ? "checked" : ""} ${disabledAttr} />
            microfone
          </label>
        </fieldset>
        <label class="assistant-input-mode-label">
          Modo de entrada
          <select data-testid="assistant-input-mode" data-action="input-mode" ${disabledAttr}>
            <option value="question-plus-recent-context"
              ${prefs.inputMode === "question-plus-recent-context" ? "selected" : ""}>
              pergunta + contexto recente
            </option>
            <option value="question-only"
              ${prefs.inputMode === "question-only" ? "selected" : ""}>
              só pergunta
            </option>
          </select>
        </label>
      </div>
      ${view.conflict ? renderConflict(view) : ""}
      ${renderTurns(view.turns)}
    </section>
  `;

  container.querySelector<HTMLInputElement>('[data-action="toggle-enabled"]')?.addEventListener(
    "change",
    (event) => {
      callbacks.onToggleEnabled((event.target as HTMLInputElement).checked);
    },
  );

  container.querySelector<HTMLInputElement>('[data-action="origin-system"]')?.addEventListener(
    "change",
    (event) => {
      callbacks.onToggleOrigin("system", (event.target as HTMLInputElement).checked);
    },
  );

  container
    .querySelector<HTMLInputElement>('[data-action="origin-microphone"]')
    ?.addEventListener("change", (event) => {
      callbacks.onToggleOrigin("microphone", (event.target as HTMLInputElement).checked);
    });

  container.querySelector<HTMLSelectElement>('[data-action="input-mode"]')?.addEventListener(
    "change",
    (event) => {
      const value = (event.target as HTMLSelectElement).value as InputMode;
      callbacks.onInputModeChange(value);
    },
  );

  container.querySelector('[data-action="conflict-cancel"]')?.addEventListener("click", () => {
    callbacks.onResolveConflict("cancel");
  });
  container.querySelector('[data-action="conflict-wait"]')?.addEventListener("click", () => {
    callbacks.onResolveConflict("wait");
  });
}

function renderConflict(view: AssistantAutoView): string {
  const conflict = view.conflict;
  if (!conflict) {
    return "";
  }
  // T042 / FR-007: se o turn “em execução” já terminou, não rotular como gerando.
  const priorTurn = view.turns.find((t) => t.id === conflict.runningTurnId);
  const priorStatus = priorTurn?.status;
  const priorStillRunning = priorStatus === "running" || (priorStatus == null && view.busy);
  const priorLabel = priorStillRunning
    ? "Em execução"
    : priorStatus === "done"
      ? "Anterior concluída"
      : priorStatus === "error"
        ? "Anterior com erro"
        : priorStatus === "cancelled"
          ? "Anterior cancelada"
          : "Anterior";
  const intro = priorStillRunning
    ? "Nova pergunta enquanto outra resposta ainda está em andamento."
    : "Nova pergunta chegou; a resposta anterior já terminou — escolha o que fazer com a nova.";
  const waitLabel = priorStillRunning
    ? "Aguardar a resposta atual terminar"
    : "Responder a nova agora (anterior já terminou)";

  return `
    <div class="assistant-conflict" data-testid="assistant-conflict" role="alertdialog"
      aria-label="Conflito de perguntas" data-prior-status="${escapeHtml(priorStatus ?? "unknown")}">
      <p><strong>Nova pergunta</strong> — ${escapeHtml(intro)}</p>
      <p data-testid="assistant-conflict-running">
        ${escapeHtml(priorLabel)}: <em>${escapeHtml(conflict.runningQuestion)}</em>
      </p>
      <p data-testid="assistant-conflict-incoming">
        Nova: <em>${escapeHtml(conflict.incoming.text)}</em>
      </p>
      <div class="assistant-conflict-actions">
        <button type="button" data-action="conflict-cancel" data-testid="assistant-conflict-cancel">
          Cancelar a anterior e responder a nova
        </button>
        <button type="button" data-action="conflict-wait" data-testid="assistant-conflict-wait">
          ${escapeHtml(waitLabel)}
        </button>
      </div>
    </div>
  `;
}

function renderTurns(turns: AssistantTurn[]): string {
  if (turns.length === 0) {
    return `<p class="assistant-empty" data-testid="assistant-empty">
      Nenhuma interação ainda. Com o automático ligado e uma sessão ativa, perguntas finais
      no transcript (origem habilitada) disparam a rota <code>live-answer</code>.
    </p>`;
  }
  // Mais recente primeiro (FR-029)
  const items = [...turns]
    .reverse()
    .map((turn) => renderTurn(turn))
    .join("");
  return `<ol class="assistant-turns" data-testid="assistant-turns">${items}</ol>`;
}

function renderTurn(turn: AssistantTurn): string {
  const statusLabel = statusText(turn);
  const answerBlock =
    turn.status === "done"
      ? `<p class="assistant-answer" data-testid="assistant-answer">${escapeHtml(turn.answer ?? "")}</p>`
      : turn.status === "error" || turn.status === "cancelled"
        ? `<p class="assistant-error" data-testid="assistant-error">${escapeHtml(turn.error ?? statusLabel)}</p>`
        : `<p class="assistant-pending" data-testid="assistant-pending">${escapeHtml(statusLabel)}</p>`;
  const meta =
    turn.providerId || turn.latencyMs != null
      ? `<p class="assistant-meta">${escapeHtml(
          [turn.providerId, turn.latencyMs != null ? `${turn.latencyMs} ms` : null]
            .filter(Boolean)
            .join(" · "),
        )}</p>`
      : "";
  return `
    <li class="assistant-turn" data-testid="assistant-turn" data-status="${turn.status}" data-turn-id="${escapeHtml(turn.id)}">
      <p class="assistant-question" data-testid="assistant-question"><strong>P:</strong> ${escapeHtml(turn.question)}</p>
      ${answerBlock}
      ${meta}
    </li>
  `;
}

function statusText(turn: AssistantTurn): string {
  switch (turn.status) {
    case "running":
      return "Gerando resposta…";
    case "queued":
      return "Na fila — aguardando a resposta anterior.";
    case "cancelled":
      return turn.error ?? "Cancelada";
    case "error":
      return turn.error ?? "Erro";
    case "done":
      return "OK";
    default:
      return turn.status;
  }
}
