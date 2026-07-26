import { describe, expect, it, vi } from "vitest";
import {
  afterCreateSuccess,
  isSelectableSessionId,
  reconcileActiveSessionAfterList,
} from "../src/session-selection";

describe("isSelectableSessionId", () => {
  it("accepts non-blank ids", () => {
    expect(isSelectableSessionId("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")).toBe(true);
  });

  it("rejects blank and whitespace", () => {
    expect(isSelectableSessionId("")).toBe(false);
    expect(isSelectableSessionId("   ")).toBe(false);
  });
});

describe("reconcileActiveSessionAfterList (FR-006 / no auto-select)", () => {
  const list = [{ id: "s1" }, { id: "s2" }];

  it("preserves active when still listed", () => {
    expect(reconcileActiveSessionAfterList("s1", list)).toBe("s1");
  });

  it("orphans to null when id missing", () => {
    expect(reconcileActiveSessionAfterList("gone", list)).toBeNull();
  });

  it("keeps null when active is null even if list is non-empty (no auto-select)", () => {
    expect(reconcileActiveSessionAfterList(null, list)).toBeNull();
  });

  it("treats blank active as null", () => {
    expect(reconcileActiveSessionAfterList("  ", list)).toBeNull();
  });
});

describe("afterCreateSuccess (FR-005)", () => {
  it("calls select with created id", async () => {
    const select = vi.fn().mockResolvedValue(undefined);
    await afterCreateSuccess("new-uuid", select);
    expect(select).toHaveBeenCalledWith("new-uuid");
  });

  it("does not invent active for blank id", async () => {
    const select = vi.fn();
    await afterCreateSuccess("  ", select);
    expect(select).not.toHaveBeenCalled();
  });
});
