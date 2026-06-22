import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchAccountScopeOptions,
  fetchClassificationStatisticsSnapshot,
  fetchPartitionsSnapshot,
  fetchSchedulerJobDetail,
} from "@/api/readOnly";
import { runAction } from "@/utils/action-feedback";

import {
  AccountClassificationsPage,
  ClassificationStatisticsPage,
  ClustersPage,
  CredentialsPage,
  PartitionsPage,
  SchedulerPage,
  SettingsPage,
  SyncSessionsPage,
  TagsPage,
  UsersPage
} from "./RemainingReadOnlyPages";

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

vi.mock("@/api/readOnly", () => ({
  fetchClustersSnapshot: vi.fn(async () => ({
    sqlServer: { items: [{ id: 1, name: "sql-ag", domain_name: "corp.local", is_enabled: true, instance_count: 2, availability_group_count: 1, last_ag_sync_status: "completed" }], total: 1, page: 1, pages: 1, limit: 20 },
    mySql: { items: [{ id: 2, name: "mysql-repl", is_enabled: true, instance_count: 3, replication_status: "healthy" }], total: 1, page: 1, pages: 1, limit: 20 }
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
    availability_group: { id: 21, name: "ag-sales", listener_name: "ag-listener" },
    replicas: [{ replica_server_name: "sql-node-1", role_desc: "PRIMARY" }],
    databases: [{ database_name: "sales", synchronization_state_desc: "SYNCHRONIZED" }]
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
    rulesByDbType: { mysql: [{ id: 9, rule_name: "root rule", classification_name: "DBA", db_type: "mysql", is_active: true, matched_accounts_count: 8 }] }
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
      rule_expression: { fn: "username_like", args: ["root"] },
      created_at: "2026-06-01T00:00:00+08:00",
      updated_at: "2026-06-02T00:00:00+08:00"
    }
  })),
  fetchAccountClassificationPermissions: vi.fn(async () => ({
    permissions: { mysql: ["SELECT", "SUPER"] }
  })),
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
    stats: { dba: { total_accounts: 8, matched_accounts_count: 8 } },
    trends: {
      buckets: [{ period_start: "2026-06-05", period_end: "2026-06-05" }],
      series: [{ classification_id: 1, classification_name: "DBA", points: [{ period_start: "2026-06-05", value: 8 }] }]
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
        state: "STATE_RUNNING",
        trigger_type: "cron",
        trigger_args: { minute: "*/5", description: "每 5 分钟" },
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
  fetchSyncSessionsSnapshot: vi.fn(async () => ({
    items: [
      {
        id: 1,
        session_id: "s-1",
        sync_type: "manual",
        sync_category: "accounts",
        status: "running",
        total_instances: 2,
        successful_instances: 1,
        failed_instances: 0,
        started_at: "2026-06-11T12:00:00+08:00"
      }
    ],
    total: 1,
    page: 1,
    pages: 1
  })),
  fetchSyncSessionDetail: vi.fn(async () => ({
    session: {
      id: 1,
      session_id: "s-1",
      sync_type: "manual",
      sync_category: "accounts",
      status: "running",
      started_at: "2026-06-11T12:00:00+08:00",
      completed_at: null,
      total_instances: 2,
      successful_instances: 1,
      failed_instances: 0,
      progress_percentage: 50,
      instance_records: [
        {
          id: 11,
          session_id: "s-1",
          instance_id: 100,
          instance_name: "mysql-prod",
          sync_category: "accounts",
          status: "running",
          started_at: "2026-06-11T12:00:00+08:00",
          completed_at: null,
          items_synced: 10,
          items_created: 2,
          items_updated: 7,
          items_deleted: 1,
          error_message: null,
          sync_details: { phase: "accounts" }
        }
      ]
    }
  })),
  fetchSyncSessionErrorLogs: vi.fn(async () => ({
    session: { session_id: "s-1", status: "running" },
    error_records: [
      {
        id: 12,
        session_id: "s-1",
        instance_name: "oracle-failed",
        sync_category: "accounts",
        status: "failed",
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
        feishu_webhook_url: "https://feishu.example",
        recipients: ["ops@example.com"],
        database_capacity_enabled: true,
        account_sync_failure_enabled: true,
        database_sync_failure_enabled: false,
        cluster_status_enabled: true,
        privileged_account_enabled: true,
        backup_issue_enabled: true
      }
    },
    riskRules: [{ rule_key: "backup_issue", enabled: true, severity: "high" }],
    jumpserver: { provider_ready: true, binding: { credential_id: 3, base_url: "https://jump.example", org_id: "org-1", verify_ssl: true }, api_credentials: [] },
    veeam: { provider_ready: false, sources: [{ id: 9, name: "veeam-main", credential_id: 4, server_host: "10.0.0.9", server_port: 9419, api_version: "v1", is_active: true, verify_ssl: true, domains: ["corp.local"] }], veeam_credentials: [] },
    adDomains: { configs: [{ id: 1, name: "corp", netbios_name: "CORP", ldap_port: 636, domain_controllers: ["dc01"], base_dn: "DC=corp,DC=local", credential_id: 5, use_ssl: true, verify_ssl: true, is_enabled: true }] }
  })),
  fetchCredentialsSnapshot: vi.fn(async () => ({
    items: [{ id: 1, name: "prod-db", credential_type: "database", db_type: "mysql", username: "root", is_active: true, instance_count: 2 }],
    total: 1,
    page: 1,
    pages: 1,
    limit: 20
  })),
  fetchTagsSnapshot: vi.fn(async () => ({
    list: { items: [{ id: 1, name: "prod", display_name: "生产", category: "env", is_active: true, instance_count: 3 }], total: 1, page: 1, pages: 1, limit: 20, stats: { total: 1, active: 1, inactive: 0, category_count: 1 } },
    categories: ["env"]
  })),
  fetchTagBulkOptions: vi.fn(async () => ({
    instances: [{ id: 1, name: "mysql-prod", db_type: "mysql", host: "10.0.0.1" }],
    tags: [{ id: 1, name: "prod", display_name: "生产", category: "env", is_active: true }],
    categoryNames: ["env"]
  })),
  fetchPartitionsSnapshot: vi.fn(async () => ({
    status: { data: { status: "healthy", total_partitions: 1, total_size: "1 MB", total_records: 1, missing_partitions: [] }, timestamp: "2026-06-11T00:00:00+08:00" },
    list: { items: [{ name: "p202606", table: "account_stats", table_type: "stats", size: "1 MB", record_count: 1, status: "healthy" }], total: 1, page: 1, pages: 1, limit: 20 },
    coreMetrics: { labels: ["06-11"], datasets: [{ label: "分区", data: [1] }], dataPointCount: 1, timeRange: "7d", yAxisLabel: "count", chartTitle: "核心指标", periodType: "daily" }
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

describe("RemainingReadOnlyPages", () => {
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
    ["系统设置", <SettingsPage />, ["设置模块", "告警设置", "邮件告警"]],
    ["凭据管理", <CredentialsPage />, ["prod-db", "root"]],
    ["标签管理", <TagsPage />, ["生产", "env"]],
    ["分区管理", <PartitionsPage />, ["p202606", "healthy"]]
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
    expect(screen.getByRole("button", { name: "批量分配" })).toBeInTheDocument();
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
    fireEvent.change(within(createDialog).getByLabelText("分类"), { target: { value: "env" } });
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

    for (const text of ["重新初始化任务", "运行中的任务", "已暂停的任务", "同步任务", "归档任务", "下次运行", "上次运行", "任务 ID", "触发器参数"]) {
      await expectTextPresent(text);
    }

    expect(screen.getByRole("button", { name: "暂停任务 同步任务" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "恢复任务 归档任务" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "立即执行 同步任务" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "编辑任务 同步任务" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "删除任务 同步任务" })).toBeInTheDocument();
  });

  it("renders sync sessions with legacy filters, fields, progress, and actions", async () => {
    renderWithQueryClient(<SyncSessionsPage />);

    await screen.findByRole("heading", { name: "会话中心" });

    for (const text of ["来源", "分类", "状态", "运行ID", "进度", "任务", "开始时间", "耗时", "操作", "50%", "manual", "accounts"]) {
      await expectTextPresent(text);
    }

    expect(screen.getByRole("button", { name: "查看详情 s-1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "取消任务 s-1" })).toBeInTheDocument();
    expect(screen.queryByText("会话指标")).not.toBeInTheDocument();
    expect(screen.queryByText("会话总数")).not.toBeInTheDocument();
    expect(screen.queryByText("最近同步会话首屏列表。")).not.toBeInTheDocument();
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
    expect(await within(sqlDetailDialog).findByText("ag-sales")).toBeInTheDocument();
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
    await waitFor(() => {
      expect(actionMocks.syncSqlServerAgAccounts).toHaveBeenCalledTimes(2);
    });

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
    expect(await within(agDialog).findByText("sql-node-1")).toBeInTheDocument();
    expect(await within(agDialog).findByText("sales")).toBeInTheDocument();
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
      "刷新",
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
      "覆盖 1/1 天",
      "规则贡献（当前周期）",
      "说明：规则之间允许重叠，“各规则之和”不等于分类去重总数。"
    ]) {
      await expectTextPresent(text);
    }

    fireEvent.click(screen.getByRole("combobox", { name: "统计周期" }));
    for (const option of ["周统计", "月统计", "季统计"]) {
      expect(await screen.findByRole("option", { name: option })).toBeInTheDocument();
    }
    for (const text of ["分类统计指标", "统计分类", "趋势序列", "周期数量", "Top 命中", "分类排行", "分类趋势面积图", "选择分类后展示当前周期 Top 规则贡献。"] ) {
      expect(screen.queryByText(text)).not.toBeInTheDocument();
    }
  });

  it("loads classification rule list, contributions, and rule trend after selecting a classification", async () => {
    renderWithQueryClient(<ClassificationStatisticsPage />);

    await screen.findByRole("heading", { name: "分类统计" });
    fireEvent.click(await screen.findByRole("combobox", { name: "账户分类" }));
    fireEvent.click(await screen.findByRole("option", { name: "DBA" }));
    fireEvent.click(screen.getByRole("button", { name: "应用" }));

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
    fireEvent.click(screen.getByRole("button", { name: "应用" }));

    await waitFor(() => {
      expect(fetchClassificationStatisticsSnapshot).toHaveBeenLastCalledWith(
        expect.objectContaining({ accountScope: "instance:11", dbType: "mysql" })
      );
    });
  });

  it("refreshes classification statistics through unified action feedback", async () => {
    renderWithQueryClient(<ClassificationStatisticsPage />);

    await screen.findByRole("heading", { name: "分类统计" });
    vi.mocked(fetchClassificationStatisticsSnapshot).mockClear();
    fireEvent.click(screen.getByRole("button", { name: "刷新" }));

    await waitFor(() => {
      expect(fetchClassificationStatisticsSnapshot).toHaveBeenCalledTimes(1);
    });
    expect(runAction).toHaveBeenCalledWith(expect.any(Promise), { success: "分类统计已刷新" });
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
    fireEvent.change(within(createRuleDialog).getByLabelText("规则表达式"), {
      target: { value: "{\"fn\":\"username_like\",\"args\":[\"readonly\"]}" }
    });
    fireEvent.click(within(createRuleDialog).getByRole("button", { name: "校验表达式" }));
    await waitFor(() => {
      expect(actionMocks.validateAccountClassificationRuleExpression).toHaveBeenCalledWith({
        fn: "username_like",
        args: ["readonly"]
      });
    });
    fireEvent.click(within(createRuleDialog).getByRole("button", { name: "保存规则" }));

    await waitFor(() => {
      expect(actionMocks.createAccountClassificationRule).toHaveBeenCalledWith({
        rule_name: "readonly rule",
        classification_id: 1,
        db_type: "mysql",
        operator: "any",
        rule_expression: { fn: "username_like", args: ["readonly"] },
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

  it("opens account classification rule detail with parsed expression and permission metadata", async () => {
    renderWithQueryClient(<AccountClassificationsPage />);

    await screen.findByRole("heading", { name: "账户分类" });
    fireEvent.click(await screen.findByRole("button", { name: "查看规则 root rule" }));

    const detailDialog = await screen.findByRole("dialog", { name: "规则详情 root rule" });
    for (const text of ["规则详情", "root rule", "DBA", "版本 2", "username_like", "权限选项", "SELECT", "SUPER"]) {
      expect(await within(detailDialog).findByText(text)).toBeInTheDocument();
    }
    expect(within(detailDialog).getAllByText("mysql").length).toBeGreaterThan(0);
    fireEvent.click(within(detailDialog).getByRole("button", { name: "关闭详情" }));
  });

  it("renders system settings with legacy module navigation, forms, and actions", async () => {
    renderWithQueryClient(<SettingsPage />);

    await screen.findByRole("heading", { name: "系统设置" });
    expect(screen.queryByText("System integrations")).not.toBeInTheDocument();

    for (const text of [
      "设置模块",
      "告警设置",
      "风险规则",
      "JumpServer",
      "Veeam",
      "AD 设置",
      "发送设置",
      "投递通道",
      "启用邮件告警",
      "发送到飞书",
      "飞书机器人 URL",
      "收件人",
      "共享收件人列表",
      "发送测试邮件",
      "发送飞书测试",
      "保存配置",
      "规则设置",
      "容量异常增长",
      "账户同步异常",
      "数据库同步异常",
      "群集状态",
      "高权限账户",
      "备份告警"
    ]) {
      await expectTextPresent(text);
    }
    expect(screen.queryByText("系统设置指标")).not.toBeInTheDocument();
    expect(screen.queryByText("JumpServer 数据源设置")).not.toBeInTheDocument();
    expect(screen.queryByText("Veeam 数据源设置")).not.toBeInTheDocument();
    expect(screen.queryByText("AD 域列表")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "风险规则" }));
    await expectTextPresent("保存规则");
    await expectTextPresent("仅影响风险中心展示");
    expect(screen.queryByText("发送设置")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "JumpServer" }));
    for (const text of [
      "JumpServer 数据源设置",
      "绑定配置",
      "API 凭据",
      "JumpServer URL",
      "组织 ID",
      "SSL 证书验证",
      "保存绑定",
      "解绑数据源",
      "同步 JumpServer 资源",
      "运行状态"
    ]) {
      await expectTextPresent(text);
    }
    expect(screen.queryByText("邮件告警")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Veeam" }));
    for (const text of [
      "新增数据源",
      "数据源名称",
      "Veeam 凭据",
      "Veeam IP",
      "端口",
      "API 版本",
      "域名列表",
      "保存数据源",
      "删除数据源",
      "新增模式",
      "同步 Veeam 备份",
      "数据源列表"
    ]) {
      await expectTextPresent(text);
    }
    expect(screen.queryByText("JumpServer 数据源设置")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "AD 设置" }));
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
      "AD 域列表"
    ]) {
      await expectTextPresent(text);
    }
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
      "数据库连接",
      "核心指标趋势",
      "最近7天的核心指标统计",
      "日",
      "周",
      "月",
      "季",
      "分区列表",
      "分区",
      "表",
      "类型",
      "大小",
      "记录",
      "状态"
    ]) {
      await expectTextPresent(text);
    }

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
    fireEvent.click(screen.getByRole("button", { name: "删除任务 同步任务" }));
    expect(await screen.findByRole("alertdialog", { name: "确认删除任务 同步任务" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认删除任务" }));
    await waitFor(() => {
      expect(actionMocks.reloadSchedulerJobs).toHaveBeenCalled();
      expect(actionMocks.pauseSchedulerJob).toHaveBeenCalledWith("job-1");
      expect(actionMocks.resumeSchedulerJob).toHaveBeenCalledWith("job-2");
      expect(actionMocks.runSchedulerJob).toHaveBeenCalledWith("job-1");
      expect(actionMocks.deleteSchedulerJob).toHaveBeenCalledWith("job-1");
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

    fireEvent.click(screen.getByRole("button", { name: "风险规则" }));
    fireEvent.click(screen.getByRole("button", { name: "保存规则" }));

    fireEvent.click(screen.getByRole("button", { name: "JumpServer" }));
    fireEvent.click(screen.getByRole("button", { name: "保存绑定" }));
    fireEvent.click(screen.getByRole("button", { name: "同步 JumpServer 资源" }));
    fireEvent.click(screen.getByRole("button", { name: "解绑数据源" }));

    fireEvent.click(screen.getByRole("button", { name: "Veeam" }));
    fireEvent.click(screen.getByRole("button", { name: "保存数据源" }));
    fireEvent.click(screen.getByRole("button", { name: "停用数据源" }));
    fireEvent.click(screen.getByRole("button", { name: "同步 Veeam 备份" }));
    fireEvent.click(screen.getByRole("button", { name: "删除数据源" }));

    fireEvent.click(screen.getByRole("button", { name: "AD 设置" }));
    fireEvent.click(screen.getByRole("button", { name: "保存 AD 域" }));
    fireEvent.click(screen.getByRole("button", { name: "停用 AD 域" }));
    fireEvent.click(screen.getByRole("button", { name: "测试 AD 连接" }));
    fireEvent.click(screen.getByRole("button", { name: "AD 域账户同步" }));
    fireEvent.click(screen.getByRole("button", { name: "删除配置" }));
    await waitFor(() => {
      expect(actionMocks.sendAlertTestEmail).toHaveBeenCalledWith(["ops@example.com"]);
      expect(actionMocks.sendFeishuTest).toHaveBeenCalledWith("https://feishu.example");
      expect(actionMocks.saveAlertSettings).toHaveBeenCalledWith({
        account_sync_failure_enabled: true,
        backup_issue_enabled: true,
        cluster_status_enabled: true,
        database_capacity_enabled: true,
        database_sync_failure_enabled: false,
        feishu_enabled: true,
        feishu_webhook_url: "https://feishu.example",
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

  it("updates scheduler cron through a React dialog", async () => {
    renderWithQueryClient(<SchedulerPage />);

    await screen.findByRole("heading", { name: "定时任务" });
    fireEvent.click(await screen.findByRole("button", { name: "编辑任务 同步任务" }));
    const dialog = await screen.findByRole("dialog", { name: "编辑任务 同步任务" });
    fireEvent.change(within(dialog).getByLabelText("Cron 表达式"), { target: { value: "*/10 * * * *" } });
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
    expect(fetchSchedulerJobDetail).toHaveBeenCalledWith("job-1");
  });

  it("runs tag bulk assignment and removal through v1 APIs", async () => {
    renderWithQueryClient(<TagsPage />);

    await screen.findByRole("heading", { name: "标签管理" });
    fireEvent.click(await screen.findByRole("button", { name: "批量分配" }));
    const dialog = await screen.findByRole("dialog", { name: "批量分配标签" });
    fireEvent.click(await within(dialog).findByLabelText("实例 mysql-prod"));
    fireEvent.click(within(dialog).getByLabelText("标签 生产"));
    fireEvent.click(within(dialog).getByRole("button", { name: "执行批量分配" }));

    await waitFor(() => {
      expect(actionMocks.assignTagsToInstances).toHaveBeenCalledWith([1], [1]);
    });

    fireEvent.click(screen.getByRole("button", { name: "批量分配" }));
    const removeDialog = await screen.findByRole("dialog", { name: "批量分配标签" });
    await chooseSelectOption(within(removeDialog), "操作", "批量移除全部标签");
    fireEvent.click(await within(removeDialog).findByLabelText("实例 mysql-prod"));
    fireEvent.click(within(removeDialog).getByRole("button", { name: "执行批量移除全部" }));

    await waitFor(() => {
      expect(actionMocks.removeAllTagsFromInstances).toHaveBeenCalledWith([1]);
    });
  });

  it("switches partition core metrics period through v1 API parameters", async () => {
    renderWithQueryClient(<PartitionsPage />);

    await screen.findByRole("heading", { name: "分区管理" });
    await waitFor(() => expect(screen.getByText("p202606")).toBeInTheDocument());
    vi.mocked(fetchPartitionsSnapshot).mockClear();

    fireEvent.click(screen.getByRole("button", { name: "周" }));

    await waitFor(() => {
      expect(fetchPartitionsSnapshot).toHaveBeenLastCalledWith({ days: 28, periodType: "weekly" });
    });
  });
});
