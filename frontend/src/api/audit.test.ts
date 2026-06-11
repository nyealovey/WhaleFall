import { describe, expect, it, vi } from "vitest";

import { fetchAccountChangeLogsSnapshot, fetchHistoryLogsSnapshot } from "./audit";

describe("audit api", () => {
  it("loads history logs and statistics", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ items: [{ id: 1, message: "hello" }], total: 1, page: 1, pages: 1, limit: 20 })
        .mockResolvedValueOnce({ total_logs: 1, error_count: 0, warning_count: 0 })
    };

    const snapshot = await fetchHistoryLogsSnapshot(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/logs?page=1&limit=20");
    expect(client.get).toHaveBeenCalledWith("/api/v1/logs/statistics?hours=24");
    expect(snapshot.list.items[0]?.message).toBe("hello");
    expect(snapshot.statistics.total_logs).toBe(1);
  });

  it("loads account change logs and statistics", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ items: [{ id: 1, username: "readonly" }], total: 1, page: 1, pages: 1, limit: 20 })
        .mockResolvedValueOnce({ total_changes: 1, success_count: 1, failed_count: 0, affected_accounts: 1 })
    };

    const snapshot = await fetchAccountChangeLogsSnapshot(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/account-change-logs?page=1&limit=20");
    expect(client.get).toHaveBeenCalledWith("/api/v1/account-change-logs/statistics?hours=24");
    expect(snapshot.list.items[0]?.username).toBe("readonly");
    expect(snapshot.statistics.total_changes).toBe(1);
  });
});
