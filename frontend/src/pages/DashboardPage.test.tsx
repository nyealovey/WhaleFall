import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DashboardPage } from "./DashboardPage";
import { runAction } from "@/utils/action-feedback";

vi.mock("@/api/dashboard", () => ({
  fetchDashboardSnapshot: vi.fn(async () => ({
    overview: {
      users: { total: 2, active: 2 },
      instances: { total: 7, active: 6, inactive: 1, deleted: 0, physical: 6, ag_virtual: 1 },
      accounts: { total: 42, active: 40, normal: 39, locked: 1, deleted: 2 },
      classified_accounts: {
        total: 18,
        auto: 12,
        classifications: [{ code: "dba", display_name: "DBA", count: 8 }]
      },
      capacity: { total_gb: 512.4, usage_percent: 64 },
      databases: { total: 25, active: 24, inactive: 1, deleted: 0 }
    },
    status: {
      system: {
        cpu: 11,
        memory: { used: 1024, total: 2048, percent: 50 },
        disk: { used: 100, total: 200, percent: 50 }
      },
      services: { database: "healthy", redis: "healthy" },
      uptime: "3 days"
    },
    charts: {
      log_trend: [{ date: "2026-06-11", error_count: 2, warning_count: 5 }],
      log_levels: [{ level: "ERROR", count: 3 }],
      sync_trend: [{ date: "2026-06-11", count: 4 }]
    },
    activities: []
  }))
}));

vi.mock("@/utils/action-feedback", () => ({
  runAction: vi.fn((request: Promise<unknown>) => request)
}));

function renderWithQueryClient() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardPage />
    </QueryClientProvider>
  );
}

describe("DashboardPage", () => {
  it("renders live dashboard metrics instead of migration placeholders", async () => {
    renderWithQueryClient();

    await waitFor(() => {
      expect(screen.getByText("7")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "仪表盘" })).toBeInTheDocument();
    expect(screen.getByText("账户总数")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("数据库总数")).toBeInTheDocument();
    expect(screen.getByText("25")).toBeInTheDocument();
    expect(screen.getByText("DBA")).toBeInTheDocument();
    expect(screen.getByText("ERROR")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "日志等级折线图" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "同步趋势面积图" })).toBeInTheDocument();
    expect(screen.getAllByRole("progressbar")).toHaveLength(3);
    expect(screen.queryByText("迁移状态")).not.toBeInTheDocument();
    expect(screen.queryByText("活动流")).not.toBeInTheDocument();
  });

  it("keeps dashboard aligned with the legacy cockpit content", async () => {
    renderWithQueryClient();

    await screen.findByRole("heading", { name: "仪表盘" });

    for (const text of [
      "刷新数据",
      "数据库实例",
      "在线",
      "物理",
      "AG",
      "停用",
      "删除",
      "总容量",
      "风险告警",
      "错误和告警日志趋势（最近7天）",
      "错误日志",
      "告警日志",
      "系统状态",
      "CPU 使用率",
      "内存使用率",
      "磁盘使用率",
      "数据库:",
      "Redis:",
      "系统运行时间"
    ]) {
      await waitFor(() => {
        expect(screen.getAllByText(text).length).toBeGreaterThan(0);
      });
    }
  });

  it("refreshes through unified action feedback", async () => {
    renderWithQueryClient();

    await screen.findByRole("heading", { name: "仪表盘" });
    fireEvent.click(screen.getByRole("button", { name: "刷新数据" }));

    expect(runAction).toHaveBeenCalledWith(expect.any(Promise), { success: "仪表盘已刷新" });
  });
});
