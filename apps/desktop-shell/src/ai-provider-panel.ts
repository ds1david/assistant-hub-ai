// Painel de configuração/teste de provedores de IA — US3 (FR-013/FR-014). Renderização pura +
// callbacks injetados, testável sem Tauri real (mesmo padrão de agent-panel.ts). Segredo nunca
// é lido/exibido além do valor mascarado devolvido por get_ai_provider_secret_preview (FR-014)
// — este arquivo nunca recebe nem manipula o valor resolvido de um secretRef.
import type {
  ConnectionTestResult,
  InvocationErrorType,
  Provider,
  SecretPreview,
} from "./api-client";
import { escapeHtml } from "./dom-utils";

export interface AiProviderPanelState {
  providers: Provider[];
  selectedProviderId: string | null; // null = formulário de novo provedor
  testResult: ConnectionTestResult | null;
  secretPreview: SecretPreview | null;
  error: string | null;
}

export interface AiProviderPanelCallbacks {
  onSelect: (providerId: string | null) => void;
  /** second arg: optional raw secret to store (os:); never kept in UI state after save */
  onSave: (provider: Provider, secretValue?: string | null) => void;
  onToggleEnabled: (providerId: string, enabled: boolean) => void;
  onTestConnection: (providerId: string) => void;
  onDelete: (providerId: string) => void;
}

const ERROR_TYPE_LABELS: Record<InvocationErrorType, string> = {
  AUTHENTICATION: "autenticação",
  MODEL_NOT_FOUND: "modelo inexistente",
  TIMEOUT: "timeout",
  RATE_LIMITED: "rate limit",
  GENERIC: "erro genérico",
  CAPABILITY_MISMATCH: "capacidade não suportada",
  CIRCUIT_OPEN: "circuit breaker aberto",
};

export function renderAiProviderPanel(
  container: HTMLElement,
  state: AiProviderPanelState,
  callbacks: AiProviderPanelCallbacks,
): void {
  const selected = state.providers.find((p) => p.id === state.selectedProviderId) ?? null;

  container.innerHTML = `
    <div class="ai-provider-list" data-testid="ai-provider-list">
      ${state.providers.map((provider) => renderListItem(provider)).join("")}
    </div>
    <button type="button" data-testid="ai-provider-new-button">Novo provedor</button>
    ${state.error ? `<p class="ai-provider-error" data-testid="ai-provider-error">${escapeHtml(state.error)}</p>` : ""}
    ${renderForm(selected)}
    ${state.secretPreview ? renderSecretPreview(state.secretPreview) : ""}
    ${state.testResult ? renderTestResult(state.testResult) : ""}
  `;

  container.querySelectorAll<HTMLElement>("[data-provider-id]").forEach((el) => {
    const providerId = el.dataset.providerId as string;
    el.querySelector('[data-action="select"]')?.addEventListener("click", () => callbacks.onSelect(providerId));
    el.querySelector('[data-action="delete"]')?.addEventListener("click", () => callbacks.onDelete(providerId));
    el.querySelector('[data-action="test"]')?.addEventListener("click", () => callbacks.onTestConnection(providerId));
    el.querySelector<HTMLInputElement>('[data-action="toggle-enabled"]')?.addEventListener("change", (event) => {
      callbacks.onToggleEnabled(providerId, (event.target as HTMLInputElement).checked);
    });
  });

  container.querySelector('[data-testid="ai-provider-new-button"]')?.addEventListener("click", () => {
    callbacks.onSelect(null);
  });

  container.querySelector("[data-testid=\"ai-provider-form\"]")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const { provider, secretValue } = readProviderFromForm(form, selected);
    callbacks.onSave(provider, secretValue);
  });
}

function renderListItem(provider: Provider): string {
  return `
    <div class="ai-provider-item" data-provider-id="${escapeHtml(provider.id)}" data-testid="ai-provider-item-${escapeHtml(provider.id)}">
      <span>${escapeHtml(provider.label)} (${escapeHtml(provider.type)})</span>
      <label>
        <input type="checkbox" data-action="toggle-enabled" ${provider.enabled ? "checked" : ""} />
        habilitado
      </label>
      <button type="button" data-action="select">Editar</button>
      <button type="button" data-action="test" data-testid="ai-provider-test-button-${escapeHtml(provider.id)}">Testar conexão</button>
      <button type="button" data-action="delete">Remover</button>
    </div>
  `;
}

function renderForm(selected: Provider | null): string {
  const idReadOnly = selected ? "readonly" : "";
  return `
    <form data-testid="ai-provider-form">
      <input name="id" placeholder="id" value="${escapeHtml(selected?.id ?? "")}" ${idReadOnly} required />
      <input name="label" placeholder="label" value="${escapeHtml(selected?.label ?? "")}" required />
      <select name="type">
        ${["openai-compatible", "anthropic", "gemini", "custom-http"]
          .map((type) => `<option value="${type}" ${selected?.type === type ? "selected" : ""}>${type}</option>`)
          .join("")}
      </select>
      <input name="baseUrl" placeholder="baseUrl" value="${escapeHtml(selected?.baseUrl ?? "")}" required />
      <input name="model" placeholder="model" value="${escapeHtml(selected?.defaults.model ?? "")}" required />
      <input name="timeoutMs" type="number" placeholder="timeoutMs" value="${selected?.defaults.timeoutMs ?? 30000}" required />
      <select name="authMode">
        ${["none", "bearer", "api-key"]
          .map(
            (mode) =>
              `<option value="${mode}" ${selected?.authentication.mode === mode ? "selected" : ""}>${mode}</option>`,
          )
          .join("")}
      </select>
      <input name="secretRef" data-testid="ai-provider-secret-ref"
        placeholder="secretRef (env:VAR ou os:…)" value="${escapeHtml(selected?.authentication.secretRef ?? "")}" />
      <input name="secretValue" type="password" data-testid="ai-provider-secret-value"
        placeholder="colar API key (salva no cofre OS; deixe vazio para manter)" autocomplete="off" value="" />
      <input name="capabilities" placeholder="capacidades (separadas por vírgula)" value="${escapeHtml((selected?.capabilities ?? []).join(","))}" />
      <button type="submit" data-testid="ai-provider-save-button">Salvar</button>
    </form>
  `;
}

export function readProviderFromForm(
  form: HTMLFormElement,
  selected: Provider | null,
): { provider: Provider; secretValue: string | null } {
  const data = new FormData(form);
  const authMode = String(data.get("authMode") ?? "none") as Provider["authentication"]["mode"];
  let secretRef = String(data.get("secretRef") ?? "").trim();
  const secretValue = String(data.get("secretValue") ?? "").trim();
  const providerId = String(data.get("id") ?? "").trim();
  // If user pasted a key, prefer os: ref (store fills on save); keep explicit env: if typed.
  if (secretValue.length > 0 && authMode !== "none") {
    if (!secretRef.startsWith("env:")) {
      secretRef = `os:assistant-hub/providers/${providerId}`;
    }
  }
  return {
    provider: {
      id: providerId,
      label: String(data.get("label") ?? "").trim(),
      type: String(data.get("type") ?? "openai-compatible") as Provider["type"],
      enabled: selected?.enabled ?? true,
      baseUrl: String(data.get("baseUrl") ?? "").trim(),
      authentication: {
        mode: authMode,
        secretRef: authMode === "none" || secretRef === "" ? null : secretRef,
        headerName: selected?.authentication.headerName ?? null,
      },
      defaults: {
        model: String(data.get("model") ?? "").trim(),
        temperature: selected?.defaults.temperature ?? null,
        topP: selected?.defaults.topP ?? null,
        maxTokens: selected?.defaults.maxTokens ?? null,
        timeoutMs: Number(data.get("timeoutMs") ?? 30000),
      },
      capabilities: String(data.get("capabilities") ?? "")
        .split(",")
        .map((c) => c.trim())
        .filter((c) => c.length > 0),
    },
    secretValue: secretValue.length > 0 ? secretValue : null,
  };
}

function renderSecretPreview(preview: SecretPreview): string {
  // Nunca o valor completo — só o que o servidor já mascarou (FR-014).
  const value = preview.maskedValue ? escapeHtml(preview.maskedValue) : "(sem segredo configurado)";
  return `<p class="ai-provider-secret-preview" data-testid="ai-provider-secret-preview">${value}</p>`;
}

function renderTestResult(result: ConnectionTestResult): string {
  if (result.success) {
    const detail = result.message ? ` (${escapeHtml(result.message)})` : "";
    return `<p class="ai-provider-test-result" data-testid="ai-provider-test-result" data-success="true">Conexão OK${detail}</p>`;
  }
  const label = result.errorType ? ERROR_TYPE_LABELS[result.errorType] : "erro desconhecido";
  const detail = result.message ? ` — ${escapeHtml(result.message)}` : "";
  return `
    <p class="ai-provider-test-result" data-testid="ai-provider-test-result" data-success="false" data-error-type="${result.errorType ?? ""}">
      Falha: ${escapeHtml(label)}${detail}
    </p>
  `;
}
