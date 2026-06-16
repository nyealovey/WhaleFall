import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { fetchRiskCenterSnapshot } from "@/api/riskCenter";

import { RiskCenterPage } from "./RiskCenterPage";

vi.mock("@/api/riskCenter", () => ({
  fetchRiskCenterSnapshot: vi.fn(async () => ({
    summary: {
      total_instances: 2,
      severity_counts: { high: 1, medium: 1, low: 0, ok: 0 },
      db_type_counts: { mysql: { total: 1, high: 1, medium: 0, low: 0, ok: 0 } },
      top_risks: [{ rule_key: "backup_missing", instance_name: "db-critical", severity: "high", label: "备份缺失" }],
      generated_at: "2026-06-11T10:00:00"
    },
    cards: {
      items: [
        {
          instance_id: 1,
          name: "db-critical",
          db_type: "mysql",
          host: "10.0.0.1",
          port: 3306,
          overall_severity: "high",
          risk_score: 100,
          group: "MySQL",
          backup: { tone: "danger", label: "未备份" },
          audit: { tone: "success", label: "已开启" },
          managed: { tone: "warning", label: "未托管" },
          cluster: { tone: "muted", label: "无群集" },
          tasks: { tone: "success", label: "正常" },
          links: { detail: "/instances/1" },
          risk_items: [{ rule_key: "backup_missing", category: "backup", severity: "high", label: "备份缺失", detail: "未发现近期备份" }]
        }
      ],
      total: 1,
      page: 1,
      pages: 1,
      limit: 12
    }
  }))
}));

function renderWithQueryClient() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <RiskCenterPage />
    </QueryClientProvider>
  );
}

describe("RiskCenterPage", () => {
  it("renders risk summary and cards from the API", async () => {
    renderWithQueryClient();

    await waitFor(() => {
      expect(screen.getAllByText("db-critical").length).toBeGreaterThan(0);
    });

    expect(screen.getByRole("heading", { name: "风险中心" })).toBeInTheDocument();
    expect(screen.getAllByText("高风险").length).toBeGreaterThan(0);
    expect(screen.getAllByText("备份缺失").length).toBeGreaterThan(0);
    expect(screen.getByText("10.0.0.1:3306")).toBeInTheDocument();
    expect(screen.queryByText("React 页面骨架已就绪")).not.toBeInTheDocument();
  });

  it("keeps risk center aligned with legacy filters, groups, and signal wall", async () => {
    renderWithQueryClient();

    await screen.findByRole("heading", { name: "风险中心" });

    for (const text of [
      "刷新",
      "总实例",
      "搜索",
      "实例名 / 主机 / 类型",
      "严重度",
      "数据库类型",
      "状态",
      "标签",
      "筛选",
      "清空",
      "MySQL (1)",
      "实例核心风险指标",
      "备份",
      "审计",
      "托管",
      "群集",
      "任务"
    ]) {
      await waitFor(() => {
        expect(screen.getAllByText(text).length).toBeGreaterThan(0);
      });
    }
  });

  it("applies legacy risk filters to the cards request", async () => {
    renderWithQueryClient();

    await screen.findByRole("heading", { name: "风险中心" });
    vi.mocked(fetchRiskCenterSnapshot).mockClear();

    fireEvent.change(screen.getByPlaceholderText("实例名 / 主机 / 类型"), { target: { value: "db-critical" } });
    fireEvent.click(screen.getByRole("combobox", { name: "严重度" }));
    fireEvent.click(await screen.findByRole("option", { name: "高风险" }));
    fireEvent.click(screen.getByRole("combobox", { name: "数据库类型" }));
    fireEvent.click(await screen.findByRole("option", { name: "MySQL" }));
    fireEvent.click(screen.getByRole("combobox", { name: "状态" }));
    fireEvent.click(await screen.findByRole("option", { name: "异常" }));
    fireEvent.click(screen.getByRole("combobox", { name: "标签" }));
    fireEvent.click(await screen.findByRole("option", { name: "生产" }));
    fireEvent.click(screen.getByRole("button", { name: "筛选" }));

    await waitFor(() => {
      expect(fetchRiskCenterSnapshot).toHaveBeenCalledWith({
        dbType: "mysql",
        search: "db-critical",
        severity: "high",
        status: "warning",
        tag: "prod"
      });
    });
  });
});
