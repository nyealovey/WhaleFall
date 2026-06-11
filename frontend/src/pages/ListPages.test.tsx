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

describe("ListPages", () => {
  it("renders instances from the API", async () => {
    renderWithQueryClient(<InstancesPage />);

    await waitFor(() => {
      expect(screen.getByText("mysql-prod")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "实例管理" })).toBeInTheDocument();
    expect(screen.getByText("10.0.0.8:3306")).toBeInTheDocument();
    expect(screen.getByText("生产")).toBeInTheDocument();
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders database ledgers from the API", async () => {
    renderWithQueryClient(<DatabaseLedgersPage />);

    await waitFor(() => {
      expect(screen.getByText("app_db")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "数据库台账" })).toBeInTheDocument();
    expect(screen.getByText("2.00 GB")).toBeInTheDocument();
    expect(screen.getAllByText("已更新").length).toBeGreaterThan(0);
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders account ledgers from the API", async () => {
    renderWithQueryClient(<AccountLedgersPage />);

    await waitFor(() => {
      expect(screen.getByText("readonly")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "账户台账" })).toBeInTheDocument();
    expect(screen.getByText("只读账户")).toBeInTheDocument();
    expect(screen.getAllByText("mysql-prod").length).toBeGreaterThan(0);
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });
});
