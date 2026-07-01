import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchAccountClassificationPermissions,
  fetchAccountScopeOptions,
  fetchClusterInstanceOptions,
  fetchClassificationStatisticsSnapshot,
  fetchMySqlClusterDetail,
  fetchPartitionsSnapshot,
  fetchSchedulerSnapshot,
  fetchSchedulerJobDetail,
  fetchTaskRunsSnapshot,
} from "@/api/readOnly";

import { CredentialsPage, TagsPage, UsersPage } from "./CatalogAdminPages";
import { AccountClassificationsPage, ClassificationStatisticsPage } from "./ClassificationPages";
import { ClustersPage } from "./ClustersPage";
import { PartitionsPage } from "./PartitionsPage";
import { SchedulerPage } from "./SchedulerPage";
import { SettingsPage } from "./SettingsPage";
import { SyncSessionsPage } from "./SyncSessionsPage";
import { TagBulkAssignPage } from "./TagBulkAssignPage";

const adminUser = { id: 1, username: "admin", role: "admin", is_active: true };
const viewerUser = { id: 2, username: "viewer", role: "viewer", is_active: true };

const actionMocks = vi.hoisted(() => ({
  assignTagsToInstances: vi.fn(async () => ({ ok: true })),
  autoClassifyAccounts: vi.fn(async () => ({ ok: true })),
  cancelSyncSession: vi.fn(async () => ({ ok: true })),
  createAdDomainConfig: vi.fn(async () => ({ ok: true })),
  createAccountClassification: vi.fn(async () => ({ ok: true })),
  createAccountClassificationRule: vi.fn(async () => ({ ok: true })),
  cleanupPartitions: vi.fn(async () => ({ ok: true })),
  createMySqlCluster: vi.fn(async () => ({ ok: true })),
  createSqlServerAvailabilityGroup: vi.fn(async () => ({ ok: true })),
  createPartition: vi.fn(async () => ({ ok: true })),
  createSqlServerCluster: vi.fn(async () => ({ ok: true })),
  createCredential: vi.fn(async () => ({ ok: true })),
  createTag: vi.fn(async () => ({ ok: true })),
  createUser: vi.fn(async () => ({ ok: true })),
  createVeeamSource: vi.fn(async () => ({ ok: true })),
  deleteAccountClassification: vi.fn(async () => ({ ok: true })),
  deleteAccountClassificationRule: vi.fn(async () => ({ ok: true })),
  deleteCredential: vi.fn(async () => ({ ok: true })),
  deleteSchedulerJob: vi.fn(async () => ({ ok: true })),
  deleteTag: vi.fn(async () => ({ ok: true })),
  deleteUser: vi.fn(async () => ({ ok: true })),
  pauseSchedulerJob: vi.fn(async () => ({ ok: true })),
  reloadSchedulerJobs: vi.fn(async () => ({ ok: true })),
  disableVeeamSource: vi.fn(async () => ({ ok: true })),
  enableVeeamSource: vi.fn(async () => ({ ok: true })),
  removeAllTagsFromInstances: vi.fn(async () => ({ ok: true })),
  removeTagsFromInstances: vi.fn(async () => ({ ok: true })),
  resumeSchedulerJob: vi.fn(async () => ({ ok: true })),
  runSchedulerJob: vi.fn(async () => ({ ok: true })),
  saveAlertSettings: vi.fn(async () => ({ ok: true })),
  saveJumpServerSource: vi.fn(async () => ({ ok: true })),
  saveRiskRules: vi.fn(async () => ({ ok: true })),
  sendAlertTestEmail: vi.fn(async () => ({ ok: true })),
  sendFeishuTest: vi.fn(async () => ({ ok: true })),
  setAdDomainConfigEnabled: vi.fn(async () => ({ ok: true })),
  testAdDomainConfig: vi.fn(async () => ({ ok: true })),
  updateAccountClassification: vi.fn(async () => ({ ok: true })),
  updateAccountClassificationRule: vi.fn(async () => ({ ok: true })),
  validateAccountClassificationRuleExpression: vi.fn(async () => ({ rule_expression: { fn: "username_like", args: ["readonly"] } })),
  updateAdDomainConfig: vi.fn(async () => ({ ok: true })),
  replaceMySqlClusterInstances: vi.fn(async () => ({ ok: true })),
  replaceSqlServerClusterInstances: vi.fn(async () => ({ ok: true })),
  updateCredential: vi.fn(async () => ({ ok: true })),
  updateSchedulerJob: vi.fn(async () => ({ ok: true })),
  updateTag: vi.fn(async () => ({ ok: true })),
  updateUser: vi.fn(async () => ({ ok: true })),
  updateVeeamSource: vi.fn(async () => ({ ok: true })),
  syncAdDomains: vi.fn(async () => ({ ok: true })),
  syncJumpServer: vi.fn(async () => ({ ok: true })),
  syncMySqlClusterTopology: vi.fn(async () => ({ ok: true })),
  syncSqlServerAgAccounts: vi.fn(async () => ({ ok: true })),
  syncSqlServerAvailabilityGroups: vi.fn(async () => ({ ok: true })),
  syncSqlServerClusterStatus: vi.fn(async () => ({ ok: true })),
  syncVeeam: vi.fn(async () => ({ ok: true })),
  unbindJumpServer: vi.fn(async () => ({ ok: true })),
  deleteVeeamSource: vi.fn(async () => ({ ok: true })),
  deleteAdDomainConfig: vi.fn(async () => ({ ok: true })),
  updateMySqlCluster: vi.fn(async () => ({ ok: true })),
  updateSqlServerAvailabilityGroup: vi.fn(async () => ({ ok: true })),
  updateSqlServerCluster: vi.fn(async () => ({ ok: true }))
}));

vi.mock("@/api/actions", () => actionMocks);

vi.mock("@/utils/action-feedback", () => ({
  runAction: vi.fn((promise: Promise<unknown>) => promise)
}));

const listApiMocks = vi.hoisted(() => ({
  fetchAccountLedgers: vi.fn(async () => ({
    items: [
      {
        id: 501,
        username: "WZ\\admin-zmian",
        instance_name: "AGDB10",
        instance_host: "10.10.10.177",
        db_type: "sqlserver",
        is_locked: false,
        is_superuser: true,
        is_active: true,
        is_deleted: false,
        ad_status: "unmatched",
        last_change_time: "2026-05-21T09:04:43+08:00",
        availability_reasons: [],
        classifications: [{ display_name: "分类" }],
        tags: [{ name: "prod", display_name: "生产环境" }, { name: "wenzhou", display_name: "温州" }, { name: "primary", display_name: "主从" }]
      }
    ],
    total: 1,
    page: 1,
    pages: 1,
    limit: 100
  }))
}));

vi.mock("@/api/lists", () => listApiMocks);

vi.mock("@/api/readOnly", () => ({
  fetchClustersSnapshot: vi.fn(async () => ({
    sqlServer: { items: [{ id: 1, name: "sql-ag", domain_name: "corp.local", is_enabled: true, instance_count: 2, availability_group_count: 1, last_status_sync_status: "completed", last_status_sync_at: "2026-06-11T09:00:00+08:00", last_ag_sync_status: "completed", last_ag_sync_at: "2026-06-11T10:00:00+08:00" }], total: 1, page: 1, pages: 1, limit: 20 },
    mySql: { items: [{ id: 2, name: "mysql-repl", is_enabled: true, instance_count: 3, last_topology_sync_status: "completed", last_topology_sync_at: "2026-06-11T11:00:00+08:00", abnormal_replica_count: 2 }], total: 1, page: 1, pages: 1, limit: 20 }
  })),
  fetchSqlServerClusterDetail: vi.fn(async () => ({
    cluster: { id: 1, name: "sql-ag", domain_name: "corp.local", description: "SQL Server 群集", is_enabled: true },
    instances: [{ id: 11, name: "sql-node-1", host: "10.0.0.11" }],
    availability_groups: [
      {
        id: 21,
        name: "ag-sales",
        listener_name: "ag-listener",
        listener_host: "ag.example",
        listener_port: 1433,
        connection_database: "master",
        last_sync_at: "2026-06-11T10:00:00+08:00",
        account_credential_id: 9,
        contained_enabled: true,
        is_enabled: true
      }
    ]
  })),
  fetchClusterInstanceOptions: vi.fn(async (dbType: "sqlserver" | "mysql") =>
    dbType === "sqlserver"
      ? [
          { id: 11, name: "sql-node-1", host: "10.0.0.11", db_type: "sqlserver" },
          { id: 13, name: "sql-node-2", host: "10.0.0.13", db_type: "sqlserver" }
        ]
      : [
          { id: 12, name: "mysql-primary", host: "10.0.0.21", db_type: "mysql" },
          { id: 14, name: "mysql-replica", host: "10.0.0.24", db_type: "mysql" }
        ]
  ),
  fetchSqlServerAvailabilityGroupDashboard: vi.fn(async () => ({
    summary: {
      ag_name: "ag-sales",
      cluster_name: "sql-ag",
      listener_name: "ag-listener",
      listener_host: "ag.example",
      listener_port: 1433,
      status: "normal",
      cluster_status: "normal",
      cluster_type: "SQL Server AG",
      primary_replica: "sql-node-1",
      last_checked_at: "2026-06-11T10:00:00+08:00"
    },
    replicas: [
      {
        replica_server_name: "sql-node-1",
        role_desc: "PRIMARY",
        availability_mode_desc: "SYNCHRONOUS_COMMIT",
        failover_mode_desc: "AUTOMATIC",
        connected_state_desc: "CONNECTED",
        synchronization_health_desc: "HEALTHY",
        status: "normal"
      }
    ],
    database_groups: [
      {
        replica_server_name: "sql-node-1",
        status: "normal",
        databases: [
          {
            database_name: "sales",
            synchronization_state_desc: "SYNCHRONIZED",
            synchronization_health_desc: "HEALTHY",
            failover_ready: true,
            log_send_queue_size: 0,
            redo_queue_size: 0,
            status: "normal"
          }
        ]
      }
    ],
    kpis: { total_databases: 1, abnormal_databases: 0, affected_replicas: 0 }
  })),
  fetchMySqlClusterDetail: vi.fn(async () => ({
    cluster: { id: 2, name: "mysql-repl", description: "MySQL replication 群集", is_enabled: true },
    instances: [{ id: 12, name: "mysql-primary", host: "10.0.0.21", role: "primary" }]
  })),
  fetchAccountClassificationsSnapshot: vi.fn(async () => ({
    classifications: [
      { id: 1, code: "dba", display_name: "DBA", risk_level: 2, rules_count: 1, is_system: true },
      { id: 2, code: "app", display_name: "App", risk_level: 4, rules_count: 0, is_system: false }
    ],
    rulesByDbType: {
      mysql: [
        {
          id: 9,
          rule_name: "root rule",
          classification_id: 1,
          classification_name: "DBA",
          db_type: "mysql",
          is_active: true,
          matched_accounts_count: 8,
          rule_expression: {
            version: 4,
            expr: { op: "OR", args: [{ fn: "has_privilege", args: { name: "SELECT", scope: "global" } }] }
          }
        }
      ]
    }
  })),
  fetchAccountClassificationRuleDetail: vi.fn(async () => ({
    rule: {
      id: 9,
      rule_name: "root rule",
      classification_id: 1,
      classification_name: "DBA",
      db_type: "mysql",
      rule_group_id: "rg-1",
      rule_version: 2,
      is_active: true,
      rule_expression: {
        version: 4,
        expr: {
          op: "AND",
          args: [
            { op: "OR", args: [{ fn: "has_privilege", args: { name: "SELECT", scope: "global" } }] },
            { op: "OR", args: [{ fn: "has_privilege", args: { name: "CREATE", scope: "database" } }] }
          ]
        }
      },
      created_at: "2026-06-01T00:00:00+08:00",
      updated_at: "2026-06-02T00:00:00+08:00"
    }
  })),
  fetchAccountClassificationPermissions: vi.fn(async (dbType: string) => {
    if (dbType === "mysql") {
      return {
        permissions: {
          global_privileges: [
            { name: "SELECT", description: "查询数据", introduced_in_major: null },
            { name: "SUPER", description: "超级权限", introduced_in_major: null }
          ],
          database_privileges: [{ name: "CREATE", description: "创建数据库对象", introduced_in_major: null }]
        }
      };
    }
    if (dbType === "postgresql") {
      return {
        permissions: {
          predefined_roles: [{ name: "pg_read_all_data", description: "读取所有数据", introduced_in_major: null }],
          role_attributes: [{ name: "CREATEDB", description: "创建数据库", introduced_in_major: null }],
          database_privileges: [{ name: "CONNECT", description: "连接数据库", introduced_in_major: null }]
        }
      };
    }
    return { permissions: {} };
  }),
  fetchAccountScopeOptions: vi.fn(async (dbType?: string) =>
    dbType === "mysql"
      ? [
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
      : []
  ),
  fetchClassificationStatisticsSnapshot: vi.fn(
    async (filters?: { classificationId?: string | number; ruleId?: string | number; ruleStatus?: string }) => ({
    stats: { dba: { total_accounts: 8, matched_accounts_count: 8 }, app: { total_accounts: 3, matched_accounts_count: 3 } },
    trends: {
      buckets: [{ period_start: "2026-06-05", period_end: "2026-06-05" }],
      series: [
        { classification_id: 1, classification_name: "DBA", points: [{ period_start: "2026-06-05", value: 8 }] },
        { classification_id: 2, classification_name: "App", points: [{ period_start: "2026-06-05", value: 3 }] }
      ]
    },
    selectedClassificationTrend: filters?.classificationId ? [{ period_start: "2026-06-05", value: 8 }] : undefined,
    selectedRuleTrend: filters?.ruleId ? [{ period_start: "2026-06-05", value: 8 }] : undefined,
    rulesOverview: filters?.classificationId
      ? {
          latest_coverage_days: 1,
          latest_expected_days: 1,
          rules: [
            {
              rule_id: 9,
              rule_name: "root rule",
              db_type: "mysql",
              is_active: filters.ruleStatus !== "archived",
              latest_value_sum: 8,
              latest_coverage_days: 1,
              latest_expected_days: 1,
              window_value_sum: 8
            }
          ]
        }
      : undefined,
    ruleContributions: filters?.classificationId
      ? {
          coverage_days: 1,
          expected_days: 1,
          contributions: [{ rule_id: 9, rule_name: "root rule", db_type: "mysql", is_active: true, value_sum: 8 }]
        }
      : undefined
  })),
  fetchSchedulerSnapshot: vi.fn(async () => ({
    jobs: [
      {
        id: "job-1",
        task_id: "job-1",
        name: "同步任务",
        task_name: "同步任务",
        func: "tasks.sync",
        state: "STATE_RUNNING",
        trigger_type: "cron",
        trigger_args: { second: "0", minute: "*/5", hour: "*", day: "*", month: "*", day_of_week: "*", year: "*", description: "每 5 分钟" },
        next_run_time: "2026-06-11 12:00",
        last_run_time: "2026-06-11 11:55",
        is_builtin: true
      },
      {
        id: "job-2",
        task_id: "job-2",
        name: "归档任务",
        task_name: "归档任务",
        state: "STATE_PAUSED",
        trigger_type: "cron",
        trigger_args: { hour: "2", description: "每日归档" },
        next_run_time: null,
        last_run_time: null,
        is_builtin: true
      }
    ]
  })),
  fetchSchedulerJobDetail: vi.fn(async () => ({
    id: "job-1",
    name: "同步任务",
    trigger: "cron[minute='*/5']",
    func: "tasks.sync",
    args: ["accounts"],
    kwargs: { scope: "all" },
    misfire_grace_time: 60,
    max_instances: 1,
    coalesce: true
  })),
  fetchTaskRunsSnapshot: vi.fn(async () => ({
    items: [
      {
        id: 1,
        run_id: "s-1",
        task_key: "sync_accounts",
        task_name: "账户同步",
        task_category: "account",
        trigger_source: "manual",
        status: "running",
        progress_total: 2,
        progress_completed: 1,
        progress_failed: 0,
        started_at: "2026-06-11T12:00:00+08:00",
        completed_at: null
      },
      {
        id: 2,
        run_id: "s-2",
        task_key: "email_alert",
        task_name: "邮件告警汇总",
        task_category: "notification",
        trigger_source: "scheduled",
        status: "completed",
        progress_total: 1,
        progress_completed: 1,
        progress_failed: 0,
        started_at: "2026-06-11T01:00:00+08:00",
        completed_at: "2026-06-11T01:00:03+08:00"
      }
    ],
    total: 2,
    page: 1,
    pages: 1
  })),
  fetchTaskRunDetail: vi.fn(async () => ({
    run: {
      id: 1,
      run_id: "s-1",
      task_key: "sync_accounts",
      task_name: "账户同步",
      task_category: "account",
      trigger_source: "manual",
      status: "running",
      started_at: "2026-06-11T12:00:00+08:00",
      completed_at: null,
      progress_total: 2,
      progress_completed: 1,
      progress_failed: 0
    },
    items: [
      {
        id: 11,
        run_id: "s-1",
        item_type: "instance",
        item_key: "mysql-prod",
        item_name: "mysql-prod",
        instance_id: 100,
        status: "running",
        started_at: "2026-06-11T12:00:00+08:00",
        completed_at: null,
        metrics_json: { items_synced: 10, items_created: 2, items_updated: 7, items_deleted: 1 },
        error_message: null
      }
    ]
  })),
  fetchTaskRunErrorLogs: vi.fn(async () => ({
    run: {
      id: 1,
      run_id: "s-1",
      task_key: "sync_accounts",
      task_name: "账户同步",
      task_category: "account",
      trigger_source: "manual",
      status: "running",
      started_at: "2026-06-11T12:00:00+08:00",
      completed_at: null,
      progress_total: 2,
      progress_completed: 1,
      progress_failed: 1
    },
    items: [
      {
        id: 12,
        run_id: "s-1",
        item_type: "instance",
        item_key: "oracle-failed",
        item_name: "oracle-failed",
        instance_id: 101,
        status: "failed",
        started_at: "2026-06-11T12:01:00+08:00",
        completed_at: "2026-06-11T12:02:00+08:00",
        metrics_json: {},
        error_message: "connection refused"
      }
    ],
    error_count: 1
  })),
  fetchUsersSnapshot: vi.fn(async () => ({
    list: { items: [{ id: 1, username: "admin", role: "admin", is_active: true, created_at_display: "2026-06-11" }], total: 1, page: 1, pages: 1, limit: 10 },
    stats: { total: 1, active: 1, inactive: 0, admin: 1, user: 0 }
  })),
  fetchSettingsSnapshot: vi.fn(async () => ({
    alerts: {
      smtp_ready: true,
      from_address: "ops@example.com",
      settings: {
        global_enabled: true,
        feishu_enabled: true,
        feishu_webhook_url_configured: true,
        feishu_webhook_url_masked: "https://open.feishu.cn/open-apis/bot/v2/hook/**********oken",
        recipients: ["ops@example.com"],
        database_capacity_enabled: true,
        database_capacity_percent_threshold: 30,
        database_capacity_absolute_gb_threshold: 20,
        account_sync_failure_enabled: true,
        database_sync_failure_enabled: false,
        cluster_status_enabled: true,
        privileged_account_enabled: true,
        backup_issue_enabled: true
      }
    },
    riskRules: [{ rule_key: "backup_issue", category: "备份", display_name: "备份问题", description: "最近一次备份不可用", enabled: true, severity: "high" }],
    jumpserver: {
      provider_ready: true,
      binding: { credential_id: 3, credential: { id: 3, name: "jump-api" }, base_url: "https://jump.example", org_id: "org-1", verify_ssl: true, last_sync_status: "completed", last_sync_at: "2026-06-11T01:00:00+00:00" },
      api_credentials: [{ id: 3, name: "jump-api" }]
    },
    veeam: {
      provider_ready: false,
      sources: [{ id: 9, name: "veeam-main", credential_id: 4, credential: { id: 4, name: "veeam-api" }, server_host: "10.0.0.9", server_port: 9419, api_version: "v1", is_active: true, verify_ssl: true, domains: ["corp.local"], last_sync_status: "completed", last_sync_at: "2026-06-11T02:00:00+00:00" }],
      veeam_credentials: [{ id: 4, name: "veeam-api" }]
    },
    adDomains: { configs: [{ id: 1, name: "corp", netbios_name: "CORP", ldap_port: 636, domain_controllers: ["dc01"], base_dn: "DC=corp,DC=local", credential_id: 5, credential: { id: 5, name: "ldap-bind" }, use_ssl: true, verify_ssl: true, is_enabled: true, last_sync_status: "completed", last_sync_at: "2026-06-11T03:00:00+00:00", last_sync_metrics: { ad_principals_total: 12, ad_users_total: 10, ad_groups_total: 2, total: 8, normal: 6, disabled: 1, orphaned: 1, updated: 3 } }], credentials: [{ id: 5, name: "ldap-bind" }] }
  })),
  fetchCredentialsSnapshot: vi.fn(async () => ({
    items: [
      { id: 1, name: "prod-db", credential_type: "database", db_type: "mysql", username: "root", is_active: true, instance_count: 2 },
      { id: 2, name: "ldap-bind", credential_type: "ldap", db_type: null, username: "bind", is_active: true, instance_count: 0 }
    ],
    total: 2,
    page: 1,
    pages: 1,
    limit: 20
  })),
  fetchTagsSnapshot: vi.fn(async () => ({
    list: { items: [{ id: 1, name: "prod", display_name: "生产", category: "env", is_active: true, instance_count: 3 }], total: 1, page: 1, pages: 1, limit: 20, stats: { total: 1, active: 1, inactive: 0, category_count: 1 } },
    categories: ["env"]
  })),
  fetchTagBulkOptions: vi.fn(async () => ({
    instances: [{ id: 1, name: "mysql-prod", db_type: "mysql", host: "10.0.0.1", port: 3306 }],
    tags: [{ id: 1, name: "prod", display_name: "生产", category: "env", is_active: true }],
    categoryNames: ["env"]
  })),
  fetchPartitionsSnapshot: vi.fn(async () => ({
    status: { data: { status: "healthy", total_partitions: 3, total_size: "3 MB", total_records: 30, missing_partitions: [], partitions: [{ name: "p202605", date: "2026-05-01", status: "past", size: "1 MB", record_count: 10 }, { name: "p202606", date: "2026-06-01", status: "current", size: "1 MB", record_count: 12 }, { name: "p202607", date: "2026-07-01", status: "future", size: "1 MB", record_count: 8 }] }, timestamp: "2026-06-11T00:00:00+08:00" },
    list: {
      items: [
        { name: "p202605", date: "2026-05-01", table: "account_stats", table_type: "stats", size: "1 MB", record_count: 10, status: "past" },
        { name: "p202606", date: "2026-06-01", table: "account_stats", table_type: "stats", size: "1 MB", record_count: 12, status: "current" },
        { name: "p202607", date: "2026-07-01", table: "account_stats", table_type: "stats", size: "1 MB", record_count: 8, status: "future" }
      ],
      total: 3,
      page: 1,
      pages: 1,
      limit: 20
    },
    coreMetrics: {
      labels: ["2026-06-11"],
      datasets: [
        { label: "实例数总量", data: [77] },
        { label: "实例日统计数量", data: [3] },
        { label: "数据库数总量", data: [130] },
        { label: "数据库日统计数量", data: [9] }
      ],
      dataPointCount: 1,
      timeRange: "最近7天的核心指标统计",
      yAxisLabel: "数量",
      chartTitle: "日核心指标趋势",
      periodType: "daily"
    }
  }))
}));

function renderWithQueryClient(element: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  return render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>);
}

async function expectTextPresent(text: string) {
  await waitFor(() => {
    expect(screen.getAllByText(text).length).toBeGreaterThan(0);
  });
}

async function switchTab(name: string | RegExp) {
  const tab = screen.getByRole("tab", { name });
  fireEvent.mouseDown(tab, { button: 0, ctrlKey: false });
  fireEvent.click(tab);
  await waitFor(() => expect(tab).toHaveAttribute("aria-selected", "true"));
}

async function chooseSelectOption(scope: ReturnType<typeof within>, label: string, optionName: string) {
  fireEvent.click(scope.getByRole("combobox", { name: label }));
  fireEvent.click(await screen.findByRole("option", { name: optionName }));
}

describe("Console pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const cases: Array<[string, ReactElement, string[]]> = [
    ["群集管理", <ClustersPage />, ["sql-ag"]],
    ["账户分类", <AccountClassificationsPage />, ["DBA", "root rule"]],
    ["分类统计", <ClassificationStatisticsPage />, ["DBA", "分类趋势（去重账号数）"]],
    ["定时任务", <SchedulerPage />, ["同步任务", "运行中"]],
    ["会话中心", <SyncSessionsPage />, ["s-1", "running"]],
    ["用户管理", <UsersPage />, ["admin", "用户列表"]],
    ["系统设置", <SettingsPage />, ["设置模块", "Alerts", "邮件告警"]],
    ["凭据管理", <CredentialsPage />, ["prod-db", "root"]],
    ["标签管理", <TagsPage />, ["生产", "env"]],
    ["分区管理", <PartitionsPage />, ["2026年6月", "当前"]]
  ];

  it.each(cases)("renders %s from read-only APIs", async (heading, element, expectedTexts) => {
    renderWithQueryClient(element);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    });

    for (const text of expectedTexts) {
      await expectTextPresent(text);
    }
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders credential management with legacy filters, fields, and actions", async () => {
    renderWithQueryClient(<CredentialsPage />);

    await screen.findByRole("heading", { name: "凭据管理" });

    for (const text of ["搜索", "凭据类型", "数据库类型", "状态", "凭据", "类型", "绑定实例", "创建时间", "操作"]) {
      await expectTextPresent(text);
    }

    expect(screen.getByRole("button", { name: "添加凭据" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "编辑凭据 prod-db" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "删除凭据 prod-db" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "查看凭据 prod-db" })).not.toBeInTheDocument();
    expect(screen.queryByText("凭据指标")).not.toBeInTheDocument();
    expect(screen.queryByText("凭据总数")).not.toBeInTheDocument();
    expect(screen.queryByText("每页 20 条")).not.toBeInTheDocument();
  });

  it("runs credential create, update, and delete through React dialogs", async () => {
    renderWithQueryClient(<CredentialsPage />);

    await screen.findByRole("heading", { name: "凭据管理" });
    fireEvent.click(await screen.findByRole("button", { name: "添加凭据" }));
    const createDialog = await screen.findByRole("dialog", { name: "新建凭据" });
    fireEvent.change(within(createDialog).getByLabelText("凭据名称"), { target: { value: "ops-db" } });
    fireEvent.change(within(createDialog).getByLabelText("用户名"), { target: { value: "app_user" } });
    fireEvent.change(within(createDialog).getByLabelText("密码"), { target: { value: "Strong123" } });
    fireEvent.change(within(createDialog).getByLabelText("描述"), { target: { value: "ops" } });
    fireEvent.click(within(createDialog).getByRole("button", { name: "保存凭据" }));

    await waitFor(() => {
      expect(actionMocks.createCredential).toHaveBeenCalledWith({
        name: "ops-db",
        credential_type: "database",
        db_type: "mysql",
        username: "app_user",
        password: "Strong123",
        description: "ops",
        is_active: true
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "编辑凭据 prod-db" }));
    const editDialog = await screen.findByRole("dialog", { name: "编辑凭据 prod-db" });
    fireEvent.change(within(editDialog).getByLabelText("凭据名称"), { target: { value: "prod-db-updated" } });
    fireEvent.click(within(editDialog).getByRole("button", { name: "保存凭据" }));

    await waitFor(() => {
      expect(actionMocks.updateCredential).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          name: "prod-db-updated",
          credential_type: "database",
          db_type: "mysql",
          username: "root",
          is_active: true
        })
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "删除凭据 prod-db" }));
    expect(await screen.findByRole("alertdialog", { name: "确认删除凭据 prod-db" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认删除凭据" }));

    await waitFor(() => {
      expect(actionMocks.deleteCredential).toHaveBeenCalledWith(1);
    });
  });

  it("hides database type in credential forms when the credential is not a database credential", async () => {
    renderWithQueryClient(<CredentialsPage />);

    await screen.findByRole("heading", { name: "凭据管理" });
    fireEvent.click(await screen.findByRole("button", { name: "编辑凭据 ldap-bind" }));
    const editDialog = await screen.findByRole("dialog", { name: "编辑凭据 ldap-bind" });
    expect(within(editDialog).getByRole("combobox", { name: "凭据类型" })).toHaveTextContent("LDAP");
    expect(within(editDialog).queryByRole("combobox", { name: "数据库类型" })).not.toBeInTheDocument();
    fireEvent.click(within(editDialog).getByRole("button", { name: "取消" }));

    fireEvent.click(screen.getByRole("button", { name: "添加凭据" }));
    const createDialog = await screen.findByRole("dialog", { name: "新建凭据" });
    await chooseSelectOption(within(createDialog), "凭据类型", "LDAP");
    expect(within(createDialog).queryByRole("combobox", { name: "数据库类型" })).not.toBeInTheDocument();
  });

  it("keeps legacy credential type labels and password visibility control", async () => {
    renderWithQueryClient(<CredentialsPage />);

    await screen.findByRole("heading", { name: "凭据管理" });
    fireEvent.click(await screen.findByRole("button", { name: "添加凭据" }));
    const createDialog = await screen.findByRole("dialog", { name: "新建凭据" });

    fireEvent.click(within(createDialog).getByRole("combobox", { name: "凭据类型" }));
    for (const option of ["数据库", "API", "Veeam", "LDAP", "SSH"]) {
      expect(await screen.findByRole("option", { name: option })).toBeInTheDocument();
    }
    fireEvent.click(await screen.findByRole("option", { name: "Veeam" }));
    expect(within(createDialog).queryByRole("combobox", { name: "数据库类型" })).not.toBeInTheDocument();

    const passwordInput = within(createDialog).getByLabelText("密码");
    expect(passwordInput).toHaveAttribute("type", "password");
    fireEvent.click(within(createDialog).getByRole("button", { name: "显示密码" }));
    expect(passwordInput).toHaveAttribute("type", "text");
    fireEvent.click(within(createDialog).getByRole("button", { name: "隐藏密码" }));
    expect(passwordInput).toHaveAttribute("type", "password");
  });

  it("renders tag management with legacy stats, filters, fields, and actions", async () => {
    renderWithQueryClient(<TagsPage />);

    await screen.findByRole("heading", { name: "标签管理" });

    for (const text of ["全部标签", "启用率", "停用率", "标签分类", "搜索", "状态", "标签", "分类", "关联", "操作"]) {
      await expectTextPresent(text);
    }

    for (const text of ["均值/分类 1", "启用 1", "停用 0", "启用/分类 1", "100.0%", "0.0%"]) {
      await expectTextPresent(text);
    }
    expect(screen.getByRole("button", { name: "添加标签" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "批量分配" })).toHaveAttribute("href", "/tags/bulk/assign");
    expect(screen.getByRole("button", { name: "编辑标签 生产" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "删除标签 生产" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "查看标签 生产" })).not.toBeInTheDocument();
    expect(screen.queryByText("分类: env")).not.toBeInTheDocument();
  });

  it("runs tag create, update, and delete through React dialogs", async () => {
    renderWithQueryClient(<TagsPage />);

    await screen.findByRole("heading", { name: "标签管理" });
    fireEvent.click(await screen.findByRole("button", { name: "添加标签" }));
    const createDialog = await screen.findByRole("dialog", { name: "新建标签" });
    fireEvent.change(within(createDialog).getByLabelText("标签编码"), { target: { value: "staging" } });
    fireEvent.change(within(createDialog).getByLabelText("展示名称"), { target: { value: "预发" } });
    fireEvent.click(within(createDialog).getByRole("combobox", { name: "分类" }));
    fireEvent.click(await screen.findByRole("option", { name: "env" }));
    fireEvent.click(within(createDialog).getByRole("button", { name: "保存标签" }));

    await waitFor(() => {
      expect(actionMocks.createTag).toHaveBeenCalledWith({
        name: "staging",
        display_name: "预发",
        category: "env",
        is_active: true
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "编辑标签 生产" }));
    const editDialog = await screen.findByRole("dialog", { name: "编辑标签 生产" });
    fireEvent.change(within(editDialog).getByLabelText("展示名称"), { target: { value: "生产环境" } });
    fireEvent.click(within(editDialog).getByRole("button", { name: "保存标签" }));

    await waitFor(() => {
      expect(actionMocks.updateTag).toHaveBeenCalledWith(1, {
        name: "prod",
        display_name: "生产环境",
        category: "env",
        is_active: true
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "删除标签 生产" }));
    expect(await screen.findByRole("alertdialog", { name: "确认删除标签 生产" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认删除标签" }));

    await waitFor(() => {
      expect(actionMocks.deleteTag).toHaveBeenCalledWith(1);
    });
  });

  it("renders user management with legacy filters, fields, and actions", async () => {
    renderWithQueryClient(<UsersPage />);

    await screen.findByRole("heading", { name: "用户管理" });

    for (const text of ["搜索", "角色", "状态", "ID", "用户", "创建时间", "操作", "#1", "管理员", "启用"]) {
      await expectTextPresent(text);
    }

    expect(screen.getByRole("button", { name: "新建用户" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "编辑用户 admin" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "删除用户 admin" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "查看用户 admin" })).not.toBeInTheDocument();
    expect(screen.queryByText("用户指标")).not.toBeInTheDocument();
    expect(screen.queryByText("用户总数")).not.toBeInTheDocument();
    expect(screen.queryByText("每页 10 条")).not.toBeInTheDocument();
  });

  it("matches legacy read-only management actions for non-admin users", async () => {
    renderWithQueryClient(<AccountClassificationsPage currentUser={viewerUser} />);

    await screen.findByRole("heading", { name: "账户分类" });
    expect(await screen.findByRole("button", { name: "查看规则 root rule" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "自动分类" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "新建分类" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "新建规则" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "编辑分类 DBA" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "编辑规则 root rule" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "删除规则 root rule" })).not.toBeInTheDocument();

    cleanup();
    renderWithQueryClient(<UsersPage currentUser={viewerUser} />);

    await screen.findByRole("heading", { name: "用户管理" });
    expect(screen.queryByRole("button", { name: "查看用户 admin" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "新建用户" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "编辑用户 admin" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "删除用户 admin" })).not.toBeInTheDocument();

    cleanup();
    renderWithQueryClient(<CredentialsPage currentUser={viewerUser} />);

    await screen.findByRole("heading", { name: "凭据管理" });
    expect(screen.queryByRole("button", { name: "查看凭据 prod-db" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "添加凭据" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "编辑凭据 prod-db" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "删除凭据 prod-db" })).not.toBeInTheDocument();

    cleanup();
    renderWithQueryClient(<TagsPage currentUser={viewerUser} />);

    await screen.findByRole("heading", { name: "标签管理" });
    expect(screen.queryByRole("button", { name: "查看标签 生产" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "添加标签" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "批量分配" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "编辑标签 生产" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "删除标签 生产" })).not.toBeInTheDocument();
  });

  it("prevents the current administrator from deleting their own user row", async () => {
    renderWithQueryClient(<UsersPage currentUser={adminUser} />);

    await screen.findByRole("heading", { name: "用户管理" });
    expect(await screen.findByRole("button", { name: "编辑用户 admin" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "不能删除当前登录用户" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "删除用户 admin" })).not.toBeInTheDocument();
  });

  it("runs user create, update, and delete through React dialogs", async () => {
    renderWithQueryClient(<UsersPage />);

    await screen.findByRole("heading", { name: "用户管理" });
    fireEvent.click(await screen.findByRole("button", { name: "新建用户" }));
    const createDialog = await screen.findByRole("dialog", { name: "新建用户" });
    fireEvent.change(within(createDialog).getByLabelText("用户名"), { target: { value: "ops_user" } });
    fireEvent.change(within(createDialog).getByLabelText("初始密码"), { target: { value: "Aa123456" } });
    fireEvent.click(within(createDialog).getByRole("button", { name: "保存用户" }));

    await waitFor(() => {
      expect(actionMocks.createUser).toHaveBeenCalledWith({
        username: "ops_user",
        role: "user",
        password: "Aa123456",
        is_active: true
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "编辑用户 admin" }));
    const editDialog = await screen.findByRole("dialog", { name: "编辑用户 admin" });
    await chooseSelectOption(within(editDialog), "角色", "普通用户");
    fireEvent.click(within(editDialog).getByRole("button", { name: "保存用户" }));

    await waitFor(() => {
      expect(actionMocks.updateUser).toHaveBeenCalledWith(1, {
        username: "admin",
        role: "user",
        is_active: true
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "删除用户 admin" }));
    expect(await screen.findByRole("alertdialog", { name: "确认删除用户 admin" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认删除用户" }));

    await waitFor(() => {
      expect(actionMocks.deleteUser).toHaveBeenCalledWith(1);
    });
  });

  it("renders scheduler cards with legacy groups, fields, and actions", async () => {
    renderWithQueryClient(<SchedulerPage />);

    await screen.findByRole("heading", { name: "定时任务" });
    await expectTextPresent("同步任务");
    expect(screen.queryByText("定时任务指标")).not.toBeInTheDocument();
    expect(screen.queryByText("任务总数")).not.toBeInTheDocument();
    expect(screen.queryByText("运行任务")).not.toBeInTheDocument();
    expect(screen.queryByText("内置任务")).not.toBeInTheDocument();
    expect(screen.queryByText("可配置")).not.toBeInTheDocument();

    for (const text of ["重新初始化任务", "运行中的任务", "已暂停的任务", "同步任务", "归档任务", "下次运行", "上次运行", "任务 ID"]) {
      await expectTextPresent(text);
    }
    expect(screen.queryByText("触发器参数")).not.toBeInTheDocument();

    expect(screen.getByRole("button", { name: "暂停任务 同步任务" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "恢复任务 归档任务" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "立即执行 同步任务" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "编辑任务 同步任务" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "删除任务 同步任务" })).not.toBeInTheDocument();
  });

  it("renders sync sessions with legacy filters, fields, progress, and actions", async () => {
    renderWithQueryClient(<SyncSessionsPage />);

    await screen.findByRole("heading", { name: "会话中心" });

    for (const text of ["来源", "分类", "状态", "运行ID", "进度", "任务", "开始时间", "耗时", "操作", "50%", "手动", "账户", "告警"]) {
      await expectTextPresent(text);
    }

    expect(screen.getByRole("button", { name: "查看详情 s-1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "取消任务 s-1" })).toBeInTheDocument();
    expect(screen.queryByRole("searchbox", { name: "搜索" })).not.toBeInTheDocument();
    expect(screen.queryByText("notification")).not.toBeInTheDocument();
    expect(screen.queryByText("会话指标")).not.toBeInTheDocument();
    expect(screen.queryByText("会话总数")).not.toBeInTheDocument();
    expect(screen.queryByText("最近同步会话首屏列表。")).not.toBeInTheDocument();
  });

  it("filters sync sessions with the backend notification category", async () => {
    renderWithQueryClient(<SyncSessionsPage />);

    await screen.findByRole("heading", { name: "会话中心" });
    fireEvent.click(await screen.findByRole("combobox", { name: "分类" }));
    fireEvent.click(await screen.findByRole("option", { name: "告警" }));

    await waitFor(() => {
      expect(fetchTaskRunsSnapshot).toHaveBeenLastCalledWith(
        expect.objectContaining({ taskCategory: "notification" })
      );
    });
  });

  it("opens sync session detail in a React dialog", async () => {
    renderWithQueryClient(<SyncSessionsPage />);

    await screen.findByRole("button", { name: "查看详情 s-1" });
    fireEvent.click(screen.getByRole("button", { name: "查看详情 s-1" }));

    expect(await screen.findByRole("dialog", { name: "会话详情 s-1" })).toBeInTheDocument();
    expect(await screen.findByText("mysql-prod")).toBeInTheDocument();
    expect(await screen.findByText("oracle-failed")).toBeInTheDocument();
    expect(await screen.findByText("connection refused")).toBeInTheDocument();
    expect(screen.queryByText("同步详情")).not.toBeInTheDocument();
  });

  it("renders clusters with legacy filters, fields, db type panels, and actions", async () => {
    renderWithQueryClient(<ClustersPage />);

    await screen.findByRole("heading", { name: "群集管理" });
    expect(screen.queryByText("Cluster topology")).not.toBeInTheDocument();

    for (const text of ["添加群集", "搜索", "状态", "SQL Server", "MySQL"]) {
      await expectTextPresent(text);
    }
    for (const header of ["群集", "域名", "状态", "绑定实例", "AG", "最近 AG 同步", "数据库同步状态", "操作"]) {
      expect(screen.getAllByRole("columnheader", { name: header }).length).toBeGreaterThan(0);
    }

    expect(screen.getByRole("button", { name: "管理群集 sql-ag" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "AG账户 sql-ag" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "查看AG状态 sql-ag" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "管理群集 mysql-repl" })).not.toBeInTheDocument();

    await switchTab(/MySQL/);

    for (const header of ["群集", "拓扑", "状态", "绑定实例", "主从状态", "操作"]) {
      expect(screen.getAllByRole("columnheader", { name: header }).length).toBeGreaterThan(0);
    }
    expect(screen.queryByRole("button", { name: "管理群集 sql-ag" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "管理群集 mysql-repl" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "主从状态 mysql-repl" })).toBeInTheDocument();
  });

  it("runs cluster create and update forms through v1 APIs", async () => {
    renderWithQueryClient(<ClustersPage />);

    await screen.findByRole("heading", { name: "群集管理" });
    fireEvent.click(await screen.findByRole("button", { name: "添加 SQL Server 群集" }));
    const sqlCreateDialog = await screen.findByRole("dialog", { name: "新建 SQL Server 群集" });
    fireEvent.change(within(sqlCreateDialog).getByLabelText("群集名称"), { target: { value: "sql-new" } });
    fireEvent.change(within(sqlCreateDialog).getByLabelText("群集域名"), { target: { value: "corp.local" } });
    fireEvent.change(within(sqlCreateDialog).getByLabelText("描述"), { target: { value: "primary ag" } });
    fireEvent.click(within(sqlCreateDialog).getByRole("button", { name: "保存群集" }));

    await waitFor(() => {
      expect(actionMocks.createSqlServerCluster).toHaveBeenCalledWith({
        name: "sql-new",
        domain_name: "corp.local",
        description: "primary ag",
        is_enabled: true
      });
    });

    fireEvent.click(await screen.findByRole("button", { name: "添加 MySQL 群集" }));
    const mysqlCreateDialog = await screen.findByRole("dialog", { name: "新建 MySQL 群集" });
    fireEvent.change(within(mysqlCreateDialog).getByLabelText("群集名称"), { target: { value: "mysql-new" } });
    fireEvent.change(within(mysqlCreateDialog).getByLabelText("描述"), { target: { value: "replica group" } });
    fireEvent.click(within(mysqlCreateDialog).getByRole("button", { name: "保存群集" }));

    await waitFor(() => {
      expect(actionMocks.createMySqlCluster).toHaveBeenCalledWith({
        name: "mysql-new",
        description: "replica group",
        is_enabled: true
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "管理群集 sql-ag" }));
    const sqlEditDialog = await screen.findByRole("dialog", { name: "编辑 SQL Server 群集 sql-ag" });
    fireEvent.change(within(sqlEditDialog).getByLabelText("群集名称"), { target: { value: "sql-ag-updated" } });
    fireEvent.click(within(sqlEditDialog).getByRole("button", { name: "保存群集" }));

    await waitFor(() => {
      expect(actionMocks.updateSqlServerCluster).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ name: "sql-ag-updated", domain_name: "corp.local", is_enabled: true })
      );
    });

    await switchTab(/MySQL/);

    fireEvent.click(screen.getByRole("button", { name: "管理群集 mysql-repl" }));
    const mysqlEditDialog = await screen.findByRole("dialog", { name: "编辑 MySQL 群集 mysql-repl" });
    fireEvent.change(within(mysqlEditDialog).getByLabelText("群集名称"), { target: { value: "mysql-repl-updated" } });
    fireEvent.click(within(mysqlEditDialog).getByRole("button", { name: "保存群集" }));

    await waitFor(() => {
      expect(actionMocks.updateMySqlCluster).toHaveBeenCalledWith(
        2,
        expect.objectContaining({ name: "mysql-repl-updated", is_enabled: true })
      );
    });
  });

  it("opens cluster details and runs cluster sync actions through v1 APIs", async () => {
    renderWithQueryClient(<ClustersPage />);

    await screen.findByRole("heading", { name: "群集管理" });
    fireEvent.click(await screen.findByRole("button", { name: "查看AG状态 sql-ag" }));
    const sqlDetailDialog = await screen.findByRole("dialog", { name: "SQL Server 群集详情 sql-ag" });
    expect(await within(sqlDetailDialog).findByText("sql-node-1")).toBeInTheDocument();
    expect((await within(sqlDetailDialog).findAllByText("ag-sales")).length).toBeGreaterThan(0);
    expect(await within(sqlDetailDialog).findByText("副本状态")).toBeInTheDocument();
    expect(await within(sqlDetailDialog).findByText("数据库状态")).toBeInTheDocument();
    expect(await within(sqlDetailDialog).findByText("PRIMARY")).toBeInTheDocument();
    expect(await within(sqlDetailDialog).findByText("SYNCHRONIZED")).toBeInTheDocument();
    fireEvent.click(within(sqlDetailDialog).getByRole("button", { name: "同步AG信息" }));
    fireEvent.click(within(sqlDetailDialog).getByRole("button", { name: "同步群集状态" }));
    fireEvent.click(within(sqlDetailDialog).getByRole("button", { name: "同步AG账户" }));

    await waitFor(() => {
      expect(actionMocks.syncSqlServerAvailabilityGroups).toHaveBeenCalledWith(1, "master");
      expect(actionMocks.syncSqlServerClusterStatus).toHaveBeenCalledWith(1);
      expect(actionMocks.syncSqlServerAgAccounts).toHaveBeenCalledWith(1);
    });
    fireEvent.click(within(sqlDetailDialog).getByRole("button", { name: "关闭详情" }));

    fireEvent.click(screen.getByRole("button", { name: "AG账户 sql-ag" }));
    const agAccountsDialog = await screen.findByRole("dialog", { name: "AG 账户 sql-ag" });
    for (const text of ["AG 总数", "Contained", "已配凭据", "启用采集"]) {
      expect(await within(agAccountsDialog).findByText(text)).toBeInTheDocument();
    }
    expect((await within(agAccountsDialog).findAllByText("ag-sales")).length).toBeGreaterThan(0);
    await within(agAccountsDialog).findByText("WZ\\admin-zmian");
    expect(within(agAccountsDialog).getByText("AGDB10 · 10.10.10.177")).toBeInTheDocument();
    expect(within(agAccountsDialog).getByText("可用")).toBeInTheDocument();
    expect(within(agAccountsDialog).getByText("是")).toBeInTheDocument();
    expect(within(agAccountsDialog).getByText("未匹配AD")).toBeInTheDocument();
    expect(within(agAccountsDialog).getByText("分类 分类")).toBeInTheDocument();
    expect(within(agAccountsDialog).getByText("标签 生产环境 / 温州 / 主从")).toBeInTheDocument();
    expect(within(agAccountsDialog).getByText("最近变更 2026-05-21 09:04:43")).toBeInTheDocument();
    expect(within(agAccountsDialog).queryByText("暂无 AG 账户，请先同步 AG 账户")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(listApiMocks.fetchAccountLedgers).toHaveBeenCalledWith(
        expect.objectContaining({ ownerType: "sqlserver_ag", ownerId: 21, includeRoles: true, limit: 100 })
      );
    });
    expect(actionMocks.syncSqlServerAgAccounts).toHaveBeenCalledTimes(1);
    fireEvent.click(within(agAccountsDialog).getByRole("button", { name: "同步 AG 账户" }));
    await waitFor(() => {
      expect(actionMocks.syncSqlServerAgAccounts).toHaveBeenCalledTimes(2);
    });
    fireEvent.click(within(agAccountsDialog).getAllByRole("button", { name: "关闭" })[0]);

    await switchTab(/MySQL/);

    fireEvent.click(screen.getByRole("button", { name: "主从状态 mysql-repl" }));
    const mysqlDetailDialog = await screen.findByRole("dialog", { name: "MySQL 群集详情 mysql-repl" });
    expect(await within(mysqlDetailDialog).findByText("mysql-primary")).toBeInTheDocument();
    fireEvent.click(within(mysqlDetailDialog).getByRole("button", { name: "同步主从拓扑" }));

    await waitFor(() => {
      expect(actionMocks.syncMySqlClusterTopology).toHaveBeenCalledWith(2);
    });
  });

  it("runs cluster binding and SQL Server AG configuration through existing v1 APIs", async () => {
    renderWithQueryClient(<ClustersPage />);

    await screen.findByRole("heading", { name: "群集管理" });
    fireEvent.click(await screen.findByRole("button", { name: "查看AG状态 sql-ag" }));
    const sqlDetailDialog = await screen.findByRole("dialog", { name: "SQL Server 群集详情 sql-ag" });
    expect(within(sqlDetailDialog).queryByRole("button", { name: "编辑实例绑定" })).not.toBeInTheDocument();
    expect(within(sqlDetailDialog).queryByRole("button", { name: "新建AG配置" })).not.toBeInTheDocument();
    fireEvent.click(within(sqlDetailDialog).getByRole("button", { name: "关闭详情" }));

    fireEvent.click(screen.getByRole("button", { name: "绑定实例 sql-ag" }));
    const bindingDialog = await screen.findByRole("dialog", { name: "编辑 SQL Server 实例绑定 sql-ag" });
    expect(screen.queryByRole("region", { name: "编辑 SQL Server 实例绑定 sql-ag" })).not.toBeInTheDocument();
    expect(await within(bindingDialog).findByText("sql-node-2")).toBeInTheDocument();
    fireEvent.click(within(bindingDialog).getByRole("checkbox", { name: /sql-node-2/ }));
    fireEvent.click(within(bindingDialog).getByRole("button", { name: "保存绑定" }));

    await waitFor(() => {
      expect(actionMocks.replaceSqlServerClusterInstances).toHaveBeenCalledWith(1, [11, 13]);
    });

    fireEvent.click(screen.getByRole("button", { name: "AG配置 sql-ag" }));
    const agDialog = await screen.findByRole("dialog", { name: "SQL Server AG 配置 sql-ag" });
    expect(screen.queryByRole("region", { name: "SQL Server AG 配置 sql-ag" })).not.toBeInTheDocument();
    expect(await within(agDialog).findByText("ag-sales")).toBeInTheDocument();

    fireEvent.click(within(agDialog).getByRole("button", { name: "新建AG配置" }));
    fireEvent.change(within(agDialog).getByLabelText("AG 名称"), { target: { value: "ag-new" } });
    fireEvent.change(within(agDialog).getByLabelText("监听器名称"), { target: { value: "ag-new-listener" } });
    fireEvent.change(within(agDialog).getByLabelText("监听器地址"), { target: { value: "ag-new.example" } });
    fireEvent.change(within(agDialog).getByLabelText("监听器端口"), { target: { value: "1433" } });
    fireEvent.change(within(agDialog).getByLabelText("连接数据库"), { target: { value: "master" } });
    fireEvent.change(within(agDialog).getByLabelText("账户凭据ID"), { target: { value: "9" } });
    fireEvent.click(within(agDialog).getByRole("button", { name: "保存AG配置" }));

    await waitFor(() => {
      expect(actionMocks.createSqlServerAvailabilityGroup).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          name: "ag-new",
          listener_name: "ag-new-listener",
          listener_host: "ag-new.example",
          listener_port: 1433,
          connection_database: "master",
          account_credential_id: 9,
          contained_enabled: false,
          is_enabled: true
        })
      );
    });

    fireEvent.click(within(agDialog).getByRole("button", { name: "编辑AG ag-sales" }));
    expect(within(agDialog).getByRole("heading", { name: "编辑 SQL Server AG 配置 ag-sales" })).toBeInTheDocument();
    fireEvent.change(within(agDialog).getByLabelText("监听器地址"), { target: { value: "ag-edit.example" } });
    fireEvent.click(within(agDialog).getByRole("button", { name: "保存AG配置" }));

    await waitFor(() => {
      expect(actionMocks.updateSqlServerAvailabilityGroup).toHaveBeenCalledWith(
        1,
        21,
        expect.objectContaining({ name: "ag-sales", listener_host: "ag-edit.example" })
      );
    });

    fireEvent.click(within(agDialog).getByRole("button", { name: "查看AG看板 ag-sales" }));
    expect(await within(agDialog).findByRole("heading", { name: "SQL Server AG 看板 ag-sales" })).toBeInTheDocument();
    expect((await within(agDialog).findAllByText("sql-node-1")).length).toBeGreaterThan(0);
    expect(await within(agDialog).findByText("sales")).toBeInTheDocument();
  });

  it("uses instance_id rather than binding id when editing MySQL cluster bindings", async () => {
    vi.mocked(fetchMySqlClusterDetail).mockResolvedValueOnce({
      cluster: { id: 2, name: "mysql-repl", description: "MySQL replication 群集", is_enabled: true },
      instances: [
        { id: 900, instance_id: 12, name: "mysql-primary", host: "10.0.0.21", role: "primary" },
        { id: 901, instance_id: 14, name: "mysql-replica", host: "10.0.0.24", role: "replica" }
      ]
    });
    vi.mocked(fetchClusterInstanceOptions).mockResolvedValueOnce([
      { id: 12, name: "mysql-primary", host: "10.0.0.21", db_type: "mysql" },
      { id: 14, name: "mysql-replica", host: "10.0.0.24", db_type: "mysql" },
      { id: 900, name: "wrong-selected-instance", host: "10.0.9.0", db_type: "mysql" }
    ]);
    renderWithQueryClient(<ClustersPage />);

    await screen.findByRole("heading", { name: "群集管理" });
    await screen.findByRole("tab", { name: /MySQL/ });
    await switchTab(/MySQL/);
    fireEvent.click(screen.getByRole("button", { name: "绑定实例 mysql-repl" }));
    const bindingDialog = await screen.findByRole("dialog", { name: "编辑 MySQL 实例绑定 mysql-repl" });

    expect(await within(bindingDialog).findByRole("checkbox", { name: /mysql-primary/ })).toBeChecked();
    expect(within(bindingDialog).getByRole("checkbox", { name: /mysql-replica/ })).toBeChecked();
    expect(within(bindingDialog).getByRole("checkbox", { name: /wrong-selected-instance/ })).not.toBeChecked();

    fireEvent.click(within(bindingDialog).getByRole("checkbox", { name: /mysql-primary/ }));
    fireEvent.click(within(bindingDialog).getByRole("button", { name: "保存绑定" }));

    await waitFor(() => {
      expect(actionMocks.replaceMySqlClusterInstances).toHaveBeenCalledWith(2, [14]);
    });
  });

  it("renders account classifications with legacy panels, rule groups, and actions", async () => {
    renderWithQueryClient(<AccountClassificationsPage />);

    await screen.findByRole("heading", { name: "账户分类" });

    for (const text of ["自动分类", "账户分类", "规则管理", "新建分类", "新建规则", "#dba", "系统", "2级", "MYSQL 规则", "root rule", "8"]) {
      await expectTextPresent(text);
    }

    expect(screen.getByRole("button", { name: "编辑分类 DBA" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "查看规则 root rule" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "编辑规则 root rule" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "删除规则 root rule" })).toBeInTheDocument();
    expect(screen.queryByText("分类展示名、系统标记、风险等级和规则数量。")).not.toBeInTheDocument();
    expect(screen.queryByText("按数据库类型汇总后的分类规则。")).not.toBeInTheDocument();
    expect(screen.queryByText("共 2 条")).not.toBeInTheDocument();
  });

  it("renders classification statistics with legacy filters, rule list, and chart panels", async () => {
    renderWithQueryClient(<ClassificationStatisticsPage />);

    await screen.findByRole("heading", { name: "分类统计" });

    for (const text of [
      "账户分类",
      "统计周期",
      "日统计",
      "数据库类型",
      "实例/AG",
      "规则列表",
      "最新周期",
      "搜索规则名/备注",
      "启用",
      "选择分类后加载规则列表与规则趋势",
      "分类趋势（去重账号数）",
      "全部分类",
      "DBA",
      "App",
      "覆盖 1/1 天",
      "规则贡献（当前周期）",
      "说明：规则之间允许重叠，“各规则之和”不等于分类去重总数。"
    ]) {
      await expectTextPresent(text);
    }

    fireEvent.click(screen.getByRole("combobox", { name: "统计周期" }));
    for (const option of ["周统计", "月统计", "季统计", "年统计（即将支持）"]) {
      expect(await screen.findByRole("option", { name: option })).toBeInTheDocument();
    }
    expect(await screen.findByRole("option", { name: "年统计（即将支持）" })).toHaveAttribute("data-disabled");
    for (const text of ["分类统计指标", "统计分类", "趋势序列", "周期数量", "Top 命中", "分类排行", "分类趋势面积图", "选择分类后展示当前周期 Top 规则贡献。"] ) {
      expect(screen.queryByText(text)).not.toBeInTheDocument();
    }
    expect(screen.queryByText("DBA", { selector: ".mb-2" })).not.toBeInTheDocument();
  });

  it("loads classification rule list, contributions, and rule trend after selecting a classification", async () => {
    renderWithQueryClient(<ClassificationStatisticsPage />);

    await screen.findByRole("heading", { name: "分类统计" });
    fireEvent.click(await screen.findByRole("combobox", { name: "账户分类" }));
    fireEvent.click(await screen.findByRole("option", { name: "DBA" }));
    fireEvent.click(screen.getAllByRole("button", { name: "应用筛选" })[0]);

    await waitFor(() => {
      expect(fetchClassificationStatisticsSnapshot).toHaveBeenLastCalledWith(
        expect.objectContaining({ classificationId: "1", periodType: "daily", periods: 7 })
      );
    });
    await expectTextPresent("root rule");
    await expectTextPresent("贡献 8");

    fireEvent.click(screen.getByRole("button", { name: "查看趋势" }));

    await waitFor(() => {
      expect(fetchClassificationStatisticsSnapshot).toHaveBeenLastCalledWith(expect.objectContaining({ ruleId: "9" }));
    });
    await expectTextPresent("规则趋势（命中账号数）");
  });

  it("loads classification account scope options after selecting a database type", async () => {
    renderWithQueryClient(<ClassificationStatisticsPage />);

    await screen.findByRole("heading", { name: "分类统计" });
    const databaseTypeSelect = await screen.findByRole("combobox", { name: "数据库类型" });
    vi.mocked(fetchAccountScopeOptions).mockClear();
    fireEvent.click(databaseTypeSelect);
    fireEvent.click(await screen.findByRole("option", { name: "MySQL" }));

    await waitFor(() => {
      expect(fetchAccountScopeOptions).toHaveBeenCalledWith("mysql");
    });

    fireEvent.click(screen.getByRole("combobox", { name: "实例/AG" }));
    fireEvent.click(await screen.findByRole("option", { name: "mysql-prod (MYSQL)" }));
    fireEvent.click(screen.getAllByRole("button", { name: "应用筛选" })[0]);

    await waitFor(() => {
      expect(fetchClassificationStatisticsSnapshot).toHaveBeenLastCalledWith(
        expect.objectContaining({ accountScope: "instance:11", dbType: "mysql" })
      );
    });
  });

  it("runs direct account classification actions through v1 APIs", async () => {
    renderWithQueryClient(<AccountClassificationsPage />);

    await screen.findByRole("heading", { name: "账户分类" });
    await screen.findByText("App");
    fireEvent.click(screen.getByRole("button", { name: "自动分类" }));
    fireEvent.click(screen.getByRole("button", { name: "删除分类 App" }));
    expect(await screen.findByRole("alertdialog", { name: "确认删除分类 App" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认删除分类" }));
    fireEvent.click(screen.getByRole("button", { name: "删除规则 root rule" }));
    expect(await screen.findByRole("alertdialog", { name: "确认删除规则 root rule" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认删除规则" }));

    await waitFor(() => {
      expect(actionMocks.autoClassifyAccounts).toHaveBeenCalled();
      expect(actionMocks.deleteAccountClassification).toHaveBeenCalledWith(2);
      expect(actionMocks.deleteAccountClassificationRule).toHaveBeenCalledWith(9);
    });
  });

  it("runs account classification and rule forms through v1 APIs", async () => {
    renderWithQueryClient(<AccountClassificationsPage />);

    await screen.findByRole("heading", { name: "账户分类" });
    fireEvent.click(await screen.findByRole("button", { name: "新建分类" }));
    const createClassificationDialog = await screen.findByRole("dialog", { name: "新建分类" });
    fireEvent.change(within(createClassificationDialog).getByLabelText("分类编码"), { target: { value: "ops" } });
    fireEvent.change(within(createClassificationDialog).getByLabelText("展示名称"), { target: { value: "运维" } });
    fireEvent.change(within(createClassificationDialog).getByLabelText("描述"), { target: { value: "ops accounts" } });
    fireEvent.change(within(createClassificationDialog).getByLabelText("风险等级"), { target: { value: "3" } });
    fireEvent.change(within(createClassificationDialog).getByLabelText("优先级"), { target: { value: "40" } });
    fireEvent.click(within(createClassificationDialog).getByRole("button", { name: "保存分类" }));

    await waitFor(() => {
      expect(actionMocks.createAccountClassification).toHaveBeenCalledWith({
        code: "ops",
        display_name: "运维",
        description: "ops accounts",
        risk_level: 3,
        icon_name: null,
        priority: 40
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "编辑分类 DBA" }));
    const editClassificationDialog = await screen.findByRole("dialog", { name: "编辑分类 DBA" });
    fireEvent.change(within(editClassificationDialog).getByLabelText("展示名称"), { target: { value: "DBA账号" } });
    fireEvent.click(within(editClassificationDialog).getByRole("button", { name: "保存分类" }));

    await waitFor(() => {
      expect(actionMocks.updateAccountClassification).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ code: "dba", display_name: "DBA账号", risk_level: 2 })
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "新建规则" }));
    const createRuleDialog = await screen.findByRole("dialog", { name: "新建规则" });
    fireEvent.change(within(createRuleDialog).getByLabelText("规则名称"), { target: { value: "readonly rule" } });
    expect(within(createRuleDialog).queryByLabelText("规则表达式")).not.toBeInTheDocument();
    expect(await within(createRuleDialog).findByText("全局权限")).toBeInTheDocument();
    expect(await within(createRuleDialog).findByText("数据库权限")).toBeInTheDocument();
    fireEvent.click(within(createRuleDialog).getByRole("checkbox", { name: "选择权限 SELECT" }));
    fireEvent.click(within(createRuleDialog).getByRole("button", { name: "保存规则" }));

    await waitFor(() => {
      expect(actionMocks.createAccountClassificationRule).toHaveBeenCalledWith({
        rule_name: "readonly rule",
        classification_id: 1,
        db_type: "mysql",
        operator: "OR",
        rule_expression: {
          version: 4,
          expr: { op: "OR", args: [{ fn: "has_privilege", args: { name: "SELECT", scope: "global" } }] }
        },
        is_active: true
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "编辑规则 root rule" }));
    const editRuleDialog = await screen.findByRole("dialog", { name: "编辑规则 root rule" });
    fireEvent.change(within(editRuleDialog).getByLabelText("规则名称"), { target: { value: "root rule v2" } });
    fireEvent.click(within(editRuleDialog).getByRole("button", { name: "保存规则" }));

    await waitFor(() => {
      expect(actionMocks.updateAccountClassificationRule).toHaveBeenCalledWith(
        9,
        expect.objectContaining({ rule_name: "root rule v2", classification_id: 1, db_type: "mysql" })
      );
    });
  });

  it("reloads account classification permissions after changing rule database type", async () => {
    renderWithQueryClient(<AccountClassificationsPage />);

    await screen.findByRole("heading", { name: "账户分类" });
    fireEvent.click(await screen.findByRole("button", { name: "新建规则" }));
    const createRuleDialog = await screen.findByRole("dialog", { name: "新建规则" });
    expect(await within(createRuleDialog).findByText("SELECT")).toBeInTheDocument();

    const dbTypeSelect = within(createRuleDialog).getByRole("combobox", { name: "数据库类型" });
    dbTypeSelect.focus();
    fireEvent.keyDown(dbTypeSelect, { key: "ArrowDown" });
    fireEvent.click(await screen.findByRole("option", { name: "PostgreSQL" }));

    expect(await within(createRuleDialog).findByText("预定义角色")).toBeInTheDocument();
    expect(await within(createRuleDialog).findByText("pg_read_all_data")).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchAccountClassificationPermissions).toHaveBeenLastCalledWith("postgresql");
    });
  });

  it("ignores legacy prefixed permission keys in account classification rule forms", async () => {
    vi.mocked(fetchAccountClassificationPermissions).mockResolvedValueOnce({
      permissions: {
        mysql_database_privileges: [{ name: "LEGACY_CREATE", description: "旧口径数据库权限", introduced_in_major: null }],
        mysql_global_privileges: [{ name: "LEGACY_SELECT", description: "旧口径全局权限", introduced_in_major: null }]
      }
    });

    renderWithQueryClient(<AccountClassificationsPage />);

    await screen.findByRole("heading", { name: "账户分类" });
    fireEvent.click(await screen.findByRole("button", { name: "新建规则" }));
    const createRuleDialog = await screen.findByRole("dialog", { name: "新建规则" });

    expect(await within(createRuleDialog).findByText("暂无全局权限")).toBeInTheDocument();
    expect(await within(createRuleDialog).findByText("暂无数据库权限")).toBeInTheDocument();
    expect(within(createRuleDialog).queryByText("LEGACY_SELECT")).not.toBeInTheDocument();
    expect(within(createRuleDialog).queryByText("LEGACY_CREATE")).not.toBeInTheDocument();
  });

  it("opens account classification rule detail with parsed expression and permission metadata", async () => {
    renderWithQueryClient(<AccountClassificationsPage />);

    await screen.findByRole("heading", { name: "账户分类" });
    fireEvent.click(await screen.findByRole("button", { name: "查看规则 root rule" }));

    const detailDialog = await screen.findByRole("dialog", { name: "规则详情 root rule" });
    for (const text of ["规则详情", "root rule", "DBA", "版本 2", "匹配逻辑", "AND · 所有条件满足", "权限配置", "全局权限", "数据库权限", "SELECT", "CREATE"]) {
      expect(await within(detailDialog).findByText(text)).toBeInTheDocument();
    }
    expect(within(detailDialog).queryByText("规则表达式")).not.toBeInTheDocument();
    expect(within(detailDialog).queryByText("权限选项")).not.toBeInTheDocument();
    expect(within(detailDialog).queryByText(/"expr"/)).not.toBeInTheDocument();
    expect(within(detailDialog).getAllByText("mysql").length).toBeGreaterThan(0);
    fireEvent.click(within(detailDialog).getByRole("button", { name: "关闭详情" }));
  });

  it("renders system settings with legacy module navigation, forms, and actions", async () => {
    renderWithQueryClient(<SettingsPage />);

    await screen.findByRole("heading", { name: "系统设置" });
    expect(screen.queryByText("System integrations")).not.toBeInTheDocument();

    for (const text of [
      "设置模块",
      "Alerts",
      "Risk Rules",
      "JumpServer",
      "Veeam",
      "Active Directory",
      "发送设置",
      "投递通道",
      "启用邮件告警",
      "飞书数据源",
      "飞书数据源列表",
      "编辑飞书数据源",
      "飞书机器人 URL",
      "当前飞书 Webhook",
      "清空飞书 Webhook",
      "收件人",
      "发送测试邮件",
      "发送飞书测试",
      "保存配置",
      "规则设置",
      "容量异常增长",
      "容量增长百分比阈值",
      "容量增长绝对阈值",
      "账户同步异常",
      "数据库同步异常",
      "群集状态",
      "高权限账户",
      "备份告警"
    ]) {
      await expectTextPresent(text);
    }
    const moduleTabs = screen.getByRole("tablist");
    for (const label of ["告警设置", "风险规则", "AD 设置"]) {
      expect(within(moduleTabs).queryByRole("tab", { name: label })).not.toBeInTheDocument();
    }
    expect(screen.getByDisplayValue("已配置：https://open.feishu.cn/open-apis/bot/v2/hook/**********oken")).toBeInTheDocument();
    expect(screen.queryByText("共享收件人列表")).not.toBeInTheDocument();
    const capacityRule = screen.getByLabelText("容量异常增长规则");
    expect(within(capacityRule).getByLabelText("容量增长百分比阈值")).toHaveValue(30);
    expect(within(capacityRule).getByLabelText("容量增长绝对阈值")).toHaveValue(20);
    expect(screen.queryByText("系统设置指标")).not.toBeInTheDocument();
    expect(screen.queryByText("JumpServer 数据源设置")).not.toBeInTheDocument();
    expect(screen.queryByText("Veeam 数据源设置")).not.toBeInTheDocument();
    expect(screen.queryByText("AD 域列表")).not.toBeInTheDocument();

    await switchTab("Risk Rules");
    await expectTextPresent("保存规则");
    for (const text of ["备份", "备份问题", "最近一次备份不可用", "严重级别"]) {
      await expectTextPresent(text);
    }
    expect(screen.getByRole("radio", { name: "高" })).toBeChecked();
    expect(screen.queryByText("启用规则")).not.toBeInTheDocument();
    expect(screen.queryByText("发送设置")).not.toBeInTheDocument();

    await switchTab("JumpServer");
    for (const text of [
      "JumpServer 数据源设置",
      "绑定配置",
      "API 凭据",
      "jump-api",
      "JumpServer URL",
      "组织 ID",
      "SSL 证书验证",
      "保存绑定",
      "解绑数据源",
      "同步 JumpServer 资源",
      "运行状态",
      "最近同步状态"
    ]) {
      await expectTextPresent(text);
    }
    expect(screen.getByDisplayValue("completed")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2026-06-11T01:00:00+00:00")).toBeInTheDocument();
    expect(screen.queryByText("邮件告警")).not.toBeInTheDocument();

    await switchTab("Veeam");
    for (const text of [
      "新增数据源",
      "数据源名称",
      "Veeam 凭据",
      "veeam-api",
      "Veeam IP",
      "端口",
      "API 版本",
      "域名列表",
      "启用状态",
      "最近同步",
      "Provider 汇总",
      "保存数据源",
      "删除数据源",
      "新增模式",
      "同步 Veeam 备份",
      "数据源列表"
    ]) {
      await expectTextPresent(text);
    }
    expect(screen.queryByText("JumpServer 数据源设置")).not.toBeInTheDocument();

    await switchTab("Active Directory");
    for (const text of [
      "新增 AD 域",
      "域名",
      "NetBIOS 名称",
      "LDAP 端口",
      "域控地址",
      "Base DN",
      "LDAP 凭据",
      "使用 SSL",
      "证书验证",
      "启用同步",
      "保存 AD 域",
      "删除配置",
      "AD 域账户同步",
      "测试 AD 连接",
      "AD 域列表"
    ]) {
      await expectTextPresent(text);
    }
    expect(screen.getByText(/ldap-bind/)).toBeInTheDocument();
    expect(screen.getByText(/同步状态 completed/)).toBeInTheDocument();
    expect(screen.getByText(/AD对象 12/)).toBeInTheDocument();
    expect(screen.getByText(/SQL账户 8/)).toBeInTheDocument();
    expect(screen.getByText(/孤账户 1/)).toBeInTheDocument();
  });

  it("renders partitions with legacy commands, metric cards, period controls, chart, and list", async () => {
    renderWithQueryClient(<PartitionsPage />);

    await screen.findByRole("heading", { name: "分区管理" });

    for (const text of [
      "创建分区",
      "清理旧分区",
      "分区总数",
      "总大小",
      "总记录数",
      "健康状态",
      "日核心指标趋势",
      "最近7天的核心指标统计",
      "实例数总量",
      "实例日统计数量",
      "数据库数总量",
      "数据库日统计数量",
      "日",
      "周",
      "月",
      "季",
      "分区列表",
      "分区名称",
      "表类型",
      "大小",
      "记录数",
      "分区月份",
      "状态"
    ]) {
      await expectTextPresent(text);
    }

    const metricRegion = screen.getByLabelText("分区指标");
    expect(within(metricRegion).getByText("分区总数")).toBeInTheDocument();
    expect(within(metricRegion).getByText("总大小")).toBeInTheDocument();
    expect(within(metricRegion).getByText("总记录数")).toBeInTheDocument();
    expect(within(metricRegion).getByText("健康状态")).toBeInTheDocument();
    expect(within(metricRegion).queryByText("历史分区")).not.toBeInTheDocument();
    expect(within(metricRegion).queryByText("当前分区")).not.toBeInTheDocument();
    expect(within(metricRegion).queryByText("未来分区")).not.toBeInTheDocument();
    expect(within(metricRegion).queryByText("当前分区大小")).not.toBeInTheDocument();

    const chartLegend = screen.getByLabelText("核心指标趋势图例");
    expect(within(chartLegend).getByLabelText("实例数总量：实例聚合")).toHaveAttribute("data-point-style", "rect");
    expect(within(chartLegend).getByLabelText("实例日统计数量：实例统计")).toHaveAttribute("data-point-style", "star");
    expect(within(chartLegend).getByLabelText("数据库数总量：数据库聚合")).toHaveAttribute("data-point-style", "circle");
    expect(within(chartLegend).getByLabelText("数据库日统计数量：数据库统计")).toHaveAttribute("data-point-style", "triangle");

    expect(screen.getByLabelText("分区状态 历史")).toHaveAttribute("data-status-tone", "muted");
    expect(screen.getByLabelText("分区状态 当前")).toHaveAttribute("data-status-tone", "success");
    expect(screen.getByLabelText("分区状态 未来")).toHaveAttribute("data-status-tone", "info");

    expect(screen.queryByLabelText("年份")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("月份")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("保留月数")).not.toBeInTheDocument();
    expect(screen.queryByText("每页 20 条")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "创建分区" }));
    const createDialog = await screen.findByRole("dialog", { name: "创建分区" });
    expect(within(createDialog).getByLabelText("年份")).toBeInTheDocument();
    expect(within(createDialog).getByLabelText("月份")).toBeInTheDocument();
    fireEvent.click(within(createDialog).getByRole("button", { name: "取消" }));

    fireEvent.click(screen.getByRole("button", { name: "清理旧分区" }));
    const cleanupDialog = await screen.findByRole("alertdialog", { name: "清理旧分区" });
    expect(within(cleanupDialog).getByLabelText("保留月数")).toBeInTheDocument();
  });

  it("runs scheduler, session, settings, and partition actions through v1 APIs", async () => {
    renderWithQueryClient(<SchedulerPage />);
    await screen.findByRole("heading", { name: "定时任务" });
    await screen.findByRole("button", { name: "重新初始化任务" });
    fireEvent.click(screen.getByRole("button", { name: "重新初始化任务" }));
    fireEvent.click(screen.getByRole("button", { name: "暂停任务 同步任务" }));
    fireEvent.click(screen.getByRole("button", { name: "恢复任务 归档任务" }));
    fireEvent.click(screen.getByRole("button", { name: "立即执行 同步任务" }));
    expect(screen.queryByRole("button", { name: "删除任务 同步任务" })).not.toBeInTheDocument();
    await waitFor(() => {
      expect(actionMocks.reloadSchedulerJobs).toHaveBeenCalled();
      expect(actionMocks.pauseSchedulerJob).toHaveBeenCalledWith("job-1");
      expect(actionMocks.resumeSchedulerJob).toHaveBeenCalledWith("job-2");
      expect(actionMocks.runSchedulerJob).toHaveBeenCalledWith("job-1");
      expect(actionMocks.deleteSchedulerJob).not.toHaveBeenCalled();
    });

    cleanup();
    renderWithQueryClient(<SyncSessionsPage />);
    await screen.findByRole("heading", { name: "会话中心" });
    await screen.findByRole("button", { name: "取消任务 s-1" });
    fireEvent.click(screen.getByRole("button", { name: "取消任务 s-1" }));
    expect(await screen.findByRole("alertdialog", { name: "确认取消会话 s-1" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认取消会话" }));
    await waitFor(() => {
      expect(actionMocks.cancelSyncSession).toHaveBeenCalledWith("s-1");
    });

    cleanup();
    renderWithQueryClient(<SettingsPage />);
    await screen.findByRole("heading", { name: "系统设置" });
    await screen.findByRole("button", { name: "发送测试邮件" });
    fireEvent.click(screen.getByRole("button", { name: "发送测试邮件" }));
    fireEvent.click(screen.getByRole("button", { name: "发送飞书测试" }));
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));

    await switchTab("Risk Rules");
    fireEvent.click(screen.getByRole("button", { name: "保存规则" }));

    await switchTab("JumpServer");
    fireEvent.click(screen.getByRole("button", { name: "保存绑定" }));
    fireEvent.click(screen.getByRole("button", { name: "同步 JumpServer 资源" }));
    fireEvent.click(screen.getByRole("button", { name: "解绑数据源" }));

    await switchTab("Veeam");
    fireEvent.click(screen.getByRole("button", { name: "保存数据源" }));
    fireEvent.click(screen.getByRole("button", { name: "停用数据源" }));
    fireEvent.click(screen.getByRole("button", { name: "同步 Veeam 备份" }));
    fireEvent.click(screen.getByRole("button", { name: "删除数据源" }));

    await switchTab("Active Directory");
    fireEvent.click(screen.getByRole("button", { name: "编辑AD域 corp" }));
    fireEvent.click(screen.getByRole("button", { name: "保存 AD 域" }));
    fireEvent.click(screen.getByRole("button", { name: "停用 AD 域" }));
    fireEvent.click(screen.getByRole("button", { name: "测试 AD 连接" }));
    fireEvent.click(screen.getByRole("button", { name: "AD 域账户同步" }));
    fireEvent.click(screen.getByRole("button", { name: "删除配置" }));
    await waitFor(() => {
      expect(actionMocks.sendAlertTestEmail).toHaveBeenCalledWith(["ops@example.com"]);
      expect(actionMocks.sendFeishuTest).toHaveBeenCalledWith("");
      expect(actionMocks.saveAlertSettings).toHaveBeenCalledWith({
        account_sync_failure_enabled: true,
        backup_issue_enabled: true,
        cluster_status_enabled: true,
        database_capacity_enabled: true,
        database_capacity_percent_threshold: 30,
        database_capacity_absolute_gb_threshold: 20,
        database_sync_failure_enabled: false,
        feishu_enabled: true,
        feishu_webhook_url: "",
        clear_feishu_webhook_url: false,
        global_enabled: true,
        privileged_account_enabled: true,
        recipients: ["ops@example.com"]
      });
      expect(actionMocks.saveRiskRules).toHaveBeenCalledWith([{ rule_key: "backup_issue", enabled: true, severity: "high" }]);
      expect(actionMocks.saveJumpServerSource).toHaveBeenCalledWith({
        credential_id: 3,
        base_url: "https://jump.example",
        org_id: "org-1",
        verify_ssl: true
      });
      expect(actionMocks.syncJumpServer).toHaveBeenCalled();
      expect(actionMocks.unbindJumpServer).toHaveBeenCalled();
      expect(actionMocks.updateVeeamSource).toHaveBeenCalledWith(9, {
        name: "veeam-main",
        credential_id: 4,
        server_host: "10.0.0.9",
        server_port: 9419,
        api_version: "v1",
        verify_ssl: true,
        match_domains: ["corp.local"]
      });
      expect(actionMocks.disableVeeamSource).toHaveBeenCalledWith(9);
      expect(actionMocks.syncVeeam).toHaveBeenCalled();
      expect(actionMocks.deleteVeeamSource).toHaveBeenCalledWith(9);
      expect(actionMocks.updateAdDomainConfig).toHaveBeenCalledWith(1, {
        name: "corp",
        netbios_name: "CORP",
        domain_controllers: ["dc01"],
        ldap_port: 636,
        use_ssl: true,
        verify_ssl: true,
        base_dn: "DC=corp,DC=local",
        credential_id: 5,
        is_enabled: true,
        description: null
      });
      expect(actionMocks.setAdDomainConfigEnabled).toHaveBeenCalledWith(1, false);
      expect(actionMocks.testAdDomainConfig).toHaveBeenCalledWith(1);
      expect(actionMocks.syncAdDomains).toHaveBeenCalled();
      expect(actionMocks.deleteAdDomainConfig).toHaveBeenCalledWith(1);
    });

    cleanup();
    renderWithQueryClient(<PartitionsPage />);
    await screen.findByRole("heading", { name: "分区管理" });
    fireEvent.click(screen.getByRole("button", { name: "创建分区" }));
    const createDialog = await screen.findByRole("dialog", { name: "创建分区" });
    await chooseSelectOption(within(createDialog), "年份", "2026年");
    await chooseSelectOption(within(createDialog), "月份", "7月");
    fireEvent.click(within(createDialog).getByRole("button", { name: "创建分区" }));
    fireEvent.click(screen.getByRole("button", { name: "清理旧分区" }));
    expect(actionMocks.cleanupPartitions).not.toHaveBeenCalled();
    const cleanupDialog = await screen.findByRole("alertdialog", { name: "清理旧分区" });
    fireEvent.change(within(cleanupDialog).getByLabelText("保留月数"), { target: { value: "18" } });
    fireEvent.click(within(cleanupDialog).getByRole("button", { name: "开始清理" }));
    await waitFor(() => {
      expect(actionMocks.createPartition).toHaveBeenCalledWith("2026-07-01");
      expect(actionMocks.cleanupPartitions).toHaveBeenCalledWith(18);
    });
  });

  it("updates scheduler cron through the legacy split-field editor", async () => {
    renderWithQueryClient(<SchedulerPage />);

    await screen.findByRole("heading", { name: "定时任务" });
    fireEvent.click(await screen.findByRole("button", { name: "编辑任务 同步任务" }));
    const dialog = await screen.findByRole("dialog", { name: "编辑任务 同步任务" });
    expect(within(dialog).getByLabelText("任务名称")).toHaveValue("同步任务");
    expect(within(dialog).getByLabelText("执行函数")).toHaveValue("tasks.sync");
    for (const label of ["秒", "分钟", "小时", "日", "月份", "星期", "年份"]) {
      expect(within(dialog).getByLabelText(label)).toBeInTheDocument();
    }
    fireEvent.change(within(dialog).getByLabelText("分钟"), { target: { value: "*/10" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "保存任务" }));

    await waitFor(() => {
      expect(actionMocks.updateSchedulerJob).toHaveBeenCalledWith("job-1", {
        trigger_type: "cron",
        cron_expression: "*/10 * * * *"
      });
    });
  });

  it("opens the scheduler job detail provided by the legacy page", async () => {
    renderWithQueryClient(<SchedulerPage />);
    await screen.findByRole("heading", { name: "定时任务" });
    fireEvent.click(await screen.findByRole("button", { name: "查看任务 同步任务" }));
    const jobDialog = await screen.findByRole("dialog", { name: "任务详情 同步任务" });
    expect(await within(jobDialog).findByText("tasks.sync")).toBeInTheDocument();
    expect(within(jobDialog).getByText("2026/6/11 11:55:00")).toBeInTheDocument();
    for (const internalLabel of ["状态", "最大实例数", "错过执行宽限", "触发参数", "位置参数", "关键字参数", "合并执行"]) {
      expect(within(jobDialog).queryByText(internalLabel)).not.toBeInTheDocument();
    }
    expect(fetchSchedulerJobDetail).toHaveBeenCalledWith("job-1");
  });

  it("refreshes scheduler groups after pausing or resuming a job", async () => {
    renderWithQueryClient(<SchedulerPage />);
    await screen.findByRole("heading", { name: "定时任务" });
    await screen.findByRole("button", { name: "暂停任务 同步任务" });
    expect(fetchSchedulerSnapshot).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "暂停任务 同步任务" }));
    await waitFor(() => expect(actionMocks.pauseSchedulerJob).toHaveBeenCalledWith("job-1"));
    await waitFor(() => expect(fetchSchedulerSnapshot).toHaveBeenCalledTimes(2));

    fireEvent.click(screen.getByRole("button", { name: "恢复任务 归档任务" }));
    await waitFor(() => expect(actionMocks.resumeSchedulerJob).toHaveBeenCalledWith("job-2"));
    await waitFor(() => expect(fetchSchedulerSnapshot).toHaveBeenCalledTimes(3));
  });

  it("runs tag bulk assignment and removal from the legacy-style page", async () => {
    renderWithQueryClient(<TagBulkAssignPage />);

    await screen.findByRole("heading", { name: "批量分配标签" });
    expect(screen.getByRole("link", { name: "返回标签管理" })).toHaveAttribute("href", "/tags");
    expect(screen.getByRole("tab", { name: "分配模式" })).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByText("选择实例")).toBeInTheDocument();
    expect(screen.getByText("选择标签")).toBeInTheDocument();
    expect(screen.getByText("当前选择")).toBeInTheDocument();
    expect(screen.getByText("10.0.0.1:3306 · MySQL")).toBeInTheDocument();
    const mysqlGroup = screen.getByRole("button", { name: /数据库类型 MySQL/ });
    const envGroup = screen.getByRole("button", { name: /标签分类 env/ });
    expect(mysqlGroup).toHaveAttribute("aria-expanded", "true");
    expect(envGroup).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(mysqlGroup);
    expect(mysqlGroup).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(mysqlGroup);
    expect(mysqlGroup).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(envGroup);
    expect(envGroup).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(envGroup);
    expect(envGroup).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(await screen.findByLabelText("选择实例 mysql-prod"));
    fireEvent.click(screen.getByLabelText("选择标签 生产"));
    expect(screen.getAllByText("mysql-prod").length).toBeGreaterThan(1);
    expect(screen.getAllByText("生产").length).toBeGreaterThan(1);
    fireEvent.click(screen.getByRole("button", { name: "分配标签" }));

    await waitFor(() => {
      expect(actionMocks.assignTagsToInstances).toHaveBeenCalledWith([1], [1]);
    });

    await switchTab("移除模式");
    expect(screen.getByText("选择要移除标签的实例，系统将移除这些实例上的所有标签。")).toBeInTheDocument();
    expect(screen.queryByLabelText("选择标签 生产")).not.toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("选择实例 mysql-prod"));
    fireEvent.click(screen.getByRole("button", { name: "移除标签" }));

    await waitFor(() => {
      expect(actionMocks.removeAllTagsFromInstances).toHaveBeenCalledWith([1]);
    });
  });

  it("switches partition core metrics period through v1 API parameters", async () => {
    renderWithQueryClient(<PartitionsPage />);

    await screen.findByRole("heading", { name: "分区管理" });
    await waitFor(() => expect(screen.getByText("2026年6月")).toBeInTheDocument());
    vi.mocked(fetchPartitionsSnapshot).mockClear();

    fireEvent.click(screen.getByRole("button", { name: "周" }));

    await waitFor(() => {
      expect(fetchPartitionsSnapshot).toHaveBeenLastCalledWith({
        days: 7,
        limit: 20,
        page: 1,
        periodType: "weekly",
        search: "",
        status: "",
        tableType: ""
      });
    });
  });
});
