import { describe, expect, it, vi } from "vitest";

import {
  fetchAccountClassificationsSnapshot,
  fetchAccountClassificationPermissions,
  fetchAccountClassificationRuleDetail,
  fetchAccountScopeOptions,
  fetchClassificationStatisticsSnapshot,
  fetchClusterInstanceOptions,
  fetchClustersSnapshot,
  fetchMySqlClusterDetail,
  fetchSqlServerAvailabilityGroupDashboard,
  fetchSqlServerClusterDetail,
  fetchCredentialsSnapshot,
  fetchPartitionsSnapshot,
  fetchSchedulerSnapshot,
  fetchSchedulerJobDetail,
  fetchTaskRunDetail,
  fetchTaskRunErrorLogs,
  fetchSettingsSnapshot,
  fetchTaskRunsSnapshot,
  fetchTagBulkOptions,
  fetchTagsSnapshot,
  fetchUsersSnapshot
} from "./readOnly";

describe("read-only api", () => {
  it("loads SQL Server and MySQL clusters", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ items: [{ id: 1, name: "sql-ag" }], total: 1, page: 1, pages: 1, limit: 20 })
        .mockResolvedValueOnce({ items: [{ id: 2, name: "mysql-repl" }], total: 1, page: 1, pages: 1, limit: 20 })
    };

    const snapshot = await fetchClustersSnapshot(
      {
        sqlServer: { page: 2, limit: 20, search: "ag", status: "enabled" },
        mySql: { page: 3, limit: 50, search: "replica", status: "disabled" }
      },
      client
    );

    expect(client.get).toHaveBeenCalledWith("/api/v1/sqlserver-clusters?page=2&limit=20&search=ag&status=enabled");
    expect(client.get).toHaveBeenCalledWith("/api/v1/mysql-clusters?page=3&limit=50&search=replica&status=disabled");
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

  it("loads SQL Server availability group dashboard", async () => {
    const client = {
      get: vi.fn().mockResolvedValue({
        availability_group: { id: 21, name: "ag-sales" },
        replicas: [{ replica_server_name: "sql-node-1" }],
        databases: [{ database_name: "sales" }]
      })
    };

    const dashboard = await fetchSqlServerAvailabilityGroupDashboard(1, 21, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/sqlserver-clusters/1/availability-groups/21/dashboard");
    expect(dashboard.availability_group?.name).toBe("ag-sales");
    expect(dashboard.replicas[0]?.replica_server_name).toBe("sql-node-1");
  });

  it("loads cluster instance options by database type", async () => {
    const client = {
      get: vi.fn().mockResolvedValue({
        items: [{ id: 11, name: "sql-node-1", host: "10.0.0.11", db_type: "sqlserver" }],
        total: 1,
        page: 1,
        pages: 1,
        limit: 200
      })
    };

    const options = await fetchClusterInstanceOptions("sqlserver", client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/instances?page=1&limit=200&db_type=sqlserver");
    expect(options[0]?.name).toBe("sql-node-1");
  });

  it("loads paginated users, credentials, tags, and partitions with filters", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ items: [], total: 0, page: 2, pages: 1, limit: 20 })
        .mockResolvedValueOnce({ total: 0, active: 0, inactive: 0, admin: 0, user: 0 })
        .mockResolvedValueOnce({ items: [], total: 0, page: 3, pages: 1, limit: 50 })
        .mockResolvedValueOnce({ items: [], total: 0, page: 4, pages: 1, limit: 100, stats: {} })
        .mockResolvedValueOnce({ categories: ["env"] })
        .mockResolvedValueOnce({ data: { status: "healthy" } })
        .mockResolvedValueOnce({ items: [], total: 0, page: 5, pages: 1, limit: 20 })
        .mockResolvedValueOnce({ labels: [], datasets: [], dataPointCount: 0, timeRange: "7d", yAxisLabel: "", chartTitle: "", periodType: "daily" })
    };

    await fetchUsersSnapshot({ page: 2, limit: 20, search: "admin", role: "admin", status: "active" }, client);
    await fetchCredentialsSnapshot({ page: 3, limit: 50, search: "prod", credentialType: "password", dbType: "mysql", status: "active" }, client);
    await fetchTagsSnapshot({ page: 4, limit: 100, search: "生产", category: "env", status: "active" }, client);
    await fetchPartitionsSnapshot({ page: 5, limit: 20, search: "2026", tableType: "range", status: "current", periodType: "daily", days: 7 }, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/users?page=2&limit=20&search=admin&role=admin&status=active");
    expect(client.get).toHaveBeenCalledWith("/api/v1/credentials?page=3&limit=50&search=prod&credential_type=password&db_type=mysql&status=active");
    expect(client.get).toHaveBeenCalledWith("/api/v1/tags?page=4&limit=100&search=%E7%94%9F%E4%BA%A7&category=env&status=active");
    expect(client.get).toHaveBeenCalledWith("/api/v1/partitions?page=5&limit=20&search=2026&table_type=range&status=current");
  });

  it("loads account scope options by database type", async () => {
    const client = {
      get: vi.fn().mockResolvedValue({
        account_scopes: [
          {
            value: "instance:11",
            label: "mysql-prod (MYSQL)",
            db_type: "mysql",
            owner_type: "instance",
            owner_id: 11,
            name: "mysql-prod",
            host: "10.0.0.11"
          }
        ]
      })
    };

    const options = await fetchAccountScopeOptions("mysql", client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/instances/account-scope-options?db_type=mysql");
    expect(options[0]?.value).toBe("instance:11");
  });

  it("loads classifications and rules", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ classifications: [{ id: 1, display_name: "DBA" }] })
        .mockResolvedValueOnce({ rules_by_db_type: { mysql: [{ id: 9, rule_name: "root" }] } })
        .mockResolvedValueOnce({ rule_stats: [{ rule_id: 9, matched_accounts_count: 347 }] })
    };

    const snapshot = await fetchAccountClassificationsSnapshot(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/classifications");
    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/classifications/rules");
    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/statistics/rules?rule_ids=9");
    expect(snapshot.classifications[0]?.display_name).toBe("DBA");
    expect(snapshot.rulesByDbType.mysql?.[0]?.rule_name).toBe("root");
    expect(snapshot.rulesByDbType.mysql?.[0]?.matched_accounts_count).toBe(347);
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

    const snapshot = await fetchClassificationStatisticsSnapshot({}, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/statistics/classifications");
    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/statistics/classifications/trends?period_type=daily&periods=7");
    expect(snapshot.stats.dba).toEqual({ total_accounts: 8 });
    expect(snapshot.trends.series[0]?.classification_name).toBe("DBA");
  });

  it("loads classification rule overview, contributions, and selected trends", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ dba: { total_accounts: 8 } })
        .mockResolvedValueOnce({ series: [{ classification_name: "DBA", points: [] }], buckets: [] })
        .mockResolvedValueOnce({ trend: [{ period_start: "2026-06-11", value: 8 }] })
        .mockResolvedValueOnce({ rules: [{ rule_id: 9, rule_name: "root rule", latest_value_sum: 8 }] })
        .mockResolvedValueOnce({ contributions: [{ rule_id: 9, rule_name: "root rule", value_sum: 8 }] })
        .mockResolvedValueOnce({ trend: [{ period_start: "2026-06-11", value: 8 }] })
    };

    const snapshot = await fetchClassificationStatisticsSnapshot(
      {
        accountScope: "instance:11",
        classificationId: 1,
        dbType: "mysql",
        periodType: "weekly",
        periods: 14,
        ruleId: 9,
        ruleStatus: "archived"
      },
      client
    );

    expect(client.get).toHaveBeenCalledWith("/api/v1/accounts/statistics/classifications");
    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/accounts/statistics/classifications/trends?period_type=weekly&periods=14&db_type=mysql&account_scope=instance%3A11"
    );
    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/accounts/statistics/classifications/trend?classification_id=1&period_type=weekly&periods=14&db_type=mysql&account_scope=instance%3A11"
    );
    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/accounts/statistics/rules/overview?classification_id=1&period_type=weekly&periods=14&db_type=mysql&account_scope=instance%3A11&status=archived"
    );
    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/accounts/statistics/rules/contributions?classification_id=1&period_type=weekly&db_type=mysql&account_scope=instance%3A11&limit=10"
    );
    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/accounts/statistics/rules/trend?rule_id=9&period_type=weekly&periods=14&db_type=mysql&account_scope=instance%3A11"
    );
    expect(snapshot.selectedClassificationTrend?.[0]?.value).toBe(8);
    expect(snapshot.rulesOverview?.rules[0]?.rule_name).toBe("root rule");
    expect(snapshot.ruleContributions?.contributions[0]?.value_sum).toBe(8);
    expect(snapshot.selectedRuleTrend?.[0]?.value).toBe(8);
  });

  it("loads automation lists", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce([{ id: "job-1", task_name: "同步任务" }])
        .mockResolvedValueOnce({ items: [{ run_id: "s-1" }], total: 1, page: 1, pages: 1 })
    };

    const scheduler = await fetchSchedulerSnapshot(client);
    const sessions = await fetchTaskRunsSnapshot({ page: 2, limit: 20, status: "failed", taskCategory: "notification" }, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/scheduler/jobs");
    expect(client.get).toHaveBeenCalledWith("/api/v1/task-runs?page=2&limit=20&task_category=notification&status=failed&sort=started_at&order=desc");
    expect(scheduler.jobs[0]?.task_name).toBe("同步任务");
    expect(sessions.items[0]?.run_id).toBe("s-1");
  });

  it("loads scheduler job details", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ id: "job-1", trigger: "cron[minute='*/5']", func: "tasks.sync", max_instances: 1 })
    };

    const job = await fetchSchedulerJobDetail("job-1", client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/scheduler/jobs/job-1");
    expect(job.trigger).toContain("cron");
  });

  it("loads sync session detail and error logs", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ run: { run_id: "s-1" }, items: [{ item_name: "mysql-1" }] })
        .mockResolvedValueOnce({ run: { run_id: "s-1" }, items: [{ error_message: "failed" }], error_count: 1 })
    };

    const detail = await fetchTaskRunDetail("s-1", client);
    const errors = await fetchTaskRunErrorLogs("s-1", client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/task-runs/s-1");
    expect(client.get).toHaveBeenCalledWith("/api/v1/task-runs/s-1/error-logs");
    expect(detail.items[0]?.item_name).toBe("mysql-1");
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

    const users = await fetchUsersSnapshot({}, client);
    const credentials = await fetchCredentialsSnapshot({}, client);
    const tags = await fetchTagsSnapshot({}, client);
    const partitions = await fetchPartitionsSnapshot({}, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/users?page=1&limit=20");
    expect(client.get).toHaveBeenCalledWith("/api/v1/users/stats");
    expect(client.get).toHaveBeenCalledWith("/api/v1/credentials?page=1&limit=20");
    expect(client.get).toHaveBeenCalledWith("/api/v1/tags?page=1&limit=20");
    expect(client.get).toHaveBeenCalledWith("/api/v1/tags/categories");
    expect(client.get).toHaveBeenCalledWith("/api/v1/partitions/status");
    expect(client.get).toHaveBeenCalledWith("/api/v1/partitions?page=1&limit=20");
    expect(client.get).toHaveBeenCalledWith("/api/v1/partitions/core-metrics?period_type=daily&days=7");
    expect(users.stats.total).toBe(1);
    expect(credentials.items[0]?.name).toBe("prod");
    expect(tags.categories[0]).toBe("env");
    expect(partitions.list.items[0]?.name).toBe("p202606");
  });

  it("loads partitions with selected core metric period", async () => {
    const client = {
      get: vi
        .fn()
        .mockResolvedValueOnce({ data: { status: "healthy" }, timestamp: "2026-06-11T00:00:00+08:00" })
        .mockResolvedValueOnce({ items: [], total: 0, page: 1, pages: 1, limit: 200 })
        .mockResolvedValueOnce({ labels: [], datasets: [], dataPointCount: 0, timeRange: "28d", yAxisLabel: "count", chartTitle: "core", periodType: "weekly" })
    };

    await fetchPartitionsSnapshot({ days: 28, periodType: "weekly" }, client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/partitions/core-metrics?period_type=weekly&days=28");
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
        .mockResolvedValueOnce({ items: [{ id: 5, name: "ldap-main" }], total: 1, page: 1, pages: 1, limit: 200 })
    };

    const snapshot = await fetchSettingsSnapshot(client);

    expect(client.get).toHaveBeenCalledWith("/api/v1/alerts/email-settings");
    expect(client.get).toHaveBeenCalledWith("/api/v1/risk-center/rules");
    expect(client.get).toHaveBeenCalledWith("/api/v1/integrations/jumpserver/source");
    expect(client.get).toHaveBeenCalledWith("/api/v1/integrations/veeam/sources");
    expect(client.get).toHaveBeenCalledWith("/api/v1/ad-domain-configs");
    expect(client.get).toHaveBeenCalledWith("/api/v1/credentials?page=1&limit=200&credential_type=ldap&status=active");
    expect(snapshot.alerts.smtp_ready).toBe(true);
    expect(snapshot.riskRules[0]?.rule_key).toBe("backup_issue");
    expect(snapshot.adDomains.configs[0]?.name).toBe("corp");
    expect(snapshot.adDomains.credentials?.[0]?.name).toBe("ldap-main");
  });
});
