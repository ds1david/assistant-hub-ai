import { describe, expect, it, vi } from "vitest";
import { renderAiProviderPanel } from "../src/ai-provider-panel";
import type { ConnectionTestResult, InvocationErrorType, Provider, SecretPreview } from "../src/api-client";

function provider(overrides: Partial<Provider> = {}): Provider {
  return {
    id: "real-1",
    label: "Real",
    type: "openai-compatible",
    enabled: true,
    baseUrl: "http://fake.invalid",
    authentication: { mode: "bearer", secretRef: "env:FAKE_VAR", headerName: null },
    defaults: { model: "gpt-test", temperature: null, topP: null, maxTokens: null, timeoutMs: 3000 },
    capabilities: ["chat"],
    ...overrides,
  };
}

const noopCallbacks = {
  onSelect: vi.fn(),
  onSave: vi.fn(),
  onToggleEnabled: vi.fn(),
  onTestConnection: vi.fn(),
  onDelete: vi.fn(),
};

describe("renderAiProviderPanel", () => {
  it("never renders the full resolved secret value, only the masked preview (FR-014)", () => {
    const container = document.createElement("div");
    const secretPreview: SecretPreview = { providerId: "real-1", maskedValue: "sk-...aB3f" };

    renderAiProviderPanel(
      container,
      { providers: [provider()], selectedProviderId: "real-1", testResult: null, secretPreview, error: null },
      noopCallbacks,
    );

    const html = container.innerHTML;
    expect(html).toContain("sk-...aB3f");
    expect(html.toLowerCase()).not.toContain("super-secret");
  });

  it("shows a placeholder when no secret is configured, never an empty/undefined leak", () => {
    const container = document.createElement("div");
    const secretPreview: SecretPreview = { providerId: "real-1", maskedValue: null };

    renderAiProviderPanel(
      container,
      { providers: [provider()], selectedProviderId: "real-1", testResult: null, secretPreview, error: null },
      noopCallbacks,
    );

    expect(container.querySelector('[data-testid="ai-provider-secret-preview"]')?.textContent).toBe(
      "(sem segredo configurado)",
    );
  });

  it.each<[InvocationErrorType, string]>([
    ["AUTHENTICATION", "autenticação"],
    ["MODEL_NOT_FOUND", "modelo inexistente"],
    ["TIMEOUT", "timeout"],
    ["RATE_LIMITED", "rate limit"],
    ["GENERIC", "erro genérico"],
    ["CAPABILITY_MISMATCH", "capacidade não suportada"],
  ])("renders a distinct message for %s, never a generic-only message", (errorType, expectedLabel) => {
    const container = document.createElement("div");
    const testResult: ConnectionTestResult = { providerId: "real-1", success: false, errorType, message: null };

    renderAiProviderPanel(
      container,
      { providers: [provider()], selectedProviderId: "real-1", testResult, secretPreview: null, error: null },
      noopCallbacks,
    );

    const resultEl = container.querySelector('[data-testid="ai-provider-test-result"]');
    expect(resultEl?.getAttribute("data-error-type")).toBe(errorType);
    expect(resultEl?.textContent).toContain(expectedLabel);
  });

  it("calls onSave with the form values when the form is submitted", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const onSave = vi.fn();

    renderAiProviderPanel(
      container,
      { providers: [], selectedProviderId: null, testResult: null, secretPreview: null, error: null },
      { ...noopCallbacks, onSave },
    );

    const form = container.querySelector<HTMLFormElement>('[data-testid="ai-provider-form"]')!;
    (form.elements.namedItem("id") as HTMLInputElement).value = "novo-1";
    (form.elements.namedItem("label") as HTMLInputElement).value = "Novo";
    (form.elements.namedItem("baseUrl") as HTMLInputElement).value = "http://novo.invalid";
    (form.elements.namedItem("model") as HTMLInputElement).value = "modelo-x";
    form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));

    expect(onSave).toHaveBeenCalledOnce();
    const saved = onSave.mock.calls[0][0] as Provider;
    expect(saved.id).toBe("novo-1");
    expect(saved.label).toBe("Novo");
    expect(saved.baseUrl).toBe("http://novo.invalid");
    document.body.removeChild(container);
  });

  it("toggling the enabled checkbox calls onToggleEnabled with the provider id", () => {
    const container = document.createElement("div");
    const onToggleEnabled = vi.fn();

    renderAiProviderPanel(
      container,
      { providers: [provider({ enabled: true })], selectedProviderId: null, testResult: null, secretPreview: null, error: null },
      { ...noopCallbacks, onToggleEnabled },
    );

    const checkbox = container.querySelector<HTMLInputElement>('[data-action="toggle-enabled"]')!;
    checkbox.checked = false;
    checkbox.dispatchEvent(new Event("change", { bubbles: true }));

    expect(onToggleEnabled).toHaveBeenCalledWith("real-1", false);
  });
});
