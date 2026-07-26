import { describe, expect, it } from "vitest";
import {
  resolveAlignment,
  resolveAssistantEmptyKind,
  buildGuidanceCommand,
} from "../src/session-alignment";

describe("resolveAlignment", () => {
  it("returns no_active_session when UI has no session", () => {
    expect(resolveAlignment(null, { running: true, agentSessionId: "a" })).toBe(
      "no_active_session",
    );
  });

  it("returns agent_stopped when agent not running", () => {
    expect(resolveAlignment("s1", { running: false, agentSessionId: "s1" })).toBe(
      "agent_stopped",
    );
  });

  it("returns agent_session_unknown when running without id", () => {
    expect(resolveAlignment("s1", { running: true, agentSessionId: null })).toBe(
      "agent_session_unknown",
    );
  });

  it("returns aligned when ids match", () => {
    expect(resolveAlignment("s1", { running: true, agentSessionId: "s1" })).toBe("aligned");
  });

  it("returns mismatched when ids differ", () => {
    expect(resolveAlignment("s1", { running: true, agentSessionId: "s2" })).toBe("mismatched");
  });

  it("mismatches UI UUID vs agent session-YYYYMMDD path id", () => {
    expect(
      resolveAlignment("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", {
        running: true,
        agentSessionId: "session-20260725-120000",
      }),
    ).toBe("mismatched");
  });
});

describe("buildGuidanceCommand (021 FR-012)", () => {
  it("includes --session with the active session id", () => {
    const id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
    expect(buildGuidanceCommand(id, "perfil.yaml")).toContain(`--session ${id}`);
  });
});

describe("resolveAssistantEmptyKind (FR-010)", () => {
  const base = {
    alignment: "aligned" as const,
    autoEnabled: true,
    enabledSourceTypes: ["system"] as const,
  };

  it("prioritizes session_mismatch over partials", () => {
    expect(
      resolveAssistantEmptyKind({
        ...base,
        alignment: "mismatched",
        feed: [{ kind: "Partial", text: "oi", sourceType: "system" }],
      }),
    ).toBe("session_mismatch");
  });

  it("returns prefs_auto_off when automatic is off", () => {
    expect(
      resolveAssistantEmptyKind({
        ...base,
        autoEnabled: false,
        feed: [{ kind: "Partial", text: "x", sourceType: "system" }],
      }),
    ).toBe("prefs_auto_off");
  });

  it("returns prefs_no_origin when no origins enabled", () => {
    expect(
      resolveAssistantEmptyKind({
        ...base,
        enabledSourceTypes: [],
        feed: [{ kind: "Partial", text: "x", sourceType: "system" }],
      }),
    ).toBe("prefs_no_origin");
  });

  it("returns awaiting_transcript for empty feed (not awaiting_final) — I4", () => {
    expect(resolveAssistantEmptyKind({ ...base, feed: [] })).toBe("awaiting_transcript");
  });

  it("returns awaiting_final when only partials", () => {
    expect(
      resolveAssistantEmptyKind({
        ...base,
        feed: [{ kind: "Partial", text: "como vai", sourceType: "system" }],
      }),
    ).toBe("awaiting_final");
  });

  it("returns no_eligible_question for finals that are not questions", () => {
    expect(
      resolveAssistantEmptyKind({
        ...base,
        feed: [{ kind: "Final", text: "ok", sourceType: "system" }],
      }),
    ).toBe("no_eligible_question");
  });

  it("buildGuidanceCommand includes session id", () => {
    expect(buildGuidanceCommand("uuid-1", "perfil.yaml")).toContain("--session uuid-1");
  });
});
