import { describe, expect, it, vi } from "vitest";

import {
  fetchAccountClassificationsSnapshot,
  fetchAccountClassificationPermissions,
  fetchAccountClassificationRuleDetail,
  fetchClassificationStatisticsSnapshot,
  fetchClustersSnapshot,
  fetchMySqlClusterDetail,
  fetchSqlServerClusterDetail,
  fetchCredentialsSnapshot,
  fetchPartitionsSnapshot,
  fetchSchedulerSnapshot,
  fetchSyncSessionDetail,
  fetchSyncSessionErrorLogs,
  fetchSettingsSnapshot,
  fetchSyncSessionsSnapshot,
  fetchTagBulkOptions,
  fetchTagsSnapshot,
  fetchUsersSnapshot
} from "./readOnly";

describe("read-only migration api", () => {
  it("loads SQL Server and MySQL clusters", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ items: [{ id: 1, name: "sql-ag" }], total: 1, page: 1, pages: 1, limit: 20 })
        .mockResolvedValueOnce({ items: [{ id: 2, name: "mysql-repl" }], total: 1, page: 1, pages: 1, limit: 20 })
    };

    const snapshot = await fetchClustersSnapshot(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/sqlserver-clusters?page=1&limit=200");
    expect(client.get).toHaveBeenCalledWith("/api/v1/mysql-clusters?page=1&limit=200");
    expect(snapshot.sqlServer.items[0]?.name).toBe("sql-ag");
    expect(snapshot.mySql.items[0]?.name).toBe("mysql-repl");
  });

  it("loads SQL Server and MySQL cluster details", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({
          cluster: { id: 1, name: "sql-ag" },
          instances: [{ id: 11, name: "sql-node-1" }],
          availability_groups: [{ id: 21, name: "ag-sales" }]
        })
        .mockResolvedValueOnce({
          cluster: { id: 2, name: "mysql-repl" },
          instances: [{ id: 12, name: "mysql-primary" }]
        })
    };

    const sqlServer = await fetchSqlServerClusterDetail(1, client);
    const mySql = await fetchMySqlClusterDetail(2, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/sqlserver-clusters/1");
    expect(client.get).toHaveBeenCalledWith("/api/v1/mysql-clusters/2");
    expect(sqlServer.availability_groups[0]?.name).toBe("ag-sales");
    expect(mySql.instances[0]?.name).toBe("mysql-primary");
  });

  it("loads classifications and rules", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ classifications: [{ id: 1, display_name: "DBA" }] })
        .mockResolvedValueOnce({ rules_by_db_type: { mysql: [{ id: 9, rule_name: "root" }] } })
    };

    const snapshot = await fetchAccountClassificationsSnapshot(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/classifications");
    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/classifications/rules");
    expect(snapshot.classifications[0]?.display_name).toBe("DBA");
    expect(snapshot.rulesByDbType.mysql?.[0]?.rule_name).toBe("root");
  });

  it("loads account classification rule detail and permission metadata", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({
          rule: {
            id: 9,
            rule_name: "root rule",
            db_type: "mysql",
            rule_expression: { fn: "username_like", args: ["root"] }
          }
        })
        .mockResolvedValueOnce({ permissions: { mysql: ["SELECT", "SUPER"] } })
    };

    const detail = await fetchAccountClassificationRuleDetail(9, client);
    const permissions = await fetchAccountClassificationPermissions("mysql", client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/classifications/rules/9");
    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/classifications/permissions/mysql");
    expect(detail.rule.rule_name).toBe("root rule");
    expect(permissions.permissions).toEqual({ mysql: ["SELECT", "SUPER"] });
  });

  it("loads classification statistics and trend series", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ dba: { total_accounts: 8 } })
        .mockResolvedValueOnce({ series: [{ classification_name: "DBA", points: [] }], buckets: [] })
    };

    const snapshot = await fetchClassificationStatisticsSnapshot(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/statistics/classifications");
    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/statistics/classifications/trends?period_type=daily&periods=7");
    expect(snapshot.stats.dba).toEqual({ total_accounts: 8 });
    expect(snapshot.trends.series[0]?.classification_name).toBe("DBA");
  });

  it("loads automation lists", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce([{ id: "job-1", task_name: "同步任务" }])
        .mockResolvedValueOnce({ items: [{ session_id: "s-1" }], total: 1, page: 1, pages: 1 })
    };

    const scheduler = await fetchSchedulerSnapshot(client);
    const sessions = await fetchSyncSessionsSnapshot(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/scheduler/jobs");
    expect(client.get).toHaveBeenCalledWith("/api/v1/sync-sessions?page=1&limit=100");
    expect(scheduler.jobs[0]?.task_name).toBe("同步任务");
    expect(sessions.items[0]?.session_id).toBe("s-1");
  });

  it("loads sync session detail and error logs", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ session: { session_id: "s-1", instance_records: [{ instance_name: "mysql-1" }] } })
        .mockResolvedValueOnce({ session: { session_id: "s-1" }, error_records: [{ error_message: "failed" }], error_count: 1 })
    };

    const detail = await fetchSyncSessionDetail("s-1", client);
    const errors = await fetchSyncSessionErrorLogs("s-1", client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/sync-sessions/s-1");
    expect(client.get).toHaveBeenCalledWith("/api/v1/sync-sessions/s-1/error-logs");
    expect(detail.session.instance_records[0]?.instance_name).toBe("mysql-1");
    expect(errors.error_count).toBe(1);
  });

  it("loads system administration snapshots", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ items: [{ id: 1, username: "admin" }], total: 1, page: 1, pages: 1, limit: 10 })
        .mockResolvedValueOnce({ total: 1, active: 1, inactive: 0, admin: 1, user: 0 })
        .mockResolvedValueOnce({ items: [{ id: 2, name: "prod" }], total: 1, page: 1, pages: 1, limit: 20 })
        .mockResolvedValueOnce({ items: [{ id: 3, display_name: "生产" }], total: 1, page: 1, pages: 1, limit: 20, stats: { total: 1, active: 1, inactive: 0, category_count: 1 } })
        .mockResolvedValueOnce({ categories: ["env"] })
        .mockResolvedValueOnce({ data: { status: "healthy" }, timestamp: "2026-06-11T00:00:00+08:00" })
        .mockResolvedValueOnce({ items: [{ name: "p202606" }], total: 1, page: 1, pages: 1, limit: 20 })
        .mockResolvedValueOnce({ labels: ["06-11"], datasets: [], dataPointCount: 1, timeRange: "7d", yAxisLabel: "count", chartTitle: "core", periodType: "daily" })
    };

    const users = await fetchUsersSnapshot(client);
    const credentials = await fetchCredentialsSnapshot(client);
    const tags = await fetchTagsSnapshot(client);
    const partitions = await fetchPartitionsSnapshot(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/users?page=1&limit=200");
    expect(client.get).toHaveBeenCalledWith("/api/v1/users/stats");
    expect(client.get).toHaveBeenCalledWith("/api/v1/credentials?page=1&limit=200");
    expect(client.get).toHaveBeenCalledWith("/api/v1/tags?page=1&limit=200");
    expect(client.get).toHaveBeenCalledWith("/api/v1/tags/categories");
    expect(client.get).toHaveBeenCalledWith("/api/v1/partitions/status");
    expect(client.get).toHaveBeenCalledWith("/api/v1/partitions?page=1&limit=200");
    expect(client.get).toHaveBeenCalledWith("/api/v1/partitions/core-metrics?period_type=daily&days=7");
    expect(users.stats.total).toBe(1);
    expect(credentials.items[0]?.name).toBe("prod");
    expect(tags.categories[0]).toBe("env");
    expect(partitions.list.items[0]?.name).toBe("p202606");
  });

  it("loads tag bulk assignment options", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ instances: [{ id: 1, name: "mysql-prod", db_type: "mysql" }] })
        .mockResolvedValueOnce({ tags: [{ id: 9, display_name: "生产", category: "env" }], category_names: ["env"] })
    };

    const options = await fetchTagBulkOptions(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/tags/bulk/instances");
    expect(client.get).toHaveBeenCalledWith("/api/v1/tags/bulk/tags");
    expect(options.instances[0]?.name).toBe("mysql-prod");
    expect(options.tags[0]?.display_name).toBe("生产");
  });

  it("loads settings overview from read-only configuration endpoints", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ smtp_ready: true, settings: { global_enabled: true } })
        .mockResolvedValueOnce({ rules: [{ rule_key: "backup_issue", enabled: true }] })
        .mockResolvedValueOnce({ provider_ready: true, api_credentials: [] })
        .mockResolvedValueOnce({ provider_ready: false, veeam_credentials: [], sources: [] })
        .mockResolvedValueOnce({ configs: [{ id: 1, name: "corp" }] })
    };

    const snapshot = await fetchSettingsSnapshot(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/alerts/email-settings");
    expect(client.get).toHaveBeenCalledWith("/api/v1/risk-center/rules");
    expect(client.get).toHaveBeenCalledWith("/api/v1/integrations/jumpserver/source");
    expect(client.get).toHaveBeenCalledWith("/api/v1/integrations/veeam/sources");
    expect(client.get).toHaveBeenCalledWith("/api/v1/ad-domain-configs");
    expect(snapshot.alerts.smtp_ready).toBe(true);
    expect(snapshot.riskRules[0]?.rule_key).toBe("backup_issue");
    expect(snapshot.adDomains.configs[0]?.name).toBe("corp");
  });
});
