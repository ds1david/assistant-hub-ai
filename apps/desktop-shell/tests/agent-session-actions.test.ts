import { describe, expect, it, vi } from "vitest";
import {
  onSessionSelected,
  restartAgentWithActiveSession,
} from "../src/agent-session-actions";

describe("restartAgentWithActiveSession (I2 / FR-011g)", () => {
  it("stops then starts with the active session id", async () => {
    const start = vi.fn().mockResolvedValue(undefined);
    const stop = vi.fn().mockResolvedValue(undefined);
    await restartAgentWithActiveSession("sess-active", "Direct", true, "perfil.yaml", {
      start,
      stop,
    });
    expect(stop).toHaveBeenCalledOnce();
    expect(start).toHaveBeenCalledWith("sess-active", "perfil.yaml");
  });

  it("starts without stop when not running", async () => {
    const start = vi.fn().mockResolvedValue(undefined);
    const stop = vi.fn();
    await restartAgentWithActiveSession("sess-active", "Direct", false, "perfil.yaml", {
      start,
      stop,
    });
    expect(stop).not.toHaveBeenCalled();
    expect(start).toHaveBeenCalledWith("sess-active", "perfil.yaml");
  });

  it("refuses Guided (no force-kill)", async () => {
    await expect(
      restartAgentWithActiveSession("s", "Guided", true, "p.yaml", {
        start: vi.fn(),
        stop: vi.fn(),
      }),
    ).rejects.toThrow(/guiado/i);
  });
});

describe("onSessionSelected (I3 / FR-009)", () => {
  it("does not call stop or start when selecting another session", () => {
    const start = vi.fn();
    const stop = vi.fn();
    const setActive = vi.fn();
    onSessionSelected("new-sess", setActive, { start, stop });
    expect(setActive).toHaveBeenCalledWith("new-sess");
    expect(start).not.toHaveBeenCalled();
    expect(stop).not.toHaveBeenCalled();
  });
});
