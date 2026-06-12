import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { AccountLedgersPage, DatabaseLedgersPage, InstancesPage } from "./ListPages";

vi.mock("@/api/lists", () => ({
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
      }
    ],
    total: 1,
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

    for (const label of ["搜索", "类型", "状态", "审计", "托管", "备份", "标签"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
    for (const header of ["名称", "类型", "主机/IP", "状态", "审计", "已托管", "备份", "活跃", "版本 / 同步", "标签", "操作"]) {
      expect(screen.getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
    for (const action of ["实例统计", "添加实例", "移入回收站", "批量测试连接", "批量导入", "显示已删除", "导出CSV"]) {
      expect(screen.getAllByText(action).length).toBeGreaterThan(0);
    }
    expect(screen.getByRole("button", { name: "查看详情 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "测试连接 1" })).toBeInTheDocument();
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
});
