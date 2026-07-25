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
  });

  it("save then load restores same session", async () => {
    const store = createMemoryPrefsStore();
    await store.save("S", {
      autoEnabled: true,
      enabledSourceTypes: ["system", "microphone"],
      inputMode: "question-only",
    });
    const loaded = await store.load("S");
    expect(loaded.autoEnabled).toBe(true);
    expect(loaded.inputMode).toBe("question-only");
    expect(loaded.enabledSourceTypes).toContain("microphone");
  });

  it("isolates S vs T (SC-010)", async () => {
    const store = createMemoryPrefsStore();
    await store.save("S", {
      autoEnabled: true,
      enabledSourceTypes: ["system"],
      inputMode: "question-only",
    });
    await store.save("T", {
      autoEnabled: false,
      enabledSourceTypes: ["microphone"],
      inputMode: "question-plus-recent-context",
    });
    const s = await store.load("S");
    const t = await store.load("T");
    expect(s.autoEnabled).toBe(true);
    expect(s.inputMode).toBe("question-only");
    expect(t.autoEnabled).toBe(false);
    expect(t.enabledSourceTypes).toEqual(["microphone"]);
    // voltar a S não vaza T
    const s2 = await store.load("S");
    expect(s2).toEqual(s);
  });

  it("normalizePrefs fills defaults", () => {
    expect(normalizePrefs(null).autoEnabled).toBe(false);
    expect(normalizePrefs({ autoEnabled: true }).enabledSourceTypes).toEqual(["system"]);
  });
});
