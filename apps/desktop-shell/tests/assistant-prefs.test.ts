import { describe, expect, it } from "vitest";
import {
  createMemoryPrefsStore,
  DEFAULT_ASSISTANT_PREFS,
  normalizePrefs,
} from "../src/assistant-prefs";

describe("assistant prefs store", () => {
  it("returns defaults for unknown session", async () => {
    const store = createMemoryPrefsStore();
    const prefs = await store.load("new-session");
    expect(prefs).toEqual(DEFAULT_ASSISTANT_PREFS);
    expect(prefs.autoEnabled).toBe(false);
    expect(prefs.enabledSourceTypes).toEqual(["system"]);
    expect(prefs.inputMode).toBe("question-plus-recent-context");
    expect(prefs.interviewMode).toBe(false);
    expect(prefs.useProsody).toBe(false);
    expect(prefs.prosodyThreshold).toBe(0.65);
    expect(prefs.includeMicrophoneInContext).toBe(true);
  });

  it("save then load restores same session", async () => {
    const store = createMemoryPrefsStore();
    await store.save("S", {
      autoEnabled: true,
      enabledSourceTypes: ["system", "microphone"],
      inputMode: "question-only",
      interviewMode: true,
      useProsody: true,
      prosodyThreshold: 0.7,
      includeMicrophoneInContext: false,
    });
    const loaded = await store.load("S");
    expect(loaded.autoEnabled).toBe(true);
    expect(loaded.inputMode).toBe("question-only");
    expect(loaded.enabledSourceTypes).toContain("microphone");
    expect(loaded.interviewMode).toBe(true);
    expect(loaded.useProsody).toBe(true);
    expect(loaded.prosodyThreshold).toBe(0.7);
    expect(loaded.includeMicrophoneInContext).toBe(false);
  });

  it("isolates S vs T (SC-010 / SC-008 include-mic)", async () => {
    const store = createMemoryPrefsStore();
    await store.save("S", {
      autoEnabled: true,
      enabledSourceTypes: ["system"],
      inputMode: "question-only",
      interviewMode: true,
      useProsody: false,
      prosodyThreshold: 0.65,
      includeMicrophoneInContext: false,
    });
    await store.save("T", {
      autoEnabled: false,
      enabledSourceTypes: ["microphone"],
      inputMode: "question-plus-recent-context",
      interviewMode: false,
      useProsody: true,
      prosodyThreshold: 0.5,
      includeMicrophoneInContext: true,
    });
    const s = await store.load("S");
    const t = await store.load("T");
    expect(s.autoEnabled).toBe(true);
    expect(s.inputMode).toBe("question-only");
    expect(s.interviewMode).toBe(true);
    expect(s.includeMicrophoneInContext).toBe(false);
    expect(t.autoEnabled).toBe(false);
    expect(t.enabledSourceTypes).toEqual(["microphone"]);
    expect(t.useProsody).toBe(true);
    expect(t.includeMicrophoneInContext).toBe(true);
    // voltar a S não vaza T
    const s2 = await store.load("S");
    expect(s2).toEqual(s);
    expect(s2.includeMicrophoneInContext).toBe(false);
  });

  it("normalizePrefs fills defaults for new fields", () => {
    expect(normalizePrefs(null).autoEnabled).toBe(false);
    expect(normalizePrefs({ autoEnabled: true }).enabledSourceTypes).toEqual(["system"]);
    expect(normalizePrefs({ autoEnabled: true }).interviewMode).toBe(false);
    expect(normalizePrefs({ autoEnabled: true }).useProsody).toBe(false);
    expect(normalizePrefs({ autoEnabled: true }).prosodyThreshold).toBe(0.65);
    expect(normalizePrefs({ prosodyThreshold: 1.5 }).prosodyThreshold).toBe(1);
    expect(normalizePrefs({ prosodyThreshold: -0.2 }).prosodyThreshold).toBe(0);
    // 028: missing includeMicrophoneInContext → true
    expect(normalizePrefs({ autoEnabled: true }).includeMicrophoneInContext).toBe(true);
    expect(normalizePrefs({ includeMicrophoneInContext: false }).includeMicrophoneInContext).toBe(
      false,
    );
    expect(normalizePrefs({ includeMicrophoneInContext: true }).includeMicrophoneInContext).toBe(
      true,
    );
  });
});
