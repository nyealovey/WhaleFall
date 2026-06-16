import { describe, expect, it, vi } from "vitest";

import {
  fetchAccountChangeHistory,
  fetchAccountLedgers,
  fetchAccountPermissions,
  fetchDatabaseLedgers,
  fetchInstanceAgAccounts,
  fetchDatabaseTableSizes,
  fetchInstanceDatabaseSizes,
  fetchInstanceAuditInfo,
  fetchInstanceBackupInfo,
  fetchInstanceConnectionStatus,
  fetchInstanceDetail,
  fetchInstanceAccounts,
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
        .mockResolvedValueOnce({ instance_id: 7, status: "ok", last_connected: "2026-06-11T01:00:00+00:00" })
        .mockResolvedValueOnce({ instance_id: 7, facts: { audit_count: 2 }, snapshot: { server_audits: [] } })
        .mockResolvedValueOnce({ instance_id: 7, backup_status: "backed_up", restore_point_count: 3 })
        .mockResolvedValueOnce({ items: [{ id: 8, username: "readonly" }], total: 1, page: 1, pages: 1, limit: 200 })
        .mockResolvedValueOnce({ cluster: { id: 2, name: "ag-cluster" }, items: [{ id: 9, username: "ag_reader" }], total: 1 })
        .mockResolvedValueOnce({ total: 1, page: 1, pages: 1, limit: 100, total_size_mb: 2048, databases: [{ database_name: "app_db" }] })
        .mockResolvedValueOnce({ account: { id: 8, username: "readonly" }, permissions: { snapshot: { roles: ["reader"] } } })
        .mockResolvedValueOnce({ account: { id: 8, username: "readonly" }, history: [{ id: 1, change_type: "grant" }] })
        .mockResolvedValueOnce({ total: 1, page: 1, pages: 1, limit: 20, tables: [{ table_name: "orders" }] })
    };

    await fetchInstanceDetail(7, client);
    await fetchInstanceConnectionStatus(7, client);
    await fetchInstanceAuditInfo(7, client);
    await fetchInstanceBackupInfo(7, client);
    const accounts = await fetchInstanceAccounts(7, client);
    const agAccounts = await fetchInstanceAgAccounts(7, client);
    const databaseSizes = await fetchInstanceDatabaseSizes(7, client);
    await fetchAccountPermissions(8, client);
    await fetchAccountChangeHistory(8, client);
    const tableSizes = await fetchDatabaseTableSizes(9, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/instances/7");
    expect(client.get).toHaveBeenCalledWith("/api/v1/instances/7/connection-status");
    expect(client.get).toHaveBeenCalledWith("/api/v1/instances/7/audit-info");
    expect(client.get).toHaveBeenCalledWith("/api/v1/instances/7/backup-info");
    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/accounts/ledgers?page=1&limit=200&instance_id=7&sort=username&order=asc&include_roles=true&owner_type=instance"
    );
    expect(client.get).toHaveBeenCalledWith("/api/v1/instances/7/ag-accounts");
    expect(client.get).toHaveBeenCalledWith("/api/v1/databases/sizes?instance_id=7&latest_only=true&include_inactive=true&page=1&limit=100");
    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/ledgers/8/permissions");
    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/ledgers/8/change-history");
    expect(client.get).toHaveBeenCalledWith("/api/v1/databases/9/tables/sizes?page=1&limit=200");
    expect(accounts.items[0]?.username).toBe("readonly");
    expect(agAccounts.items[0]?.username).toBe("ag_reader");
    expect(databaseSizes.databases[0]?.database_name).toBe("app_db");
    expect(tableSizes.tables[0]?.table_name).toBe("orders");
  });
});
