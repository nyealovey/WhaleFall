import { describe, expect, it, vi } from "vitest";

import { fetchRiskCenterSnapshot } from "./riskCenter";

describe("fetchRiskCenterSnapshot", () => {
  it("loads summary and a bounded first page of risk cards", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ total_instances: 2, severity_counts: { high: 1 }, top_risks: [] })
        .mockResolvedValueOnce({ items: [{ instance_id: 1, name: "db01" }], total: 1, page: 1, pages: 1, limit: 20 })
    };

    const snapshot = await fetchRiskCenterSnapshot({}, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/risk-center/summary");
    expect(client.get).toHaveBeenCalledWith("/api/v1/risk-center/cards?limit=20&page=1");
    expect(snapshot.summary.total_instances).toBe(2);
    expect(snapshot.cards.items[0]?.name).toBe("db01");
  });

  it("passes risk card filters through the v1 cards endpoint", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ total_instances: 2, severity_counts: {}, top_risks: [] })
        .mockResolvedValueOnce({ items: [], total: 0, page: 2, pages: 1, limit: 50 })
    };

    await fetchRiskCenterSnapshot(
      {
        dbType: "mysql",
        limit: 50,
        page: 2,
        search: "db-critical",
        severity: "high",
        status: "warning",
        tag: "prod"
      },
      client
    );

    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/risk-center/cards?limit=50&page=2&severity=high&db_type=mysql&status=warning&tag=prod&search=db-critical"
    );
  });
});
