import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { AccountChangeLogsPage, HistoryLogsPage } from "./AuditPages";

vi.mock("@/api/audit", () => ({
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

  return render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>);
}

describe("AuditPages", () => {
  it("renders history logs from the API", async () => {
    renderWithQueryClient(<HistoryLogsPage />);

    await waitFor(() => {
      expect(screen.getByText("sync failed")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "日志中心" })).toBeInTheDocument();
    expect(screen.getAllByText("scheduler").length).toBeGreaterThan(0);
    expect(screen.getAllByText("ERROR").length).toBeGreaterThan(0);
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });

  it("renders account change logs from the API", async () => {
    renderWithQueryClient(<AccountChangeLogsPage />);

    await waitFor(() => {
      expect(screen.getAllByText("CBRAIN").length).toBeGreaterThan(0);
    });

    expect(screen.getByRole("heading", { name: "变更历史" })).toBeInTheDocument();
    expect(screen.getByText("新增账户,赋予 5 项权限")).toBeInTheDocument();
    expect(screen.getAllByText("success").length).toBeGreaterThan(0);
    expect(screen.queryByText("页面骨架已接入")).not.toBeInTheDocument();
  });
});
