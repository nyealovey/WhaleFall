import { describe, expect, it, vi } from "vitest";

import { fetchCapacityDatabaseSnapshot, fetchCapacityInstanceSnapshot } from "./capacity";

describe("capacity api", () => {
  it("loads instance capacity list and summary with an explicit range", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ items: [{ id: 1, instance_id: 10 }], total: 1, page: 1, pages: 1, limit: 200 })
        .mockResolvedValueOnce({ summary: { total_instances: 1, total_size_mb: 1024 } })
        .mockResolvedValueOnce({ items: [{ id: 2, instance_id: 10, period_start: "2026-06-11" }], total: 1, page: 1, pages: 1, limit: 200 })
        .mockResolvedValueOnce({ items: [{ id: 3, instance_id: 10, period_start: "2026-06-11" }], total: 1, page: 1, pages: 1, limit: 200 })
        .mockResolvedValueOnce({ items: [{ id: 4, instance_id: 10, period_start: "2026-06-11" }], total: 1, page: 1, pages: 1, limit: 200 })
    };

    const snapshot = await fetchCapacityInstanceSnapshot(client, {
      startDate: "2026-05-12",
      endDate: "2026-06-11"
    });

    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/capacity/instances?period_type=daily&page=1&limit=200&start_date=2026-05-12&end_date=2026-06-11"
    );
    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/capacity/instances/summary?period_type=daily&start_date=2026-05-12&end_date=2026-06-11"
    );
    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/capacity/instances?period_type=daily&page=1&limit=200&start_date=2026-05-12&end_date=2026-06-11&get_all=true&chart_mode=instance"
    );
    expect(snapshot.list.items[0]?.instance_id).toBe(10);
    expect(snapshot.summary.total_instances).toBe(1);
    expect(snapshot.charts.trend.items[0]?.id).toBe(2);
    expect(snapshot.charts.change.items[0]?.id).toBe(3);
    expect(snapshot.charts.percent.items[0]?.id).toBe(4);
  });

  it("loads database capacity list and summary with an explicit range", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ items: [{ id: 2, database_name: "app_db" }], total: 1, page: 1, pages: 1, limit: 200 })
        .mockResolvedValueOnce({ summary: { total_databases: 1, total_size_mb: 2048 } })
        .mockResolvedValueOnce({ items: [{ id: 5, database_name: "app_db", period_start: "2026-06-11" }], total: 1, page: 1, pages: 1, limit: 200 })
        .mockResolvedValueOnce({ items: [{ id: 6, database_name: "app_db", period_start: "2026-06-11" }], total: 1, page: 1, pages: 1, limit: 200 })
        .mockResolvedValueOnce({ items: [{ id: 7, database_name: "app_db", period_start: "2026-06-11" }], total: 1, page: 1, pages: 1, limit: 200 })
    };

    const snapshot = await fetchCapacityDatabaseSnapshot(client, {
      startDate: "2026-05-12",
      endDate: "2026-06-11"
    });

    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/capacity/databases?period_type=daily&page=1&limit=200&start_date=2026-05-12&end_date=2026-06-11"
    );
    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/capacity/databases/summary?period_type=daily&start_date=2026-05-12&end_date=2026-06-11"
    );
    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/capacity/databases?period_type=daily&page=1&limit=200&start_date=2026-05-12&end_date=2026-06-11&get_all=true&chart_mode=database"
    );
    expect(snapshot.list.items[0]?.database_name).toBe("app_db");
    expect(snapshot.summary.total_databases).toBe(1);
    expect(snapshot.charts.trend.items[0]?.id).toBe(5);
    expect(snapshot.charts.change.items[0]?.id).toBe(6);
    expect(snapshot.charts.percent.items[0]?.id).toBe(7);
  });
});
