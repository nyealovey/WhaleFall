import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { TooltipProvider } from "@/components/ui/tooltip";

import { AccountLedgersPage, DatabaseLedgersPage, InstanceDetailPage, InstancesPage } from "./ListPages";

const actionMocks = vi.hoisted(() => ({
  batchTestInstanceConnections: vi.fn(async () => ({ ok: true })),
  batchDeleteInstances: vi.fn(async () => ({ deleted_count: 1 })),
  createInstance: vi.fn(async () => ({ ok: true })),
  deleteInstance: vi.fn(async () => ({ ok: true })),
  importInstancesFromCsv: vi.fn(async () => ({ created_count: 1 })),
  refreshDatabaseTableSizes: vi.fn(async () => ({ ok: true })),
  restoreInstance: vi.fn(async () => ({ ok: true })),
  syncAccounts: vi.fn(async () => ({ run_id: "accounts-run" })),
  syncDatabases: vi.fn(async () => ({ run_id: "databases-run" })),
  syncInstanceAccounts: vi.fn(async () => ({ session_id: "accounts-run" })),
  syncInstanceAuditInfo: vi.fn(async () => ({ session_id: "audit-run" })),
  syncInstanceBackup: vi.fn(async () => ({ run_id: "backup-run" })),
  syncInstanceCapacity: vi.fn(async () => ({ result: { refreshed: 1 } })),
  testInstanceConnection: vi.fn(async () => ({ ok: true })),
  validateInstanceConnectionParams: vi.fn(async () => ({ ok: true })),
  updateInstance: vi.fn(async () => ({ ok: true }))
}));

vi.mock("@/api/actions", () => actionMocks);

vi.mock("@/api/lists", () => ({
  buildAccountLedgersExportPath: vi.fn(() => "/api/v1/accounts/ledgers/exports"),
  buildDatabaseLedgersExportPath: vi.fn(() => "/api/v1/databases/ledgers/exports"),
  buildInstancesExportPath: vi.fn(() => "/api/v1/instances/exports"),
  fetchAccountClassificationOptions: vi.fn(async () => [{ code: "sensitive", display_name: "敏感" }]),
  fetchTagOptions: vi.fn(async () => [{ name: "prod", display_name: "生产" }]),
  fetchCredentialOptions: vi.fn(async () => [
    { id: 8, name: "prod credential", credential_type: "database", db_type: "mysql", is_active: true },
    { id: 9, name: "disabled credential", credential_type: "database", db_type: "mysql", is_active: false }
  ]),
  fetchInstances: vi.fn(async () => ({
    items: [
      {
        id: 1,
        name: "mysql-prod",
        db_type: "mysql",
        host: "10.0.0.8",
        port: 3306,
        is_active: true,
        status: "ok",
        audit_status: "enabled",
        backup_status: "backed_up",
        backup_last_time: "2026-06-11T01:00:00+00:00",
        is_jumpserver_managed: true,
        active_db_count: 12,
        active_account_count: 20,
        tags: [{ name: "prod", display_name: "生产" }]
      },
      {
        id: 4,
        name: "mysql-old",
        db_type: "mysql",
        host: "10.0.0.9",
        port: 3306,
        is_active: false,
        deleted_at: "2026-06-10T00:00:00+00:00",
        status: "deleted",
        audit_status: "configured_disabled",
        backup_status: "not_backed_up",
        is_jumpserver_managed: false,
        active_db_count: 0,
        active_account_count: 0,
        tags: []
      }
    ],
    total: 2,
    page: 1,
    pages: 1,
    limit: 20
  })),
  fetchDatabaseLedgers: vi.fn(async () => ({
    items: [
      {
        id: 2,
        database_name: "app_db",
        instance: { id: 1, name: "mysql-prod", host: "10.0.0.8", db_type: "mysql" },
        db_type: "mysql",
        capacity: { size_mb: 2048, size_bytes: 2147483648, label: "2.00 GB", collected_at: "2026-06-11T01:00:00+00:00" },
        sync_status: { value: "completed", label: "已更新", variant: "success" },
        tags: [{ name: "core", display_name: "核心" }]
      }
    ],
    total: 1,
    page: 1,
    limit: 20
  })),
  fetchAccountLedgers: vi.fn(async () => ({
    items: [
      {
        id: 3,
        username: "readonly",
        instance_name: "mysql-prod",
        instance_host: "10.0.0.8",
        db_type: "mysql",
        is_locked: false,
        is_superuser: false,
        is_active: true,
        is_deleted: false,
        last_change_time: "2026-06-11T01:00:00+00:00",
        availability_reasons: [],
        tags: [{ name: "prod", display_name: "生产" }],
        classifications: [{ display_name: "只读账户" }]
      }
    ],
    total: 1,
    page: 1,
    pages: 1,
    limit: 20
  })),
  fetchInstanceDetail: vi.fn(async () => ({
    instance: {
      id: 1,
      name: "mysql-prod",
      db_type: "sqlserver",
      host: "10.0.0.8",
      port: 3306,
      description: "生产实例",
      is_active: true,
      audit_status: "enabled",
      backup_status: "backed_up",
      main_version: "8.0",
      last_sync_time: "2026-06-11T01:00:00+00:00",
      tags: [{ name: "prod", display_name: "生产" }]
    }
  })),
  fetchInstanceConnectionStatus: vi.fn(async () => ({
    instance_id: 1,
    instance_name: "mysql-prod",
    db_type: "mysql",
    host: "10.0.0.8",
    port: 3306,
    status: "ok",
    is_active: true,
    last_connected: "2026-06-11T01:30:00+00:00"
  })),
  fetchInstanceAuditInfo: vi.fn(async () => ({
    instance_id: 1,
    instance_name: "mysql-prod",
    db_type: "mysql",
    supported: true,
    available: true,
    last_sync_time: "2026-06-11T01:20:00+00:00",
    facts: {
      audit_count: 2,
      enabled_audit_count: 1,
      specification_count: 3,
      covered_database_count: 4
    },
    snapshot: {
      server_audits: [{ name: "AuditProd", is_state_enabled: true }],
      audit_specifications: [{ name: "SpecServer", is_state_enabled: true }],
      database_audit_specifications: [{ name: "SpecDb", database_name: "app_db", is_state_enabled: false }]
    }
  })),
  fetchInstanceBackupInfo: vi.fn(async () => ({
    instance_id: 1,
    instance_name: "mysql-prod",
    backup_status: "backed_up",
    backup_last_time: "2026-06-11T01:10:00+00:00",
    matched_machine_name: "mysql-prod",
    backup_id: "backup-1",
    source_name: "生产 Veeam",
    source_server_host: "10.0.0.9",
    backup_chain_size_bytes: 2147483648,
    restore_point_count: 2,
    backup_metrics_coverage: {
      expected_restore_point_count: 2,
      enriched_restore_point_count: 1,
      missing_restore_point_count: 1,
      partial: true
    },
    restore_points: [
      {
        id: "rp-1",
        name: "Restore 1",
        type: "full",
        backup_id: "backup-1",
        data_size_bytes: 2147483648,
        backup_size_bytes: 1073741824,
        compress_ratio: 50,
        creation_time: "2026-06-11T01:00:00+00:00"
      }
    ]
  })),
  fetchInstanceAccounts: vi.fn(async () => ({
    items: [
      {
        id: 3,
        username: "readonly",
        instance_name: "mysql-prod",
        instance_host: "10.0.0.8",
        db_type: "sqlserver",
        is_locked: false,
        is_superuser: false,
        is_active: true,
        is_deleted: false,
        last_change_time: "2026-06-11T01:00:00+00:00",
        availability_reasons: [],
        tags: [{ name: "prod", display_name: "生产" }],
        classifications: [{ display_name: "只读账户" }],
        type_specific: { plugin: "mysql_native_password", account_kind: "user" }
      },
      {
        id: 4,
        username: "sa",
        instance_name: "mysql-prod",
        instance_host: "10.0.0.8",
        db_type: "sqlserver",
        is_locked: true,
        is_superuser: true,
        is_active: true,
        is_deleted: false,
        last_change_time: "2026-06-11T02:00:00+00:00",
        availability_reasons: ["策略锁定"],
        tags: [],
        classifications: [],
        type_specific: {}
      }
    ],
    total: 2,
    page: 1,
    pages: 1,
    limit: 200
  })),
  fetchInstanceAgAccounts: vi.fn(async () => ({
    cluster: { id: 8, name: "sqlserver-ag-prod" },
    items: [
      {
        id: 5,
        username: "ag_reader",
        db_type: "sqlserver",
        availability_group_name: "AG_PROD",
        listener_name: "AG_LISTENER",
        listener_host: "ag-listener.whalefall.local",
        is_locked: false,
        is_superuser: false,
        is_active: true,
        is_deleted: false,
        last_change_time: "2026-06-11T03:00:00+00:00",
        availability_reasons: []
      }
    ],
    total: 1,
    summary: { total: 1, active: 1, deleted: 0, superuser: 0 }
  })),
  fetchInstanceDatabaseSizes: vi.fn(async () => ({
    total: 2,
    page: 1,
    pages: 1,
    limit: 100,
    active_count: 1,
    filtered_count: 1,
    total_size_mb: 2048,
    databases: [
      {
        id: 2,
        database_name: "app_db",
        size_mb: 2048,
        data_size_mb: 1536,
        log_size_mb: 512,
        collected_at: "2026-06-11T01:00:00+00:00",
        is_active: true
      },
      {
        id: 3,
        database_name: "legacy_db",
        size_mb: 0,
        collected_at: null,
        is_active: false,
        last_seen_date: "2026-06-10",
        deleted_at: "2026-06-11T02:00:00+00:00"
      }
    ]
  })),
  fetchAccountPermissions: vi.fn(async () => ({
    account: { id: 3, username: "readonly", db_type: "mysql", instance_name: "mysql-prod" },
    permissions: {
      db_type: "mysql",
      username: "readonly",
      is_superuser: false,
      last_sync_time: "2026-06-11T01:00:00+00:00",
      snapshot: { roles: ["reader"], grants: ["SELECT"] }
    }
  })),
  fetchAccountChangeHistory: vi.fn(async () => ({
    account: { id: 3, username: "readonly", db_type: "mysql" },
    history: [{ id: 88, change_type: "grant", status: "success", message: "GRANT SELECT", change_time: "2026-06-11T01:00:00+00:00" }]
  })),
  fetchDatabaseTableSizes: vi.fn(async () => ({
    total: 1,
    page: 1,
    pages: 1,
    limit: 20,
    collected_at: "2026-06-11T01:00:00+00:00",
    tables: [{ schema_name: "public", table_name: "orders", size_mb: 12, data_size_mb: 9, index_size_mb: 3, row_count: 100 }]
  }))
}));

function renderWithQueryClient(element: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>{element}</TooltipProvider>
    </QueryClientProvider>
  );
}

async function expectTextPresent(text: string) {
  await waitFor(() => {
    expect(screen.getAllByText(text).length).toBeGreaterThan(0);
  });
}

describe("ListPages", () => {
  it("renders instances from the API", async () => {
    renderWithQueryClient(<InstancesPage />);

    await waitFor(() => {
      expect(screen.getByText("mysql-prod")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "实例管理" })).toBeInTheDocument();
    expect(screen.getByText("10.0.0.8:3306")).toBeInTheDocument();
    expect(screen.getAllByText("生产").length).toBeGreaterThan(0);
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders instances with legacy filters, fields, and actions", async () => {
    renderWithQueryClient(<InstancesPage />);

    await expectTextPresent("mysql-prod");
    expect(screen.queryByText("每页 20 条")).not.toBeInTheDocument();

    for (const label of ["搜索", "类型", "状态", "审计", "托管", "备份", "标签"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
    for (const header of ["名称", "类型", "主机/IP", "状态", "审计", "已托管", "备份", "活跃", "版本 / 同步", "标签", "操作"]) {
      expect(screen.getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
    for (const action of ["实例统计", "添加实例", "移入回收站", "批量测试连接", "批量导入", "显示已删除", "导出CSV"]) {
      expect(screen.getAllByText(action).length).toBeGreaterThan(0);
    }
    expect(screen.queryByRole("button", { name: "查看详情 1" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看详情 1" })).toHaveAttribute("href", "/console/instances/1");
    expect(screen.getByRole("button", { name: "编辑实例 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "测试连接 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "删除实例 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "恢复实例 4" })).toBeInTheDocument();
  });

  it("runs instance create and update forms through v1 APIs", async () => {
    renderWithQueryClient(<InstancesPage />);

    await expectTextPresent("mysql-prod");
    fireEvent.click(screen.getByRole("button", { name: "添加实例" }));
    const createDialog = await screen.findByRole("dialog", { name: "新建实例" });
    expect(createDialog.querySelector('select:not([aria-hidden="true"])')).toBeNull();
    expect(createDialog.querySelector('input[type="checkbox"]:not([aria-hidden="true"])')).toBeNull();
    expect(within(createDialog).getByRole("combobox", { name: "数据库类型" })).toBeInTheDocument();
    expect(await within(createDialog).findByRole("combobox", { name: "凭据" })).toBeInTheDocument();
    expect(within(createDialog).getByRole("switch", { name: "启用" })).toBeInTheDocument();
    fireEvent.change(within(createDialog).getByLabelText("实例名称"), { target: { value: "mysql-new" } });
    fireEvent.change(within(createDialog).getByLabelText("主机/IP"), { target: { value: "10.0.0.10" } });
    fireEvent.change(within(createDialog).getByLabelText("端口"), { target: { value: "3306" } });
    fireEvent.change(within(createDialog).getByLabelText("默认数据库"), { target: { value: "app_db" } });
    fireEvent.click(within(createDialog).getByRole("combobox", { name: "凭据" }));
    fireEvent.click(await screen.findByRole("option", { name: "prod credential · mysql" }));
    fireEvent.change(within(createDialog).getByLabelText("标签代码"), { target: { value: "prod, core" } });
    fireEvent.change(within(createDialog).getByLabelText("描述"), { target: { value: "new instance" } });
    fireEvent.click(within(createDialog).getByRole("button", { name: "校验连接参数" }));

    await waitFor(() => {
      expect(actionMocks.validateInstanceConnectionParams).toHaveBeenCalledWith({
        name: "mysql-new",
        db_type: "mysql",
        host: "10.0.0.10",
        port: 3306,
        database_name: "app_db",
        credential_id: 8,
        description: "new instance",
        tag_names: ["prod", "core"],
        is_active: true
      });
    });

    fireEvent.click(within(createDialog).getByRole("button", { name: "保存实例" }));

    await waitFor(() => {
      expect(actionMocks.createInstance).toHaveBeenCalledWith({
        name: "mysql-new",
        db_type: "mysql",
        host: "10.0.0.10",
        port: 3306,
        database_name: "app_db",
        credential_id: 8,
        description: "new instance",
        tag_names: ["prod", "core"],
        is_active: true
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "编辑实例 1" }));
    const editDialog = await screen.findByRole("dialog", { name: "编辑实例 mysql-prod" });
    fireEvent.change(within(editDialog).getByLabelText("实例名称"), { target: { value: "mysql-prod-updated" } });
    fireEvent.change(within(editDialog).getByLabelText("标签代码"), { target: { value: "prod" } });
    fireEvent.click(within(editDialog).getByRole("button", { name: "保存实例" }));

    await waitFor(() => {
      expect(actionMocks.updateInstance).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          name: "mysql-prod-updated",
          db_type: "mysql",
          host: "10.0.0.8",
          port: 3306,
          tag_names: ["prod"],
          is_active: true
        })
      );
    });
  });

  it("opens instance detail and runs existing instance actions", async () => {
    renderWithQueryClient(<InstancesPage />);

    await expectTextPresent("mysql-prod");
    fireEvent.click(screen.getByRole("checkbox", { name: "选择实例 mysql-prod" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "选择实例 mysql-old" }));
    fireEvent.click(screen.getByRole("button", { name: "批量测试连接" }));
    await waitFor(() => {
      expect(actionMocks.batchTestInstanceConnections).toHaveBeenCalledWith([1, 4]);
    });

    fireEvent.click(screen.getByRole("button", { name: "删除实例 1" }));
    expect(await screen.findByRole("alertdialog", { name: "确认移入回收站 mysql-prod" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认移入回收站" }));
    await waitFor(() => {
      expect(actionMocks.deleteInstance).toHaveBeenCalledWith(1);
    });

    fireEvent.click(screen.getByRole("button", { name: "恢复实例 4" }));
    await waitFor(() => {
      expect(actionMocks.restoreInstance).toHaveBeenCalledWith(4);
    });
  });

  it("runs instance batch delete and CSV import through v1 APIs", async () => {
    renderWithQueryClient(<InstancesPage />);

    await expectTextPresent("mysql-prod");
    fireEvent.click(screen.getByRole("checkbox", { name: "选择实例 mysql-prod" }));
    fireEvent.click(screen.getByRole("button", { name: "移入回收站" }));
    expect(await screen.findByRole("alertdialog", { name: "确认批量移入回收站" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认批量移入回收站" }));

    await waitFor(() => {
      expect(actionMocks.batchDeleteInstances).toHaveBeenCalledWith([1], "soft");
    });

    fireEvent.click(screen.getByRole("button", { name: "批量导入" }));
    const importDialog = await screen.findByRole("dialog", { name: "批量导入实例" });
    const file = new File(["name,host"], "instances.csv", { type: "text/csv" });
    fireEvent.change(within(importDialog).getByLabelText("CSV 文件"), { target: { files: [file] } });
    fireEvent.click(within(importDialog).getByRole("button", { name: "上传并创建" }));

    await waitFor(() => {
      expect(actionMocks.importInstancesFromCsv).toHaveBeenCalledWith(file);
    });
  });

  it("renders the direct instance detail page", async () => {
    renderWithQueryClient(<InstanceDetailPage instanceId={1} />);

    expect(await screen.findByRole("heading", { name: "实例详情 mysql-prod" })).toBeInTheDocument();
    expect(screen.getByText("生产实例")).toBeInTheDocument();
    expect(screen.getByText("实例ID")).toBeInTheDocument();
    expect(screen.getByText("数据库版本")).toBeInTheDocument();
    expect(screen.getByText("8.0")).toBeInTheDocument();
    expect(screen.getByText("标签")).toBeInTheDocument();
    expect(screen.getAllByText("生产").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "编辑实例" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "移入回收站" })).toBeInTheDocument();
    expect(screen.getAllByText("10.0.0.8:3306").length).toBeGreaterThan(0);
    expect(await screen.findByText("连接状态")).toBeInTheDocument();
    expect(screen.getByText("审计目标数")).toBeInTheDocument();
    expect(screen.getByText("备份链完整大小")).toBeInTheDocument();
    expect(screen.getAllByText("Backup ID").length).toBeGreaterThan(0);
    expect(screen.getAllByText("backup-1").length).toBeGreaterThan(0);
    expect(screen.getByText("覆盖数量")).toBeInTheDocument();
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
    expect(screen.getByText("平台")).toBeInTheDocument();
    expect(screen.getByText("生产 Veeam / 10.0.0.9")).toBeInTheDocument();
    expect(screen.getByText("数据大小")).toBeInTheDocument();
    expect(screen.getByText("压缩率")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.getByText("AuditProd")).toBeInTheDocument();
    expect(screen.getByText("Restore 1")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "审计信息" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "备份信息" })).toBeInTheDocument();
    expect(screen.getByText("账户信息")).toBeInTheDocument();
    expect(screen.getByText("账户信息（AG）")).toBeInTheDocument();
    expect(screen.getByText("容量信息")).toBeInTheDocument();
    expect(screen.getByText("readonly")).toBeInTheDocument();
    expect(screen.getByText("sa")).toBeInTheDocument();
    expect(screen.getByText("账户总数")).toBeInTheDocument();
    expect(screen.getByText("活跃账户")).toBeInTheDocument();
    expect(screen.getByText("AG账户总数")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "查看权限 readonly" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "变更历史 readonly" })).toBeInTheDocument();
    expect(screen.queryByText("数据库信息")).not.toBeInTheDocument();
    expect(document.querySelector("pre")).toBeNull();

    const agAccountsTab = screen.getByRole("tab", { name: "账户信息（AG）" });
    fireEvent.pointerDown(agAccountsTab);
    fireEvent.click(agAccountsTab);
    expect(await screen.findByText("AG_PROD")).toBeInTheDocument();
    expect(screen.getByText(/AG_LISTENER/)).toBeInTheDocument();

    const capacityTab = screen.getByRole("tab", { name: "容量信息" });
    fireEvent.pointerDown(capacityTab);
    fireEvent.click(capacityTab);
    expect(screen.getAllByText("app_db").length).toBeGreaterThan(0);
    expect(screen.getByText("legacy_db")).toBeInTheDocument();
    expect(screen.getAllByText("2.00 GB").length).toBeGreaterThan(0);
    expect(screen.getByText("当前数据库")).toBeInTheDocument();
    expect(screen.getByText("容量总量")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "表容量 app_db" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "返回实例列表" })).toHaveAttribute("href", "/console/instances");

    fireEvent.click(screen.getByRole("button", { name: "测试连接" }));
    fireEvent.click(screen.getByRole("button", { name: "同步账户" }));
    fireEvent.click(screen.getByRole("button", { name: "同步容量" }));
    fireEvent.click(screen.getByRole("button", { name: "同步审计" }));
    fireEvent.click(screen.getByRole("button", { name: "同步备份" }));

    await waitFor(() => {
      expect(actionMocks.testInstanceConnection).toHaveBeenCalledWith(1);
      expect(actionMocks.syncInstanceAccounts).toHaveBeenCalledWith(1);
      expect(actionMocks.syncInstanceCapacity).toHaveBeenCalledWith(1);
      expect(actionMocks.syncInstanceAuditInfo).toHaveBeenCalledWith(1);
      expect(actionMocks.syncInstanceBackup).toHaveBeenCalledWith(1);
    });
  });

  it("renders database ledgers from the API", async () => {
    renderWithQueryClient(<DatabaseLedgersPage />);

    await waitFor(() => {
      expect(screen.getByText("app_db")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { level: 1, name: "数据库台账" })).toBeInTheDocument();
    expect(screen.getByText("2.00 GB")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "数据库大小" })).toBeInTheDocument();
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders database ledgers with legacy filters, fields, and actions", async () => {
    renderWithQueryClient(<DatabaseLedgersPage />);

    await expectTextPresent("app_db");
    expect(screen.queryByText("每页 20 条")).not.toBeInTheDocument();

    for (const label of ["搜索", "类型", "标签"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
    for (const header of ["数据库/实例", "类型", "数据库大小", "标签", "操作"]) {
      expect(screen.getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
    for (const action of ["数据库统计", "同步所有数据库", "导出CSV"]) {
      expect(screen.getAllByText(action).length).toBeGreaterThan(0);
    }
    expect(screen.getByRole("button", { name: "查看容量趋势 2" })).toBeInTheDocument();
  });

  it("opens database table sizes and refreshes them through v1 APIs", async () => {
    renderWithQueryClient(<DatabaseLedgersPage />);

    await expectTextPresent("app_db");
    fireEvent.click(screen.getByRole("button", { name: "查看容量趋势 2" }));
    const dialog = await screen.findByRole("dialog", { name: "数据库表容量 app_db" });
    expect(await within(dialog).findByText("orders")).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "刷新表容量 app_db" }));

    await waitFor(() => {
      expect(actionMocks.refreshDatabaseTableSizes).toHaveBeenCalledWith(2);
    });
  });

  it("renders account ledgers from the API", async () => {
    renderWithQueryClient(<AccountLedgersPage />);

    await waitFor(() => {
      expect(screen.getByText("readonly")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { level: 1, name: "账户台账" })).toBeInTheDocument();
    expect(screen.getAllByText("只读账户").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/mysql-prod/).length).toBeGreaterThan(0);
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders account ledgers with legacy filters, fields, and actions", async () => {
    renderWithQueryClient(<AccountLedgersPage />);

    await expectTextPresent("readonly");
    expect(screen.queryByText("每页 20 条")).not.toBeInTheDocument();

    for (const label of ["搜索", "分类", "AD状态", "标签"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
    for (const header of ["账户/实例", "是否可用", "是否删除", "是否超管", "AD状态", "分类", "类型", "标签", "操作"]) {
      expect(screen.getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
    for (const action of ["账户统计", "同步所有账户", "导出CSV"]) {
      expect(screen.getAllByText(action).length).toBeGreaterThan(0);
    }
    expect(screen.getByRole("button", { name: "查看权限 3" })).toBeInTheDocument();
  });

  it("opens account permissions and change history through v1 APIs", async () => {
    renderWithQueryClient(<AccountLedgersPage />);

    await expectTextPresent("readonly");
    fireEvent.click(screen.getByRole("button", { name: "查看权限 3" }));
    const permissionsDialog = await screen.findByRole("dialog", { name: "权限详情 readonly" });
    expect(await within(permissionsDialog).findByText("reader")).toBeInTheDocument();
    fireEvent.click(within(permissionsDialog).getByRole("button", { name: "关闭详情" }));

    fireEvent.click(screen.getByRole("button", { name: "查看变更历史 3" }));
    const historyDialog = await screen.findByRole("dialog", { name: "变更历史 readonly" });
    expect(await within(historyDialog).findByText("GRANT SELECT")).toBeInTheDocument();
  });

  it("runs direct list actions through v1 APIs", async () => {
    renderWithQueryClient(<InstancesPage />);
    await expectTextPresent("mysql-prod");
    fireEvent.click(screen.getByRole("button", { name: "测试连接 1" }));
    await waitFor(() => {
      expect(actionMocks.testInstanceConnection).toHaveBeenCalledWith(1);
    });

    cleanup();
    renderWithQueryClient(<DatabaseLedgersPage />);
    await expectTextPresent("app_db");
    fireEvent.click(screen.getByRole("button", { name: "同步所有数据库" }));
    await waitFor(() => {
      expect(actionMocks.syncDatabases).toHaveBeenCalled();
    });

    cleanup();
    renderWithQueryClient(<AccountLedgersPage />);
    await expectTextPresent("readonly");
    fireEvent.click(screen.getByRole("button", { name: "同步所有账户" }));
    await waitFor(() => {
      expect(actionMocks.syncAccounts).toHaveBeenCalled();
    });
  });
});
