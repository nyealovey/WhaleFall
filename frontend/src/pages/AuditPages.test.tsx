import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { TooltipProvider } from "@/components/ui/tooltip";

import { AccountChangeLogsPage, HistoryLogsPage } from "./AuditPages";

vi.mock("@/api/audit", () => ({
  fetchAccountChangeLogDetail: vi.fn(async () => ({
    log: {
      id: 2,
      username: "CBRAIN",
      change_type: "add",
      change_time: "2026-06-11 10:00:00",
      status: "success",
      message: "新增账户,赋予 5 项权限",
      privilege_diff: [{ privilege: "CREATE SESSION", action: "added" }],
      other_diff: [{ field: "status", after: "OPEN" }],
      session_id: "session_123"
    }
  })),
  fetchHistoryLogsSnapshot: vi.fn(async () => ({
    statistics: {
      total_logs: 12,
      error_count: 1,
      warning_count: 2,
      info_count: 9,
      debug_count: 0,
      critical_count: 0,
      level_distribution: { INFO: 9, ERROR: 1, WARNING: 2 },
      top_modules: [{ module: "scheduler", count: 6 }],
      error_rate: 8.3
    },
    list: {
      items: [
        {
          id: 1,
          timestamp: "2026-06-11T10:00:00+08:00",
          timestamp_display: "2026-06-11 10:00:00",
          level: "ERROR",
          module: "scheduler",
          message: "sync failed",
          traceback: "Traceback",
          context: { run_id: "run-1" }
        }
      ],
      total: 1,
      page: 1,
      pages: 1,
      limit: 20
    }
  })),
  fetchHistoryLogDetail: vi.fn(async () => ({
    log: {
      id: 1,
      timestamp: "2026-06-11T10:00:00+08:00",
      timestamp_display: "2026-06-11 10:00:00",
      level: "ERROR",
      module: "scheduler",
      message: "sync failed",
      traceback: "Traceback",
      context: { run_id: "run-1" }
    }
  })),
  fetchAccountChangeLogsSnapshot: vi.fn(async () => ({
    statistics: {
      total_changes: 4,
      success_count: 3,
      failed_count: 1,
      affected_accounts: 2
    },
    list: {
      items: [
        {
          id: 2,
          account_id: 4453,
          instance_id: 100,
          instance_name: "CBRAIN",
          instance_host: "10.0.0.1",
          db_type: "oracle",
          username: "CBRAIN",
          change_type: "add",
          status: "success",
          message: "新增账户,赋予 5 项权限",
          change_time: "2026-06-11 10:00:00",
          session_id: "session_123",
          privilege_diff_count: 5,
          other_diff_count: 1
        }
      ],
      total: 1,
      page: 1,
      pages: 1,
      limit: 20
    }
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

describe("AuditPages", () => {
  it("renders history logs from the API", async () => {
    renderWithQueryClient(<HistoryLogsPage />);

    await waitFor(() => {
      expect(screen.getByText("sync failed")).toBeInTheDocument();
    });

    expect(screen.getByText("sync failed")).not.toHaveAttribute("title");
    expect(screen.getByRole("heading", { name: "日志中心" })).toBeInTheDocument();
    expect(screen.getAllByText("scheduler").length).toBeGreaterThan(0);
    expect(screen.getAllByText("ERROR").length).toBeGreaterThan(0);
    for (const text of ["总日志数", "错误日志", "警告日志", "信息日志", "9", "调试 0"]) {
      expect(screen.getAllByText(text).length).toBeGreaterThan(0);
    }
    expect(screen.queryByText("System audit")).not.toBeInTheDocument();
    expect(screen.queryByText("查看最近 24 小时系统日志统计、首屏日志列表和日志详情。")).not.toBeInTheDocument();
    expect(screen.queryByText(/最近 24 小时 · 每页/)).not.toBeInTheDocument();
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders account change logs from the API", async () => {
    renderWithQueryClient(<AccountChangeLogsPage />);

    await waitFor(() => {
      expect(screen.getAllByText("CBRAIN").length).toBeGreaterThan(0);
    });

    expect(screen.getByRole("heading", { name: "变更历史" })).toBeInTheDocument();
    expect(screen.getByText("新增账户,赋予 5 项权限")).not.toHaveAttribute("title");
    expect(screen.getAllByText("ORACLE").length).toBeGreaterThan(0);
    for (const text of ["变更总数", "成功率", "75%", "失败变更", "影响账号数"]) {
      expect(screen.getAllByText(text).length).toBeGreaterThan(0);
    }
    expect(screen.queryByText("Account audit")).not.toBeInTheDocument();
    expect(screen.queryByText("查看最近 24 小时账户变更统计、首屏变更日志和变更详情。")).not.toBeInTheDocument();
    expect(screen.queryByText(/最近 24 小时 · 每页/)).not.toBeInTheDocument();
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders history logs with legacy filters, fields, and actions", async () => {
    renderWithQueryClient(<HistoryLogsPage />);

    await screen.findByRole("heading", { name: "日志中心" });

    for (const text of ["搜索", "级别", "模块", "时间范围", "时间", "消息", "操作"]) {
      await expectTextPresent(text);
    }

    expect(screen.getByRole("button", { name: "查看详情 1" })).toBeInTheDocument();
  });

  it("opens history log detail in a React dialog", async () => {
    renderWithQueryClient(<HistoryLogsPage />);

    await screen.findByRole("button", { name: "查看详情 1" });
    fireEvent.click(screen.getByRole("button", { name: "查看详情 1" }));

    expect(await screen.findByRole("dialog", { name: "日志详情 #1" })).toBeInTheDocument();
    expect(screen.getAllByText("sync failed").length).toBeGreaterThan(0);
    expect(await screen.findByText("Traceback")).toBeInTheDocument();
    expect(await screen.findByText(/run-1/)).toBeInTheDocument();
  });

  it("renders account change logs with legacy filters, fields, and actions", async () => {
    renderWithQueryClient(<AccountChangeLogsPage />);

    await screen.findByRole("heading", { name: "变更历史" });

    for (const text of ["搜索", "实例", "数据库类型", "变更类型", "时间范围", "时间", "账号", "类型", "摘要", "操作"]) {
      await expectTextPresent(text);
    }

    expect(screen.getByRole("button", { name: "查看详情 2" })).toBeInTheDocument();
  });

  it("opens account change log detail in a React dialog", async () => {
    renderWithQueryClient(<AccountChangeLogsPage />);

    await screen.findByRole("button", { name: "查看详情 2" });
    fireEvent.click(screen.getByRole("button", { name: "查看详情 2" }));

    expect(await screen.findByRole("dialog", { name: "变更详情 #2" })).toBeInTheDocument();
    expect(screen.getAllByText("CBRAIN").length).toBeGreaterThan(0);
    expect(await screen.findByText(/CREATE SESSION/)).toBeInTheDocument();
    expect(await screen.findByText(/status/)).toBeInTheDocument();
  });
});
