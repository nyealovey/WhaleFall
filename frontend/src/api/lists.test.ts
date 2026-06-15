import { describe, expect, it, vi } from "vitest";

import {
  fetchAccountChangeHistory,
  fetchAccountLedgers,
  fetchAccountPermissions,
  fetchDatabaseLedgers,
  fetchDatabaseTableSizes,
  fetchInstanceDetail,
  fetchInstances
} from "./lists";

describe("list api", () => {
  it("loads the first page of instances", async () => {
    const client = {
      get: vi.fn().mockResolvedValueOnce({ items: [{ id: 1, name: "mysql-prod" }], total: 1, page: 1, pages: 1, limit: 20 })
    };

    const result = await fetchInstances(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/instances?page=1&limit=200");
    expect(result.items[0]?.name).toBe("mysql-prod");
  });

  it("loads the first page of database ledgers", async () => {
    const client = {
      get: vi.fn().mockResolvedValueOnce({ items: [{ id: 1, database_name: "app_db" }], total: 1, page: 1, limit: 20 })
    };

    const result = await fetchDatabaseLedgers(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/databases/ledgers?page=1&limit=200");
    expect(result.items[0]?.database_name).toBe("app_db");
  });

  it("loads the first page of account ledgers", async () => {
    const client = {
      get: vi.fn().mockResolvedValueOnce({ items: [{ id: 1, username: "readonly" }], total: 1, page: 1, pages: 1, limit: 20 })
    };

    const result = await fetchAccountLedgers(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/ledgers?page=1&limit=200");
    expect(result.items[0]?.username).toBe("readonly");
  });

  it("loads list detail resources from v1 endpoints", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ instance: { id: 7, name: "mysql-prod" } })
        .mockResolvedValueOnce({ account: { id: 8, username: "readonly" }, permissions: { snapshot: { roles: ["reader"] } } })
        .mockResolvedValueOnce({ account: { id: 8, username: "readonly" }, history: [{ id: 1, change_type: "grant" }] })
        .mockResolvedValueOnce({ total: 1, page: 1, pages: 1, limit: 20, tables: [{ table_name: "orders" }] })
    };

    await fetchInstanceDetail(7, client);
    await fetchAccountPermissions(8, client);
    await fetchAccountChangeHistory(8, client);
    const tableSizes = await fetchDatabaseTableSizes(9, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/instances/7");
    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/ledgers/8/permissions");
    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/ledgers/8/change-history");
    expect(client.get).toHaveBeenCalledWith("/api/v1/databases/9/tables/sizes?page=1&limit=200");
    expect(tableSizes.tables[0]?.table_name).toBe("orders");
  });
});
