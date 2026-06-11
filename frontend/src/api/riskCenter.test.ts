import { describe, expect, it, vi } from "vitest";

import { fetchRiskCenterSnapshot } from "./riskCenter";

describe("fetchRiskCenterSnapshot", () => {
  it("loads summary and a bounded first page of risk cards", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ total_instances: 2, severity_counts: { high: 1 }, top_risks: [] })
        .mockResolvedValueOnce({ items: [{ instance_id: 1, name: "db01" }], total: 1, page: 1, pages: 1, limit: 12 })
    };

    const snapshot = await fetchRiskCenterSnapshot(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/risk-center/summary");
    expect(client.get).toHaveBeenCalledWith("/api/v1/risk-center/cards?limit=12");
    expect(snapshot.summary.total_instances).toBe(2);
    expect(snapshot.cards.items[0]?.name).toBe("db01");
  });
});
