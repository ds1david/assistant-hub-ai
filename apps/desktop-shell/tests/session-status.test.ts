import { describe, expect, it } from "vitest";
import { renderSessionStatus } from "../src/session-status";
import type { SessionStatusResponse } from "../src/api-client";

describe("renderSessionStatus", () => {
  it("shows the disconnected state without rendering stale session data (FR-009)", () => {
    const container = document.createElement("div");
    const response: SessionStatusResponse = {
      status: { connectivity: "Disconnected", session: null },
      channels: [],
    };

    renderSessionStatus(container, response);

    expect(container.querySelector('[data-testid="status-disconnected"]')).not.toBeNull();
  });

  it("shows the empty state when connected but no active session exists", () => {
    const container = document.createElement("div");
    const response: SessionStatusResponse = {
      status: { connectivity: "Connected", session: null },
      channels: [],
    };

    renderSessionStatus(container, response);

    expect(container.querySelector('[data-testid="status-empty"]')).not.toBeNull();
  });

  it("renders session status and distinct channels grouped by channelId, not label (FR-002)", () => {
    const container = document.createElement("div");
    const response: SessionStatusResponse = {
      status: {
        connectivity: "Connected",
        session: {
          id: "s1",
          title: "quickstart",
          profileId: "demo",
          status: "ACTIVE",
          createdAt: null,
          startedAt: null,
          endedAt: null,
        },
      },
      channels: [
        {
          channelId: "mic-1",
          sourceType: "microphone",
          label: "Canal",
          deviceIndex: null,
          deviceName: null,
          deviceEndpointId: null,
          lastEventAt: null,
          eventCount: 1,
        },
        {
          channelId: "sys-1",
          sourceType: "system_audio",
          label: "Canal",
          deviceIndex: null,
          deviceName: null,
          deviceEndpointId: null,
          lastEventAt: null,
          eventCount: 1,
        },
      ],
    };

    renderSessionStatus(container, response);

    const items = container.querySelectorAll('[data-testid="channel-item"]');
    expect(items).toHaveLength(2);
    expect(items[0].getAttribute("data-channel-id")).toBe("mic-1");
    expect(items[1].getAttribute("data-channel-id")).toBe("sys-1");
  });
});
