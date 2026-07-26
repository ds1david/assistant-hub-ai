import { describe, expect, it, vi } from "vitest";
import { renderDiagnosticsPanel } from "../src/diagnostics-panel";
import { buildDiagnosticSnapshot } from "../src/diagnostics";

describe("renderDiagnosticsPanel", () => {
  it("wires refresh and copy", () => {
    const container = document.createElement("div");
    const onRefresh = vi.fn();
    const onCopyReport = vi.fn();
    const snapshot = buildDiagnosticSnapshot({
      sessionCoreBaseUrl: "http://localhost:8080",
      sttBaseUrl: "http://localhost:8001",
      activeSessionId: null,
      sessionCore: { ok: true, detail: "UP" },
      stt: { ok: false, detail: "down" },
      agent: { running: false, binarySource: "path" },
      shellRunning: true,
    });
    renderDiagnosticsPanel(
      container,
      { snapshot, busy: false, error: null, copyFeedback: null },
      { onRefresh, onCopyReport },
    );
    expect(container.querySelector('[data-testid="diagnostics-panel"]')).toBeTruthy();
    expect(container.querySelectorAll('[data-testid="diag-check"]').length).toBeGreaterThan(2);
    container.querySelector<HTMLButtonElement>('[data-testid="diag-refresh"]')?.click();
    container.querySelector<HTMLButtonElement>('[data-testid="diag-copy"]')?.click();
    expect(onRefresh).toHaveBeenCalled();
    expect(onCopyReport).toHaveBeenCalled();
  });
});
