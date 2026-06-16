import { describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { runAction } from "./action-feedback";

vi.mock("sonner", () => ({
  toast: {
    promise: vi.fn()
  }
}));

describe("runAction", () => {
  it("wraps action promises with shared Sonner messages", async () => {
    const promise = Promise.resolve({ ok: true });

    const result = runAction(promise, { loading: "保存中", success: "保存成功" });

    expect(result).toBe(promise);
    expect(toast.promise).toHaveBeenCalledWith(
      promise,
      expect.objectContaining({
        loading: "保存中",
        success: "保存成功"
      })
    );
    await expect(result).resolves.toEqual({ ok: true });
  });
});
