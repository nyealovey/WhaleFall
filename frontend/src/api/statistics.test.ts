import { describe, expect, it, vi } from "vitest";

import {
  fetchAccountStatisticsSnapshot,
  fetchDatabaseStatistics,
  fetchInstanceStatistics
} from "./statistics";

describe("statistics api", () => {
  it("loads instance statistics", async () => {
    const client = {
      get: vi.fn().mockResolvedValueOnce({ total_instances: 3 })
    };

    await expect(fetchInstanceStatistics(client)).resolves.toEqual({ total_instances: 3 });

    expect(client.get).toHaveBeenCalledWith("/api/v1/instances/statistics");
  });

  it("loads account statistics snapshot", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ total_accounts: 8 })
        .mockResolvedValueOnce({ mysql: { total_accounts: 5 } })
        .mockResolvedValueOnce({ DBA: { total_accounts: 2 } })
        .mockResolvedValueOnce({ rule_stats: [{ rule_id: 7, matched_accounts_count: 3 }] })
    };

    const snapshot = await fetchAccountStatisticsSnapshot(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/statistics/summary");
    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/statistics/db-types");
    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/statistics/classifications");
    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/statistics/rules");
    expect(snapshot.summary.total_accounts).toBe(8);
    expect(snapshot.dbTypes).toEqual({ mysql: { total_accounts: 5 } });
    expect(snapshot.classifications).toEqual({ DBA: { total_accounts: 2 } });
    expect(snapshot.rules.rule_stats[0]?.rule_id).toBe(7);
  });

  it("loads database statistics", async () => {
    const client = {
      get: vi.fn().mockResolvedValueOnce({
        stats: {
          total_databases: 9
        }
      })
    };

    await expect(fetchDatabaseStatistics(client)).resolves.toEqual({
      stats: {
        total_databases: 9
      }
    });

    expect(client.get).toHaveBeenCalledWith("/api/v1/databases/statistics");
  });
});
