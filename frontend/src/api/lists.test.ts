import { describe, expect, it, vi } from "vitest";

import { fetchAccountLedgers, fetchDatabaseLedgers, fetchInstances } from "./lists";

describe("list api", () => {
  it("loads the first page of instances", async () => {
    const client = {
      get: vi.fn().mockResolvedValueOnce({ items: [{ id: 1, name: "mysql-prod" }], total: 1, page: 1, pages: 1, limit: 20 })
    };

    const result = await fetchInstances(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/instances?page=1&limit=20");
    expect(result.items[0]?.name).toBe("mysql-prod");
  });

  it("loads the first page of database ledgers", async () => {
    const client = {
      get: vi.fn().mockResolvedValueOnce({ items: [{ id: 1, database_name: "app_db" }], total: 1, page: 1, limit: 20 })
    };

    const result = await fetchDatabaseLedgers(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/databases/ledgers?page=1&limit=20");
    expect(result.items[0]?.database_name).toBe("app_db");
  });

  it("loads the first page of account ledgers", async () => {
    const client = {
      get: vi.fn().mockResolvedValueOnce({ items: [{ id: 1, username: "readonly" }], total: 1, page: 1, pages: 1, limit: 20 })
    };

    const result = await fetchAccountLedgers(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/ledgers?page=1&limit=20");
    expect(result.items[0]?.username).toBe("readonly");
  });
});
