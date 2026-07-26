import { describe, expect, it } from "vitest";
import {
  buildDiagnosticSnapshot,
  formatDiagnosticReport,
  redactDetail,
  type ProbeInput,
} from "../src/diagnostics";

const base: ProbeInput = {
  sessionCoreBaseUrl: "http://localhost:8080",
  sttBaseUrl: "http://localhost:8001",
  activeSessionId: "sess-1",
  sessionCore: { ok: true, detail: "status=UP" },
  stt: { ok: true, detail: "model=small device=cuda" },
  agent: {
    running: true,
    healthy: true,
    binarySource: "sidecar",
    binaryPath: "C:\\app\\assistant-hub-audio.exe",
    agentVersion: "0.2.0",
    agentSessionId: "sess-1",
  },
  shellRunning: true,
};

describe("diagnostics", () => {
  it("builds all-up snapshot", () => {
    const snap = buildDiagnosticSnapshot(base);
    expect(snap.checks.every((c) => c.status === "up")).toBe(true);
    expect(snap.activeSessionId).toBe("sess-1");
  });

  it("marks core/stt down with next steps", () => {
    const snap = buildDiagnosticSnapshot({
      ...base,
      sessionCore: { ok: false, detail: "connection refused" },
      stt: { ok: false, detail: "timeout" },
      agent: { running: false, binarySource: "missing" },
      activeSessionId: null,
    });
    const core = snap.checks.find((c) => c.id === "session-core")!;
    const stt = snap.checks.find((c) => c.id === "stt")!;
    const agent = snap.checks.find((c) => c.id === "agent")!;
    expect(core.status).toBe("down");
    expect(core.nextStep).toMatch(/session-core/i);
    expect(stt.status).toBe("down");
    expect(agent.status).toBe("down");
    expect(agent.nextStep).toMatch(/assistant-hub-audio/i);
  });

  it("redacts secret-like fragments in details", () => {
    expect(redactDetail("token=sk-abc123456789")).toContain("[redacted]");
    const report = formatDiagnosticReport(
      buildDiagnosticSnapshot({
        ...base,
        sessionCore: { ok: true, detail: "ok password=supersecretvalue" },
      }),
    );
    expect(report).not.toContain("supersecretvalue");
    expect(report).toContain("sem secrets");
  });

  it("report never embeds raw transcript-like long blobs unchecked", () => {
    const long = "x".repeat(500);
    const report = formatDiagnosticReport(
      buildDiagnosticSnapshot({
        ...base,
        stt: { ok: true, detail: long },
      }),
    );
    expect(report.length).toBeLessThan(2000);
  });
});
