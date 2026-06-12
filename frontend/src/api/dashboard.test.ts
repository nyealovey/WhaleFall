import { describe, expect, it, vi } from "vitest";

import { fetchDashboardSnapshot } from "./dashboard";

describe("fetchDashboardSnapshot", () => {
  it("loads dashboard endpoints in one aggregate request", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ instances: { total: 3 }, accounts: { total: 8 }, databases: { total: 5 } })
        .mockResolvedValueOnce({ system: { cpu: 11 }, services: { database: "healthy", redis: "healthy" } })
        .mockResolvedValueOnce({ log_levels: [{ level: "ERROR", count: 2 }] })
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce({ top_risks: [{ instance_name: "db-critical" }] })
    };

    const snapshot = await fetchDashboardSnapshot(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/dashboard/overview");
    expect(client.get).toHaveBeenCalledWith("/api/v1/dashboard/status");
    expect(client.get).toHaveBeenCalledWith("/api/v1/dashboard/charts?type=all");
    expect(client.get).toHaveBeenCalledWith("/api/v1/dashboard/activities");
    expect(client.get).toHaveBeenCalledWith("/api/v1/risk-center/summary");
    expect(snapshot.overview.instances.total).toBe(3);
    expect(snapshot.charts.log_levels?.[0]?.level).toBe("ERROR");
    expect(snapshot.riskSummary?.top_risks?.[0]?.instance_name).toBe("db-critical");
  });
});
