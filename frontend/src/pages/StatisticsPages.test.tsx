import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { AccountStatisticsPage, DatabaseStatisticsPage, InstanceStatisticsPage } from "./StatisticsPages";

vi.mock("@/api/statistics", () => ({
  fetchInstanceStatistics: vi.fn(async () => ({
    total_instances: 3,
    current_instances: 2,
    active_instances: 2,
    normal_instances: 1,
    disabled_instances: 1,
    deleted_instances: 1,
    inactive_instances: 0,
    audit_enabled_instances: 2,
    high_availability_instances: 1,
    managed_instances: 2,
    unmanaged_instances: 0,
    backed_up_instances: 1,
    backup_stale_instances: 1,
    not_backed_up_instances: 0,
    backup_status_stats: [{ backup_status: "backed_up", count: 1 }],
    db_types_count: 1,
    db_type_stats: [{ db_type: "mysql", count: 2 }],
    port_stats: [{ port: 3306, count: 2 }],
    version_stats: [{ db_type: "mysql", version: "8.0", count: 2 }]
  })),
  fetchAccountStatisticsSnapshot: vi.fn(async () => ({
    summary: {
      total_accounts: 8,
      active_accounts: 7,
      locked_accounts: 1,
      normal_accounts: 6,
      deleted_accounts: 1,
      total_instances: 4,
      physical_instances: 3,
      ag_virtual_instances: 1,
      active_instances: 3,
      disabled_instances: 1,
      normal_instances: 3,
      deleted_instances: 0,
      owner_type_stats: { instance: 6, sqlserver_ag: 2 },
      ad_status_stats: { enabled: 5, disabled: 1 }
    },
    dbTypes: {
      mysql: { total_accounts: 5, locked_accounts: 1 },
      sqlserver: { total_accounts: 3, locked_accounts: 0 }
    },
    classifications: {
      DBA: { total_accounts: 2 },
      high_risk: { total_accounts: 1 }
    },
    rules: {
      rule_stats: [{ rule_id: 7, matched_accounts_count: 3 }]
    }
  })),
  fetchDatabaseStatistics: vi.fn(async () => ({
    stats: {
      total_databases: 9,
      active_databases: 8,
      inactive_databases: 1,
      deleted_databases: 0,
      total_instances: 2,
      total_size_mb: 4096,
      avg_size_mb: 512,
      max_size_mb: 2048,
      db_type_stats: [{ db_type: "postgresql", count: 4 }],
      instance_stats: [{ instance_id: 1, instance_name: "pg-prod", db_type: "postgresql", count: 4 }],
      sync_status_stats: [{ value: "completed", label: "已更新", variant: "success", count: 8 }],
      capacity_rankings: [
        {
          instance_id: 1,
          instance_name: "pg-prod",
          db_type: "postgresql",
          database_name: "app_db",
          size_mb: 2048,
          size_label: "2.00 GB",
          collected_at: "2026-03-16T10:00:00+00:00"
        }
      ]
    }
  }))
}));

function renderWithQueryClient(element: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  return render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>);
}

describe("StatisticsPages", () => {
  it("renders instance statistics from the API", async () => {
    renderWithQueryClient(<InstanceStatisticsPage />);

    await waitFor(() => {
      expect(screen.getAllByText("mysql").length).toBeGreaterThan(0);
    });

    expect(screen.getByRole("heading", { name: "实例统计" })).toBeInTheDocument();
    expect(screen.getAllByText("3306").length).toBeGreaterThan(0);
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders account statistics from the API", async () => {
    renderWithQueryClient(<AccountStatisticsPage />);

    await waitFor(() => {
      expect(screen.getByText("DBA")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "账户统计" })).toBeInTheDocument();
    expect(screen.getAllByText("sqlserver").length).toBeGreaterThan(0);
    expect(screen.getByText("rule #7")).toBeInTheDocument();
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders database statistics from the API", async () => {
    renderWithQueryClient(<DatabaseStatisticsPage />);

    await waitFor(() => {
      expect(screen.getAllByText("postgresql").length).toBeGreaterThan(0);
    });

    expect(screen.getByRole("heading", { name: "数据库统计" })).toBeInTheDocument();
    expect(screen.getByText("app_db")).toBeInTheDocument();
    expect(screen.getAllByText("2.00 GB").length).toBeGreaterThan(0);
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });
});
