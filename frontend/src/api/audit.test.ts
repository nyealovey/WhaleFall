import { describe, expect, it, vi } from "vitest";

import {
  fetchAccountChangeLogDetail,
  fetchAccountChangeLogsSnapshot,
  fetchAccountChangeLogOptions,
  fetchHistoryLogDetail,
  fetchHistoryLogModules,
  fetchHistoryLogsSnapshot
} from "./audit";

describe("audit api", () => {
  it("loads history logs and statistics", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ items: [{ id: 1, message: "hello" }], total: 1, page: 1, pages: 1, limit: 20 })
        .mockResolvedValueOnce({ total_logs: 1, error_count: 0, warning_count: 0 })
    };

    const snapshot = await fetchHistoryLogsSnapshot({ page: 2, limit: 20, search: "timeout", level: "ERROR", module: "scheduler", hours: 168 }, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/logs?page=2&limit=20&search=timeout&level=ERROR&module=scheduler&hours=168");
    expect(client.get).toHaveBeenCalledWith("/api/v1/logs/statistics?hours=168");
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

    const snapshot = await fetchAccountChangeLogsSnapshot({ page: 3, limit: 50, search: "root", instanceId: 7, dbType: "mysql", changeType: "add" }, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/account-change-logs?page=3&limit=50&search=root&instance_id=7&db_type=mysql&change_type=add");
    expect(client.get).toHaveBeenCalledWith("/api/v1/account-change-logs/statistics");
    expect(snapshot.list.items[0]?.username).toBe("readonly");
    expect(snapshot.statistics.total_changes).toBe(1);
  });

  it("loads full filter options", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({
          modules: ["scheduler", "accounts"],
          module_options: [
            { value: "scheduler", label: "调度任务" },
            { value: "accounts", label: "账户" }
          ]
        })
        .mockResolvedValueOnce({ instances: [{ value: "7", label: "mysql-1" }] })
    };

    const modules = await fetchHistoryLogModules(client);
    const options = await fetchAccountChangeLogOptions(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/logs/modules");
    expect(client.get).toHaveBeenCalledWith("/api/v1/instances/options");
    expect(modules).toEqual([
      { value: "scheduler", label: "调度任务" },
      { value: "accounts", label: "账户" }
    ]);
    expect(options[0]?.label).toBe("mysql-1");
  });

  it("loads history log detail", async () => {
    const client = {
      get: vi.fn().mockResolvedValue({ log: { id: 7, message: "detail message", context: { run_id: "run-7" } } })
    };

    const detail = await fetchHistoryLogDetail(7, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/logs/7");
    expect(detail.log.message).toBe("detail message");
  });

  it("loads account change log detail", async () => {
    const client = {
      get: vi.fn().mockResolvedValue({ log: { id: 8, username: "app", privilege_diff: [{ name: "SELECT" }] } })
    };

    const detail = await fetchAccountChangeLogDetail(8, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/account-change-logs/8");
    expect(detail.log.username).toBe("app");
    expect(detail.log.privilege_diff).toEqual([{ name: "SELECT" }]);
  });
});
